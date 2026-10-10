from __future__ import annotations

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


def _migrate_schema_columns(connection: sqlite3.Connection) -> None:
    """Add new columns to existing tables if missing."""
    camera_cols = {
        row["name"] for row in connection.execute("PRAGMA table_info(CAMERA)").fetchall()
    }
    new_camera_columns = [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("state", "TEXT NOT NULL DEFAULT 'online'"),
        ("last_heartbeat", "INTEGER"),
        ("last_event_timestamp", "INTEGER"),
        ("battery_level", "REAL"),
        ("firmware_version", "TEXT"),
        ("wifi_signal", "INTEGER"),
    ]
    for col_name, col_def in new_camera_columns:
        if col_name not in camera_cols:
            connection.execute(f"ALTER TABLE CAMERA ADD COLUMN {col_name} {col_def}")

    crossing_cols = {
        row["name"] for row in connection.execute("PRAGMA table_info(ILLEGAL_CROSSING)").fetchall()
    }
    if "entity_type" not in crossing_cols:
        connection.execute("ALTER TABLE ILLEGAL_CROSSING ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'pedestrian'")

    object_cols = {
        row["name"] for row in connection.execute("PRAGMA table_info(OBJECT_DETECTED)").fetchall()
    }
    if "entity_type" not in object_cols:
        connection.execute("ALTER TABLE OBJECT_DETECTED ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'car'")


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
        _migrate_schema_columns(connection)


def reset_database() -> None:
    """Clear all records from database and delete stored photos while server remains online."""
    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("DELETE FROM CRASH")
        connection.execute("DELETE FROM LIGHT_CHANGE")
        connection.execute("DELETE FROM ILLEGAL_CROSSING")
        connection.execute("DELETE FROM OBJECT_DETECTED")
        connection.execute("DELETE FROM CAMERA")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()
        connection.execute("VACUUM")

    if PHOTOS_DIR.exists():
        for item in PHOTOS_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except OSError:
                    pass


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


def update_camera_heartbeat(
    camera_id: str,
    state: str,
    name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    last_heartbeat: int | None = None,
    last_event_timestamp: int | None = None,
    battery_level: float | None = None,
    firmware_version: str | None = None,
    wifi_signal: int | None = None,
) -> dict:
    """Upsert camera heartbeat and return updated camera record."""
    camera_name = name if name else f"Camera {camera_id[:8]}"
    camera_location = f"({latitude}, {longitude})" if latitude is not None and longitude is not None else "Unknown"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO CAMERA (
                id, name, location, latitude, longitude, state,
                last_heartbeat, last_event_timestamp, battery_level,
                firmware_version, wifi_signal
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                state = excluded.state,
                name = case when ? is not null then ? else CAMERA.name end,
                latitude = coalesce(excluded.latitude, CAMERA.latitude),
                longitude = coalesce(excluded.longitude, CAMERA.longitude),
                location = case
                    when excluded.latitude is not null and excluded.longitude is not null
                    then excluded.location
                    else CAMERA.location
                end,
                last_heartbeat = coalesce(excluded.last_heartbeat, CAMERA.last_heartbeat),
                last_event_timestamp = coalesce(excluded.last_event_timestamp, CAMERA.last_event_timestamp),
                battery_level = coalesce(excluded.battery_level, CAMERA.battery_level),
                firmware_version = coalesce(excluded.firmware_version, CAMERA.firmware_version),
                wifi_signal = coalesce(excluded.wifi_signal, CAMERA.wifi_signal)
            """,
            (
                camera_id,
                camera_name,
                camera_location,
                latitude,
                longitude,
                state,
                last_heartbeat,
                last_event_timestamp,
                battery_level,
                firmware_version,
                wifi_signal,
                name,
                name,
            ),
        )
    return get_camera_by_id(camera_id)  # type: ignore


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
                entity_val = event.entity_type.value if hasattr(event.entity_type, "value") else str(event.entity_type)
                connection.execute(
                    """
                    INSERT INTO ILLEGAL_CROSSING (entity_type, timestamp, CAMERA_id)
                    VALUES (?, ?, ?)
                    """,
                    (entity_val, event.timestamp, camera_id),
                )
                counts["illegal_crossings"] += 1
            elif event_type == "object_detected":
                entity_val = event.entity_type.value if hasattr(event.entity_type, "value") else str(event.entity_type)
                connection.execute(
                    """
                    INSERT INTO OBJECT_DETECTED (entity_type, velocity, timestamp, CAMERA_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (entity_val, event.velocity, event.timestamp, camera_id),
                )
                counts["objects_detected"] += 1

    return counts


def _format_camera_row(row: sqlite3.Row) -> dict:
    """Format camera row for API output, packaging lat/lon as a location tuple/list."""
    d = dict(row)
    lat = d.pop("latitude", None)
    lon = d.pop("longitude", None)
    if lat is not None and lon is not None:
        d["location"] = [lat, lon]
    elif d.get("location") and d["location"] != "Unknown":
        d["location"] = d["location"]
    else:
        d["location"] = None
    # Classify the camera by whether it has ever reported a traffic-light change.
    # A camera that has never emitted a LIGHT_CHANGE (current_light is NULL) is
    # treated as monitoring an unsignalized crossing ("camera"); otherwise it is
    # a signalized "traffic_light" camera.
    d["camera_type"] = "traffic_light" if d.get("current_light") is not None else "camera"
    return d


def get_all_cameras() -> list[dict]:
    """Return all registered cameras with current traffic light status."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, location, latitude, longitude, state,
                   last_heartbeat, last_event_timestamp, battery_level,
                   firmware_version, wifi_signal,
                   (
                       SELECT color
                       FROM LIGHT_CHANGE
                       WHERE CAMERA_id = CAMERA.id
                       ORDER BY timestamp DESC, id DESC
                       LIMIT 1
                   ) AS current_light,
                   (
                       SELECT timestamp
                       FROM LIGHT_CHANGE
                       WHERE CAMERA_id = CAMERA.id
                       ORDER BY timestamp DESC, id DESC
                       LIMIT 1
                   ) AS current_light_timestamp
            FROM CAMERA
            ORDER BY name
            """
        ).fetchall()
        return [_format_camera_row(row) for row in rows]


