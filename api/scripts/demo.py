#!/usr/bin/env python3
"""Manage demo database state: wipe and seed realistic traffic camera data via API dogfooding."""

import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import random
import shutil
import sys
import time
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

RESOURCES_DIR = SCRIPT_DIR / "resources"


def get_random_crash_photo() -> tuple[bytes, str]:
    """Return raw bytes and content-type of a randomly selected crash photo from resources/."""
    if RESOURCES_DIR.exists():
        sample_files = [
            p for p in RESOURCES_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if sample_files:
            chosen = random.choice(sample_files)
            ext = chosen.suffix.lower()
            if ext == ".png":
                content_type = "image/png"
            elif ext == ".webp":
                content_type = "image/webp"
            else:
                content_type = "image/jpeg"
            return chosen.read_bytes(), content_type

    # Fallback 1x1 transparent PNG if resources/ is missing
    dummy_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return dummy_png, "image/png"


# Realistic major intersections across Turin (Torino, Italy)
DEMO_CAMERAS = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Piazza Castello / Via Po",
        "location": [45.0710, 7.6865],
        "state": "online",
        "battery_level": 94.5,
        "firmware_version": "2.1.0",
        "wifi_signal": -58,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "name": "Piazza San Carlo / Via Roma",
        "location": [45.0678, 7.6825],
        "state": "online",
        "battery_level": 82.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -64,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "Piazza Vittorio Veneto",
        "location": [45.0645, 7.6953],
        "state": "online",
        "battery_level": 78.4,
        "firmware_version": "2.0.8",
        "wifi_signal": -71,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "name": "Porta Nuova / Corso Vittorio",
        "location": [45.0620, 7.6780],
        "state": "online",
        "battery_level": 88.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -62,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "name": "Porta Susa / C.so Inghilterra",
        "location": [45.0725, 7.6655],
        "state": "online",
        "battery_level": 91.2,
        "firmware_version": "2.1.0",
        "wifi_signal": -66,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "name": "Piazza Statuto",
        "location": [45.0768, 7.6713],
        "state": "maintenance",
        "battery_level": 31.0,
        "firmware_version": "1.9.4",
        "wifi_signal": -82,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440007",
        "name": "Rondò della Forca / C.so Regina",
        "location": [45.0815, 7.6775],
        "state": "online",
        "battery_level": 96.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -55,
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440008",
        "name": "Piazza Bernini / Corso Francia",
        "location": [45.0755, 7.6525],
        "state": "offline",
        "battery_level": 12.2,
        "firmware_version": "1.8.2",
        "wifi_signal": -90,
    },
]


