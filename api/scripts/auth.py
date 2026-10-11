#!/usr/bin/env python3
"""Create a locally signed, camera-scoped JWT without calling the API."""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

# Make the local src package importable when this script is run directly.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != SCRIPT_DIR]
sys.path.insert(0, str(PROJECT_DIR / "src"))

import jwt  # noqa: E402
from traffic_api.auth import (  # noqa: E402
    CAMERA_JWT_ALGORITHM,
    CAMERA_JWT_ISSUER,
    get_camera_jwt_secret,
    normalize_camera_ids,
)


from typing import Optional

def create_camera_token(
    subject: str,
    camera_ids: list[UUID],
    expires_in: timedelta,
    secret: Optional[str] = None,
):
    """Sign a camera token locally using the symmetric CAMERA_JWT_SECRET string or provided secret."""
    if not subject:
        raise ValueError("JWT subject must not be empty")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iss": CAMERA_JWT_ISSUER,
        "iat": now,
        "exp": now + expires_in,
        "authorized_camera_ids": normalize_camera_ids(camera_ids),
        "type": "camera_token",
    }
    signing_secret = secret or get_camera_jwt_secret()
    return jwt.encode(payload, signing_secret, algorithm=CAMERA_JWT_ALGORITHM)


import getpass
from typing import Optional
import httpx

from traffic_api.auth_user import compute_client_hash


def cmd_login(
    api_url: str,
    username: str,
    password: Optional[str] = None,
    token_only: bool = False,
) -> int:
    """Log in to a local or remote API instance using client-side PBKDF2 hashing and output the session token."""
    api_url = api_url.rstrip("/")
    clean_username = username.strip().lower()

    if password is None:
        if sys.stdin.isatty():
            password = getpass.getpass(f"Password for '{clean_username}' (default: admin): ") or "admin"
        else:
            password = "admin"

    client_hash = compute_client_hash(clean_username, password)

    try:
        with httpx.Client(base_url=api_url, timeout=15.0, follow_redirects=True) as client:
            resp = client.post(
                "/auth/login",
                json={"username": clean_username, "client_hash": client_hash},
            )
            if resp.status_code != 200:
                print(
                    f"Login failed (HTTP {resp.status_code}): {resp.text}",
                    file=sys.stderr,
                )
                return 1

            data = resp.json()
            token = data.get("token")
            user_info = data.get("user", {})

            if token_only:
                print(token)
                return 0

            print(f"✓ Authenticated successfully as '{user_info.get('username', clean_username)}' on {api_url}")
            print(f"User ID:  {user_info.get('id', 'unknown')}")
            print(f"Token:    {token}\n")
            print("Quick verification:")
            print(f"  curl -H 'Authorization: Bearer {token}' {api_url}/auth/me")
            return 0
    except Exception as err:
        print(f"Could not connect to {api_url}: {err}", file=sys.stderr)
        return 1


def parse_camera_ids(value: str) -> list[UUID]:
    """Parse a comma-separated UUIDv4 camera-ID list."""
    values = [camera_id.strip() for camera_id in value.split(",") if camera_id.strip()]
    if not values:
        raise argparse.ArgumentTypeError("provide at least one camera UUID")

    try:
        camera_ids = [UUID(camera_id) for camera_id in values]
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "camera IDs must be comma-separated UUIDs"
        ) from error

    if any(camera_id.version != 4 for camera_id in camera_ids):
        raise argparse.ArgumentTypeError("camera IDs must be UUIDv4 values")
    return camera_ids


def main() -> int:
    # 1. Subcommand: login
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login_parser = argparse.ArgumentParser(
            prog="auth.py login",
            description="Log in to local or remote API using PBKDF2 client hashing and retrieve a user session token.",
        )
        login_parser.add_argument(
            "--api-url",
            default=os.environ.get("API_URL", "http://localhost:8000"),
            help="Base URL of the Traffic Camera API (default: %(default)s or $API_URL)",
        )
        login_parser.add_argument(
            "-u",
            "--username",
            default="admin",
            help="Username to log in as (default: admin)",
        )
        login_parser.add_argument(
            "-p",
            "--password",
            default=None,
            help="Password (default: admin or interactive prompt)",
        )
        login_parser.add_argument(
            "--token-only",
            action="store_true",
            help="Print only the bearer token string (useful for: TOKEN=$(auth.py login --token-only))",
        )
        login_args = login_parser.parse_args(sys.argv[2:])
        return cmd_login(
            api_url=login_args.api_url,
            username=login_args.username,
            password=login_args.password,
            token_only=login_args.token_only,
        )

    # 2. Camera token generator (default or via 'camera' keyword)
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] == "camera":
        raw_args = raw_args[1:]

    parser = argparse.ArgumentParser(
        description="Create a camera-scoped JWT token for embedded devices, or log in to the API.",
        epilog=(
            "Commands:\n"
            "  auth.py <camera_ids>         Generate hardware token for camera device(s)\n"
            "  auth.py login [options]      Log in as human user via PBKDF2 client hashing\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "camera_ids",
        type=parse_camera_ids,
        help="comma-separated UUIDv4 camera IDs",
    )
    parser.add_argument(
        "--subject",
        default="local-camera-authorizer",
        help="JWT subject identifying the device or client (default: %(default)s)",
    )
    parser.add_argument(
        "--expires-hours",
        type=float,
        default=24,
        help="token lifetime in hours (default: %(default)s)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="signing secret key (defaults to $CAMERA_JWT_SECRET or repo demo secret)",
    )
    args = parser.parse_args(raw_args)

    if args.expires_hours <= 0:
        parser.error("--expires-hours must be greater than zero")

    try:
        token = create_camera_token(
            subject=args.subject,
            camera_ids=args.camera_ids,
            expires_in=timedelta(hours=args.expires_hours),
            secret=args.secret,
        )
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