def get_camera_by_id(camera_id: str) -> dict | None:
    """Return a single camera by ID with current traffic light status."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, location, latitude, longitude, state,
                   last_heartbeat, last_event_timestamp, battery_level,
                   firmware_version, wifi_signal,
                   (
                       SELECT color
                       FROM LIGHT_CHANGE
                       WHERE CAMERA_id = CAMERA.id
                       ORDER BY timestamp DESC, id DESC
                       LIMIT 1
                   ) AS current_light,
                   (
                       SELECT timestamp
                       FROM LIGHT_CHANGE
                       WHERE CAMERA_id = CAMERA.id
                       ORDER BY timestamp DESC, id DESC
                       LIMIT 1
                   ) AS current_light_timestamp
            FROM CAMERA
            WHERE id = ?
            """,
            (camera_id,),
        ).fetchone()
        return _format_camera_row(row) if row else None


def get_camera_events(camera_id: str) -> list[dict]:
    """Return all events captured by a camera, merged and sorted chronologically (descending)."""
    events = []
    with get_connection() as connection:
        # Crashes
        rows = connection.execute(
            "SELECT id, photo_id, timestamp FROM CRASH WHERE CAMERA_id = ?",
            (camera_id,),
        ).fetchall()
        for r in rows:
            events.append({
                "type": "crash",
                "id": r["id"],
                "photo_id": r["photo_id"],
                "timestamp": r["timestamp"],
            })

        # Light changes
        rows = connection.execute(
            "SELECT id, color, timestamp FROM LIGHT_CHANGE WHERE CAMERA_id = ?",
            (camera_id,),
        ).fetchall()
        for r in rows:
            events.append({
                "type": "light_change",
                "id": r["id"],
                "color": r["color"],
                "timestamp": r["timestamp"],
            })

        # Illegal crossings
        rows = connection.execute(
            "SELECT id, entity_type, timestamp FROM ILLEGAL_CROSSING WHERE CAMERA_id = ?",
            (camera_id,),
        ).fetchall()
        for r in rows:
            events.append({
                "type": "illegal_crossing",
                "id": r["id"],
                "entity_type": r["entity_type"],
                "timestamp": r["timestamp"],
            })

        # Objects detected
        rows = connection.execute(
            "SELECT id, entity_type, velocity, timestamp FROM OBJECT_DETECTED WHERE CAMERA_id = ?",
            (camera_id,),
        ).fetchall()
        for r in rows:
            events.append({
                "type": "object_detected",
                "id": r["id"],
                "entity_type": r["entity_type"],
                "velocity": r["velocity"],
                "timestamp": r["timestamp"],
            })

    # Sort newest first
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events
