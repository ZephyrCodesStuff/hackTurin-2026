#!/usr/bin/env python3
"""Manage demo database state: wipe and seed realistic traffic camera data via API dogfooding."""

import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import random
import shutil
import sys
from uuid import UUID

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "src"))

from traffic_api.database import (
    DATABASE_PATH,
    PHOTOS_DIR,
    initialize_database,
)
from scripts.jwt import create_camera_token

# 1x1 transparent PNG for demo crash photos
DUMMY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Simulated realistic intersections (Berlin coordinates)
DEMO_CAMERAS = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Alexanderplatz North",
        "location": [52.5219, 13.4132],
        "state": "online",
        "battery_level": 94.5,
        "firmware_version": "2.1.0",
        "wifi_signal": -58,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "name": "Brandenburg Gate West",
        "location": [52.5163, 13.3777],
        "state": "online",
        "battery_level": 82.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -64,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "Potsdamer Platz Crossing",
        "location": [52.5096, 13.3759],
        "state": "online",
        "battery_level": 78.4,
        "firmware_version": "2.0.8",
        "wifi_signal": -71,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "name": "Kottbusser Tor Junction",
        "location": [52.4990, 13.4180],
        "state": "maintenance",
        "battery_level": 31.0,
        "firmware_version": "1.9.4",
        "wifi_signal": -82,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "name": "Friedrichstraße Station",
        "location": [52.5203, 13.3869],
        "state": "offline",
        "battery_level": 12.2,
        "firmware_version": "1.8.2",
        "wifi_signal": -90,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "name": "Checkpoint Charlie South",
        "location": [52.5075, 13.3904],
        "state": "online",
        "battery_level": 98.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -52,
    },
]


def cmd_nuke() -> None:
    """Completely wipe local database and photos directory, then recreate empty schema."""
    print("Nuking local database and demo assets...")
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print(f"  Removed {DATABASE_PATH}")

    # Remove any WAL or SHM files if present
    for suffix in ["-wal", "-shm"]:
        p = DATABASE_PATH.with_name(DATABASE_PATH.name + suffix)
        if p.exists():
            p.unlink()

    if PHOTOS_DIR.exists():
        shutil.rmtree(PHOTOS_DIR)
        print(f"  Removed {PHOTOS_DIR}")

    initialize_database()
    print("Database reset to clean state.")


