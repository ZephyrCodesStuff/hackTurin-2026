#!/usr/bin/env python3
"""Interactive arrow-key and CLI user management console."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure traffic_api package is importable
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from traffic_api.auth_user import (  # noqa: E402
    compute_client_hash,
    hash_password,
    seed_default_admin_if_needed,
)
from traffic_api.database import (  # noqa: E402
    get_all_cameras,
    initialize_database,
)
from traffic_api.user_db import (  # noqa: E402
    create_user,
    delete_user,
    get_user_assigned_camera_ids,
    get_user_by_username,
    list_users,
    set_user_cameras,
    update_user_password,
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_timestamp(ms: int) -> str:
    if not ms:
        return "Unknown"
    return datetime.fromtimestamp(ms / 1000.0).strftime("%Y-%m-%d %H:%M:%S")


def do_list() -> None:
    users = list_users()
    if not users:
        print("\n  [No users found in database]\n")
        return

    print("\n" + "=" * 65)
    print(f" {'USERNAME':<20} | {'USER ID':<36} | {'CREATED':<19}")
    print("=" * 65)
    for u in users:
        print(
            f" {u['username']:<20} | {u['id']:<36} | {format_timestamp(u.get('created_at', 0))}"
        )
    print("=" * 65 + "\n")


def do_add(username: str, password: str) -> None:
    clean_username = username.strip().lower()
    if not clean_username:
        print("Error: Username cannot be empty.")
        return
    if not password:
        print("Error: Password cannot be empty.")
        return

    client_hash = compute_client_hash(clean_username, password)
    server_hash = hash_password(client_hash)

    try:
        user = create_user(clean_username, server_hash)
        print(f"\n  [+] Successfully created user '{user['username']}' (ID: {user['id']})\n")
    except ValueError as e:
        print(f"\n  [-] Error: {e}\n")


def do_change_password(username: str, password: str) -> None:
    clean_username = username.strip().lower()
    user = get_user_by_username(clean_username)
    if not user:
        print(f"\n  [-] Error: User '{clean_username}' not found.\n")
        return
    if not password:
        print("Error: Password cannot be empty.")
        return

    client_hash = compute_client_hash(clean_username, password)
    server_hash = hash_password(client_hash)
    if update_user_password(clean_username, server_hash):
        print(f"\n  [+] Successfully updated password for user '{clean_username}'.\n")
    else:
        print(f"\n  [-] Failed to update password for '{clean_username}'.\n")


def do_delete(username: str) -> None:
    clean_username = username.strip().lower()
    if delete_user(clean_username):
        print(f"\n  [+] Successfully deleted user '{clean_username}'.\n")
    else:
        print(f"\n  [-] Error: User '{clean_username}' not found.\n")


def do_assign(username: str, camera_ids: list[str]) -> None:
    clean_username = username.strip().lower()
    user = get_user_by_username(clean_username)
    if not user:
        print(f"\n  [-] Error: User '{clean_username}' not found.\n")
        return
    set_user_cameras(user["id"], camera_ids)
    print(f"\n  [+] Successfully assigned {len(camera_ids)} camera(s) to '{clean_username}'.\n")


def interactive_arrow_menu() -> None:
    try:
        import questionary
    except ImportError:
        print("questionary is not installed. Run 'pip install questionary' for arrow-key navigation.")
        interactive_fallback_menu()
        return

    print("\n" + "╔" + "═" * 46 + "╗")
    print("║   🚦 Traffic Grid - User Management Console  ║")
    print("╚" + "═" * 46 + "╝\n")

    while True:
        action = questionary.select(
            "What would you like to do? (Use ↑/↓ arrows)",
            choices=[
                "📋 List all users",
                "➕ Add / Register user",
                "🔑 Change user password",
                "🎥 Assign cameras to user",
                "🗑️  Delete user",
                "🚪 Exit",
            ],
        ).ask()

        if action is None or action == "🚪 Exit":
            print("\nGoodbye!\n")
            break

        if action == "📋 List all users":
            do_list()

        elif action == "➕ Add / Register user":
            username = questionary.text("Enter username:").ask()
            if not username:
                continue
            password = questionary.password("Enter password:").ask()
            if not password:
                continue
            confirm = questionary.password("Confirm password:").ask()
            if password != confirm:
                print("\n  ✗ Passwords do not match!\n")
                continue
            do_add(username, password)

        elif action == "🔑 Change user password":
            users = list_users()
            if not users:
                print("\n  [No users in database]\n")
                continue
            choices = [u["username"] for u in users] + ["[Cancel]"]
            target = questionary.select("Select user to update:", choices=choices).ask()
            if target is None or target == "[Cancel]":
                continue

            new_pw = questionary.password(f"Enter new password for '{target}':").ask()
            if not new_pw:
                continue
            confirm_pw = questionary.password("Confirm new password:").ask()
            if new_pw != confirm_pw:
                print("\n  [-] Passwords do not match!\n")
                continue
            do_change_password(target, new_pw)

        elif action == "🎥 Assign cameras to user":
            users = list_users()
            if not users:
                print("\n  [No users in database]\n")
                continue
            choices = [u["username"] for u in users] + ["[Cancel]"]
            target = questionary.select("Select user to manage camera access:", choices=choices).ask()
            if target is None or target == "[Cancel]":
                continue

            if target.lower() == "admin":
                print("\n  [Note: 'admin' has automatic god-mode access to all cameras at all times]\n")

            target_user = get_user_by_username(target)
            if not target_user:
                continue

            all_cameras = get_all_cameras()
            if not all_cameras:
                print("\n  [-] No cameras found in database. Run demo seed first.\n")
                continue

            assigned_ids = set(get_user_assigned_camera_ids(target_user["id"]))
            cam_choices = [
                questionary.Choice(
                    title=f"{c['name']} (ID: {c['id'][:8]}..., {c['state']})",
                    value=c["id"],
                    checked=(c["id"] in assigned_ids),
                )
                for c in all_cameras
            ]

            selected_camera_ids = questionary.checkbox(
                f"Select cameras for '{target}' (Space to toggle, Enter to confirm):",
                choices=cam_choices,
            ).ask()

            if selected_camera_ids is not None:
                set_user_cameras(target_user["id"], selected_camera_ids)
                print(f"\n  [+] Saved! '{target}' now has access to {len(selected_camera_ids)} camera(s).\n")

        elif action == "🗑️  Delete user":
            users = list_users()
            if not users:
                print("\n  [No users in database]\n")
                continue
            choices = [u["username"] for u in users] + ["[Cancel]"]
            target = questionary.select("Select user to delete:", choices=choices).ask()
            if target is None or target == "[Cancel]":
                continue

            confirm = questionary.confirm(f"Are you sure you want to delete '{target}'?").ask()
            if confirm:
                do_delete(target)


def interactive_fallback_menu() -> None:
    import getpass

    while True:
        print("\n--- User Management ---")
        print("1. List users")
        print("2. Add user")
        print("3. Change password")
        print("4. Delete user")
        print("5. Exit")
        choice = input("Enter choice (1-5): ").strip()

        if choice == "1":
            do_list()
        elif choice == "2":
            u = input("Username: ").strip()
            p = getpass.getpass("Password: ")
            do_add(u, p)
        elif choice == "3":
            u = input("Username: ").strip()
            p = getpass.getpass("New Password: ")
            do_change_password(u, p)
        elif choice == "4":
            u = input("Username to delete: ").strip()
            do_delete(u)
        elif choice == "5":
            break


def main() -> int:
    initialize_database()
    seed_default_admin_if_needed()

    parser = argparse.ArgumentParser(
        description="Manage Traffic Grid panel users."
    )
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List registered users")

    # add
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("--username", "-u", required=True, help="Username")
    add_parser.add_argument("--password", "-p", required=True, help="Password")

    # passwd
    pw_parser = subparsers.add_parser("passwd", help="Change user password")
    pw_parser.add_argument("--username", "-u", required=True, help="Username")
    pw_parser.add_argument("--password", "-p", required=True, help="New password")

    # delete
    del_parser = subparsers.add_parser("delete", help="Delete a user")
    del_parser.add_argument("--username", "-u", required=True, help="Username")

    # assign
    assign_parser = subparsers.add_parser("assign", help="Assign cameras to a user")
    assign_parser.add_argument("--username", "-u", required=True, help="Username")
    assign_parser.add_argument(
        "--cameras",
        "-c",
        required=True,
        help="Comma-separated camera IDs, 'all', or 'none'",
    )

    args = parser.parse_args()

    if not args.command:
        interactive_arrow_menu()
        return 0

    if args.command == "list":
        do_list()
    elif args.command == "add":
        do_add(args.username, args.password)
    elif args.command == "passwd":
        do_change_password(args.username, args.password)
    elif args.command == "delete":
        do_delete(args.username)
    elif args.command == "assign":
        if args.cameras.strip().lower() == "all":
            all_cams = get_all_cameras()
            c_ids = [c["id"] for c in all_cams]
        elif args.cameras.strip().lower() == "none":
            c_ids = []
        else:
            c_ids = [x.strip() for x in args.cameras.split(",") if x.strip()]
        do_assign(args.username, c_ids)

    return 0


if __name__ == "__main__":
    sys.exit(main())
