"""SQLite setup and connection helpers for the API."""

import sqlite3
from pathlib import Path

# database.py lives at src/traffic_api/, so the project root is two levels up.
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_DIR / "data" / "traffic.db"
PHOTOS_DIR = PROJECT_DIR / "data" / "photos"
SCHEMA_PATH = PROJECT_DIR / "schema.sql"


def _schema_is_current(connection: sqlite3.Connection) -> bool:
    """Check the columns whose types changed in the initial schema."""
    camera_columns = {
        row["name"]: row["type"]
        for row in connection.execute("PRAGMA table_info(CAMERA)")
    }
    return (
        "token" not in camera_columns
        and camera_columns.get("id") == "TEXT"
        and camera_columns.get("name") == "TEXT"
        and camera_columns.get("location") == "TEXT"
    )


def get_connection() -> sqlite3.Connection:
    """Return a connection with SQLite foreign-key checks enabled."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the local database and all tables if they do not exist yet."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        has_camera_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'CAMERA'"
        ).fetchone()
        if has_camera_table and not _schema_is_current(connection):
            raise RuntimeError(
                "The local database uses an older schema. Back it up if needed, "
                "then delete data/traffic.db and restart the API."
            )
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def upsert_camera(camera_id: str, name: str, location: str) -> bool:
    """Insert or update a camera record. Returns True if a new row was inserted."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO CAMERA (id, name, location)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                location = excluded.location
            """,
            (camera_id, name, location),
        )
        return cursor.rowcount > 0


def insert_events(camera_id: str, events: list) -> dict[str, int]:
    """Insert a heterogeneous list of events for the specified camera in a single transaction."""
    counts = {
        "crashes": 0,
        "light_changes": 0,
        "illegal_crossings": 0,
        "objects_detected": 0,
    }

    with get_connection() as connection:
        for event in events:
            event_type = getattr(event, "type", None) or event.get("type")
            if event_type == "crash":
                connection.execute(
                    """
                    INSERT INTO CRASH (photo_id, timestamp, CAMERA_id)
                    VALUES (?, ?, ?)
                    """,
                    (str(event.photo_id), event.timestamp, camera_id),
                )
                counts["crashes"] += 1
            elif event_type == "light_change":
                color_val = event.color.value if hasattr(event.color, "value") else str(event.color)
                connection.execute(
                    """
                    INSERT INTO LIGHT_CHANGE (color, timestamp, CAMERA_id)
                    VALUES (?, ?, ?)
                    """,
                    (color_val, event.timestamp, camera_id),
                )
                counts["light_changes"] += 1
            elif event_type == "illegal_crossing":
                connection.execute(
                    """
                    INSERT INTO ILLEGAL_CROSSING (timestamp, CAMERA_id)
                    VALUES (?, ?)
                    """,
                    (event.timestamp, camera_id),
                )
                counts["illegal_crossings"] += 1
            elif event_type == "object_detected":
                connection.execute(
                    """
                    INSERT INTO OBJECT_DETECTED (velocity, timestamp, CAMERA_id)
                    VALUES (?, ?, ?)
                    """,
                    (event.velocity, event.timestamp, camera_id),
                )
                counts["objects_detected"] += 1

    return counts