def cmd_build(api_url: str, num_events_per_cam: int = 15, skip_nuke: bool = False) -> None:
    """Build and seed realistic simulated cameras and events exclusively via API HTTP requests."""
    api_url = api_url.rstrip("/")

    if not skip_nuke:
        # If targeting localhost, perform clean reset first
        if "localhost" in api_url or "127.0.0.1" in api_url:
            cmd_nuke()
        else:
            print(f"Targeting remote API ({api_url}); skipping local file wipe.")

    print(f"\nConnecting to API at: {api_url}")
    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        # Check health/reachability
        try:
            health = client.get("/")
            health.raise_for_status()
        except Exception as err:
            sys.exit(f"Failed to connect to API at {api_url}: {err}")

        # Sign a single camera token authorizing all demo cameras
        all_uuids = [UUID(c["id"]) for c in DEMO_CAMERAS]
        token = create_camera_token(
            subject="demo-data-seeder",
            camera_ids=all_uuids,
            expires_in=timedelta(hours=24),
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

        print(f"Seeding {len(DEMO_CAMERAS)} cameras through API endpoints...")

        now = datetime.now(timezone.utc)
        total_counts = {"crashes": 0, "light_changes": 0, "illegal_crossings": 0, "objects_detected": 0}

        for cam in DEMO_CAMERAS:
            cid = cam["id"]

            # 1. Dogfood Photo Upload if camera has a crash
            uploaded_photo_ids = []
            num_crashes = random.randint(0, 2)
            for _ in range(num_crashes):
                photo_resp = client.post(
                    f"/cameras/{cid}/photos",
                    headers={**auth_headers, "Content-Type": "image/png"},
                    content=DUMMY_PNG,
                )
                if photo_resp.status_code == 200:
                    uploaded_photo_ids.append(photo_resp.json()["photo_id"])
                else:
                    print(f"  [Warning] Photo upload failed for camera {cid}: {photo_resp.status_code}")

            # 2. Dogfood Batch Ingest endpoint
            events = []
            for photo_id in uploaded_photo_ids:
                events.append({
                    "type": "crash",
                    "photo_id": photo_id,
                    "timestamp": int((now - timedelta(minutes=random.randint(5, 720))).timestamp() * 1000),
                })

            for _ in range(num_events_per_cam):
                delta_mins = random.randint(1, 1440)
                event_time = int((now - timedelta(minutes=delta_mins)).timestamp() * 1000)
                event_type = random.choices(
                    ["light_change", "object_detected", "illegal_crossing"],
                    weights=[0.55, 0.35, 0.10],
                )[0]

                if event_type == "light_change":
                    color = random.choice(["red", "amber", "green"])
                    events.append({"type": "light_change", "color": color, "timestamp": event_time})
                elif event_type == "object_detected":
                    entity = random.choice(["car", "pedestrian", "bike", "motorbike", "truck", "animal"])
                    velocity = round(random.uniform(5.0, 75.0), 1)
                    events.append({
                        "type": "object_detected",
                        "entity_type": entity,
                        "velocity": velocity,
                        "timestamp": event_time,
                    })
                elif event_type == "illegal_crossing":
                    entity = random.choices(
                        ["pedestrian", "bike", "animal", "car", "motorbike"],
                        weights=[0.60, 0.20, 0.10, 0.05, 0.05],
                    )[0]
                    events.append({
                        "type": "illegal_crossing",
                        "entity_type": entity,
                        "timestamp": event_time,
                    })

            ingest_resp = client.post(
                f"/cameras/{cid}/ingest",
                headers=auth_headers,
                json={"events": events},
            )
            if ingest_resp.status_code != 200:
                sys.exit(f"API Ingest failed for camera {cid} ({ingest_resp.status_code}): {ingest_resp.text}")

            counts = ingest_resp.json()["counts"]
            for k, v in counts.items():
                total_counts[k] += v

            # 3. Dogfood Heartbeat endpoint
            last_hb = int(now.timestamp() * 1000) - random.randint(10, 180) * 1000
            last_ev = int(now.timestamp() * 1000) - random.randint(30, 600) * 1000

            hb_resp = client.post(
                f"/cameras/{cid}/heartbeat",
                headers=auth_headers,
                json={
                    "state": cam["state"],
                    "location": cam["location"],
                    "last_heartbeat": last_hb,
                    "last_event_timestamp": last_ev,
                    "battery_level": cam["battery_level"],
                    "firmware_version": cam["firmware_version"],
                    "wifi_signal": cam["wifi_signal"],
                },
            )
            if hb_resp.status_code != 200:
                sys.exit(f"API Heartbeat failed for camera {cid} ({hb_resp.status_code}): {hb_resp.text}")

            print(f"  ✓ {cam['name']}: {len(events)} events ingested, heartbeat broadcasted.")

        # 4. Dogfood public read endpoint to verify
        read_resp = client.get("/cameras")
        if read_resp.status_code == 200:
            cam_list = read_resp.json().get("cameras", [])
            print(f"\nVerification: {api_url}/cameras returned {len(cam_list)} cameras.")

    print("\nSummary of Ingested Data:")
    print(f"  Cameras Seeded:    {len(DEMO_CAMERAS)}")
    print(f"  Light Changes:     {total_counts['light_changes']}")
    print(f"  Objects Detected:  {total_counts['objects_detected']}")
    print(f"  Illegal Crossings: {total_counts['illegal_crossings']}")
    print(f"  Crashes & Photos:  {total_counts['crashes']}")
    print(f"\nDone! WebUI can now query {api_url}/cameras")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demo database management & API dogfooding tool (nuke/build).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: nuke
    subparsers.add_parser("nuke", help="Completely erase local database and uploaded photos.")

    # Subcommand: build
    build_parser = subparsers.add_parser(
        "build", help="Reset and seed realistic demo camera and event data via the API."
    )
    build_parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="Base URL of the Traffic Camera API (default: %(default)s or $API_URL)",
    )
    build_parser.add_argument(
        "--events-per-camera",
        type=int,
        default=15,
        help="Approximate events generated per camera (default: %(default)s)",
    )
    build_parser.add_argument(
        "--skip-nuke",
        action="store_true",
        help="Do not wipe local DB files before sending API requests.",
    )

    args = parser.parse_args()

    if args.command == "nuke":
        cmd_nuke()
    elif args.command == "build":
        cmd_build(
            api_url=args.api_url,
            num_events_per_cam=args.events_per_camera,
            skip_nuke=args.skip_nuke,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
