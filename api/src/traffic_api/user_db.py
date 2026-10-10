from __future__ import annotations

import sqlite3
import time
from uuid import uuid4

from traffic_api.database import get_connection


def current_time_ms() -> int:
    return int(time.time() * 1000)


def ensure_user_table() -> None:
    """Ensure the USER table exists in the database."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS USER (
                id TEXT NOT NULL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        connection.commit()


def create_user(
    username: str,
    password_hash: str,
    user_id: str | None = None,
) -> dict:
    """Create a new user with a pre-computed password hash."""
    clean_username = username.strip().lower()
    uid = user_id or str(uuid4())
    now = current_time_ms()

    ensure_user_table()
    with get_connection() as connection:
        try:
            connection.execute(
                """
                INSERT INTO USER (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (uid, clean_username, password_hash, now),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"User '{clean_username}' already exists") from exc

    return {
        "id": uid,
        "username": clean_username,
        "created_at": now,
    }


def get_user_by_username(username: str) -> dict | None:
    """Look up a user by username (case-insensitive)."""
    ensure_user_table()
    clean_username = username.strip().lower()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, created_at
            FROM USER
            WHERE username = ?
            """,
            (clean_username,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    """Look up a user by UUID id."""
    ensure_user_table()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, created_at
            FROM USER
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def update_user_password(username: str, new_password_hash: str) -> bool:
    """Update password hash for a given user."""
    ensure_user_table()
    clean_username = username.strip().lower()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE USER
            SET password_hash = ?
            WHERE username = ?
            """,
            (new_password_hash, clean_username),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_user(username: str) -> bool:
    """Delete a user by username."""
    ensure_user_table()
    clean_username = username.strip().lower()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM USER
            WHERE username = ?
            """,
            (clean_username,),
        ).fetchone() if False else connection.execute(
            "DELETE FROM USER WHERE username = ?",
            (clean_username,),
        )
        connection.commit()
        return cursor.rowcount > 0


def list_users() -> list[dict]:
    """Return all users, omitting password hashes."""
    ensure_user_table()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, username, created_at
            FROM USER
            ORDER BY username ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def ensure_user_camera_table() -> None:
    """Ensure the USER_CAMERA junction table exists."""
    ensure_user_table()
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS USER_CAMERA (
                user_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, camera_id),
                FOREIGN KEY (user_id) REFERENCES USER (id) ON DELETE CASCADE,
                FOREIGN KEY (camera_id) REFERENCES CAMERA (id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def get_user_assigned_camera_ids(user_id: str) -> list[str]:
    """Return raw list of camera IDs linked to this user in USER_CAMERA."""
    ensure_user_camera_table()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT camera_id
            FROM USER_CAMERA
            WHERE user_id = ?
            ORDER BY camera_id ASC
            """,
            (user_id,),
        ).fetchall()
        return [r["camera_id"] for r in rows]


def get_user_camera_ids(user_id: str, username: str) -> list[str]:
    """
    Return accessible camera IDs for user.
    Admin user always has god-mode access to all cameras.
    """
    clean_username = username.strip().lower()
    if clean_username == "admin":
        from traffic_api.database import get_all_cameras
        return [c["id"] for c in get_all_cameras()]

    return get_user_assigned_camera_ids(user_id)


def set_user_cameras(user_id: str, camera_ids: list[str]) -> None:
    """Replace all camera assignments for a given user."""
    ensure_user_camera_table()
    now = current_time_ms()
    unique_ids = sorted({cid.strip() for cid in camera_ids if cid.strip()})

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM USER_CAMERA WHERE user_id = ?",
            (user_id,),
        )
        for cid in unique_ids:
            connection.execute(
                """
                INSERT INTO USER_CAMERA (user_id, camera_id, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, cid, now),
            )
        connection.commit()