def cmd_nuke(api_url: str = "http://localhost:8000") -> None:
    """Wipe database and photos via API endpoint, with fallback to local files if targeting localhost."""
    api_url = api_url.rstrip("/")
    print(f"Nuking API database and demo photos via {api_url}/nuke...")

    all_uuids = [UUID(c["id"]) for c in DEMO_CAMERAS]
    token = create_camera_token(
        subject="demo-admin-nuker",
        camera_ids=all_uuids,
        expires_in=timedelta(minutes=15),
    )

    nuked_via_api = False
    try:
        with httpx.Client(base_url=api_url, timeout=10.0) as client:
            resp = client.post("/nuke", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                print(f"  ✓ Database wiped successfully via API: {resp.json().get('message')}")
                nuked_via_api = True
            else:
                print(f"  [Notice] API /nuke returned HTTP {resp.status_code}: {resp.text}")
    except Exception as err:
        print(f"  [Notice] Could not reach API /nuke directly: {err}")

    # If targeting local instance and API /nuke was not reached, do local disk cleanup
    if not nuked_via_api and ("localhost" in api_url or "127.0.0.1" in api_url):
        print("  Falling back to local disk reset...")
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
            print(f"  Removed {DATABASE_PATH}")

        for suffix in ["-wal", "-shm"]:
            p = DATABASE_PATH.with_name(DATABASE_PATH.name + suffix)
            if p.exists():
                p.unlink()

        if PHOTOS_DIR.exists():
            shutil.rmtree(PHOTOS_DIR)
            print(f"  Removed {PHOTOS_DIR}")

        initialize_database()
        print("Local database reset to clean state.")


def cmd_build(api_url: str, num_events_per_cam: int = 15, skip_nuke: bool = False) -> None:
    """Build and seed realistic simulated cameras and events exclusively via API HTTP requests."""
    api_url = api_url.rstrip("/")

    if not skip_nuke:
        cmd_nuke(api_url=api_url)

    print(f"\nConnecting to API at: {api_url}")
    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        try:
            health = client.get("/")
            health.raise_for_status()
        except Exception as err:
            sys.exit(f"Failed to connect to API at {api_url}: {err}")

        all_uuids = [UUID(c["id"]) for c in DEMO_CAMERAS]
        token = create_camera_token(
            subject="demo-data-seeder",
            camera_ids=all_uuids,
            expires_in=timedelta(hours=24),
        )
        auth_headers = {"Authorization": f"Bearer {token}"}

        print(f"Seeding {len(DEMO_CAMERAS)} Turin intersections through API endpoints...")

        now = datetime.now(timezone.utc)
        total_counts = {"crashes": 0, "light_changes": 0, "illegal_crossings": 0, "objects_detected": 0}

        # Colors pool so cameras start with diverse active traffic lights
        initial_colors = ["green", "red", "green", "amber", "green", "red", "green", "red"]

        for idx, cam in enumerate(DEMO_CAMERAS):
            cid = cam["id"]

            # 1. Dogfood Photo Upload if camera has a crash
            uploaded_photo_ids = []
            num_crashes = random.randint(0, 2)
            for _ in range(num_crashes):
                photo_data, content_type = get_random_crash_photo()
                photo_resp = client.post(
                    f"/cameras/{cid}/photos",
                    headers={**auth_headers, "Content-Type": content_type},
                    content=photo_data,
                )
                if photo_resp.status_code == 200:
                    uploaded_photo_ids.append(photo_resp.json()["photo_id"])
                else:
                    print(f"  [Warning] Photo upload failed for camera {cid}: {photo_resp.status_code}")

            # 2. Historical Events
            events = []
            for photo_id in uploaded_photo_ids:
                events.append({
                    "type": "crash",
                    "photo_id": photo_id,
                    "timestamp": int((now - timedelta(minutes=random.randint(15, 720))).timestamp() * 1000),
                })

            for _ in range(num_events_per_cam):
                delta_mins = random.randint(2, 1440)
                event_time = int((now - timedelta(minutes=delta_mins)).timestamp() * 1000)
                event_type = random.choices(
                    ["light_change", "object_detected", "illegal_crossing"],
                    weights=[0.50, 0.38, 0.12],
                )[0]

                if event_type == "light_change":
                    color = random.choice(["red", "amber", "green"])
                    events.append({"type": "light_change", "color": color, "timestamp": event_time})
                elif event_type == "object_detected":
                    entity = random.choice(["car", "pedestrian", "bike", "motorbike", "truck", "animal"])
                    velocity = round(random.uniform(15.0, 65.0), 1)
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

            # Ensure the MOST RECENT event is a light_change with current active color
            active_color = initial_colors[idx % len(initial_colors)]
            latest_light_time = int((now - timedelta(seconds=random.randint(5, 45))).timestamp() * 1000)
            events.append({
                "type": "light_change",
                "color": active_color,
                "timestamp": latest_light_time,
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

            # 3. Dogfood Heartbeat endpoint with Camera Name
            last_hb = int(now.timestamp() * 1000) - random.randint(5, 60) * 1000
            last_ev = latest_light_time

            hb_resp = client.post(
                f"/cameras/{cid}/heartbeat",
                headers=auth_headers,
                json={
                    "name": cam["name"],
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

            print(f"  ✓ {cam['name']}: {len(events)} events ingested (Active: {active_color.upper()}).")

        # 4. Verify
        read_resp = client.get("/cameras")
        if read_resp.status_code == 200:
            cam_list = read_resp.json().get("cameras", [])
            print(f"\nVerification: {api_url}/cameras returned {len(cam_list)} cameras in Turin.")

    print("\nSummary of Ingested Turin Data:")
    print(f"  Cameras Seeded:    {len(DEMO_CAMERAS)}")
    print(f"  Light Changes:     {total_counts['light_changes']}")
    print(f"  Objects Detected:  {total_counts['objects_detected']}")
    print(f"  Illegal Crossings: {total_counts['illegal_crossings']}")
    print(f"  Crashes & Photos:  {total_counts['crashes']}")
    print(f"\nDone! WebUI can now query {api_url}/cameras")


def cmd_live(api_url: str, interval: float = 3.5) -> None:
    """Continuously cycle traffic light colors and heartbeats in real-time for live demo showcase."""
    api_url = api_url.rstrip("/")
    print(f"Starting real-time traffic signal simulator on: {api_url}")
    print(f"Cycle interval: {interval}s (Press Ctrl+C to stop)\n")

    all_uuids = [UUID(c["id"]) for c in DEMO_CAMERAS]
    token = create_camera_token(
        subject="live-signal-simulator",
        camera_ids=all_uuids,
        expires_in=timedelta(hours=24),
    )
    auth_headers = {"Authorization": f"Bearer {token}"}

    next_colors = {"green": "amber", "amber": "red", "red": "green"}
    # Current state tracking per camera
    cam_state = {c["id"]: random.choice(["green", "amber", "red"]) for c in DEMO_CAMERAS}

    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        iteration = 0
        while True:
            iteration += 1
            # Pick 1-3 cameras to change light
            active_cams = [c for c in DEMO_CAMERAS if c["state"] != "offline"]
            chosen_cams = random.sample(active_cams, k=min(len(active_cams), random.randint(1, 3)))
            now_ms = int(time.time() * 1000)

            for cam in chosen_cams:
                cid = cam["id"]
                current = cam_state[cid]
                new_color = next_colors[current]
                cam_state[cid] = new_color

                # Post new light change
                client.post(
                    f"/cameras/{cid}/ingest",
                    headers=auth_headers,
                    json={
                        "events": [
                            {"type": "light_change", "color": new_color, "timestamp": now_ms}
                        ]
                    },
                )

                # Broadcast heartbeat
                client.post(
                    f"/cameras/{cid}/heartbeat",
                    headers=auth_headers,
                    json={
                        "name": cam["name"],
                        "state": cam["state"],
                        "location": cam["location"],
                        "last_heartbeat": now_ms,
                        "last_event_timestamp": now_ms,
                        "battery_level": cam["battery_level"],
                        "firmware_version": cam["firmware_version"],
                        "wifi_signal": cam["wifi_signal"],
                    },
                )

                timestamp_str = datetime.now().strftime("%H:%M:%S")
                color_symbol = "🟢" if new_color == "green" else "🟡" if new_color == "amber" else "🔴"
                print(f"[{timestamp_str}] {color_symbol} {cam['name']}: changed to {new_color.upper()}")

            time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demo database management & API dogfooding tool for Turin traffic grid.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: nuke
    nuke_parser = subparsers.add_parser(
        "nuke", help="Completely erase database and uploaded photos via API."
    )
    nuke_parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="Base URL of the Traffic Camera API (default: %(default)s or $API_URL)",
    )

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

    # Subcommand: live
    live_parser = subparsers.add_parser(
        "live", help="Run a live traffic light cycle simulation broadcasting events in real-time."
    )
    live_parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="Base URL of the Traffic Camera API (default: %(default)s)",
    )
    live_parser.add_argument(
        "--interval",
        type=float,
        default=3.5,
        help="Seconds between traffic light changes (default: 3.5s)",
    )

    args = parser.parse_args()

    if args.command == "nuke":
        cmd_nuke(api_url=args.api_url)
    elif args.command == "build":
        cmd_build(
            api_url=args.api_url,
            num_events_per_cam=args.events_per_camera,
            skip_nuke=args.skip_nuke,
        )
    elif args.command == "live":
        cmd_live(api_url=args.api_url, interval=args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
