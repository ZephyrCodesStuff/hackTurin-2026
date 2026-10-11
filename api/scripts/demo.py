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
from traffic_api.auth_user import seed_default_admin_if_needed
from traffic_api.user_db import get_user_by_username, set_user_cameras
from scripts.auth import create_camera_token

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
        "location": [45.0705, 7.6864],
        "state": "online",
        "battery_level": 94.5,
        "firmware_version": "2.1.0",
        "wifi_signal": -58,
        "zone": "historic_center",
        "crashes": [
            {
                "status": "resolved",
                "offset_mins": 360,
                "resolution_offset_mins": 330,
                "units": [1, 6],  # Polizia Locale, Soccorso Stradale
                "notes": "Minor fender-bender at tram crossing, cleared promptly",
            }
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "name": "Piazza San Carlo / Via Roma",
        "location": [45.0679, 7.6827],
        "state": "online",
        "battery_level": 88.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -64,
        "zone": "pedestrian_plaza",
        "crashes": [],  # Completely pedestrianized plaza: 0 crashes
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "Piazza Vittorio Veneto / Lungo Po",
        "location": [45.0652, 7.6948],
        "state": "online",
        "battery_level": 78.4,
        "firmware_version": "2.0.8",
        "wifi_signal": -71,
        "zone": "historic_riverfront",
        "crashes": [
            {
                "status": "resolved",
                "offset_mins": 480,
                "resolution_offset_mins": 440,
                "units": [1, 2],  # Polizia Locale, Emergenza Sanitaria
                "notes": "Scooter sideswipe, medical check completed on scene",
            }
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "name": "Porta Nuova / Corso Vittorio Emanuele II",
        "location": [45.0627, 7.6788],
        "state": "online",
        "battery_level": 88.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -62,
        "zone": "railway_hub_arterial",
        "crashes": [
            {
                "status": "active",
                "offset_mins": 22,
                "notes": "Multi-vehicle rear-end collision blocking tram lane",
            },
            {
                "status": "resolved",
                "offset_mins": 420,
                "resolution_offset_mins": 380,
                "units": [1, 6],
                "notes": "Vehicle stall at intersection, towed",
            },
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "name": "Porta Susa / Corso Inghilterra",
        "location": [45.0718, 7.6652],
        "state": "online",
        "battery_level": 91.2,
        "firmware_version": "2.1.0",
        "wifi_signal": -66,
        "zone": "railway_hub_arterial",
        "crashes": [
            {
                "status": "resolved",
                "offset_mins": 240,
                "resolution_offset_mins": 210,
                "units": [1, 6],
                "notes": "Taxi scrape against guard rail",
            }
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "name": "Piazza Statuto / Sottopasso",
        "location": [45.0760, 7.6710],
        "state": "maintenance",
        "battery_level": 31.0,
        "firmware_version": "1.9.4",
        "wifi_signal": -82,
        "zone": "underpass_roundabout",
        "crashes": [
            {
                "status": "resolved",
                "offset_mins": 840,
                "resolution_offset_mins": 780,
                "units": [1, 3],  # Polizia Locale, Vigili del Fuoco
                "notes": "Debris in underpass cleared by fire department",
            }
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440007",
        "name": "Rondò della Forca / Corso Regina Margherita",
        "location": [45.0793, 7.6767],
        "state": "online",
        "battery_level": 96.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -55,
        "zone": "high_risk_junction",
        "crashes": [
            {
                "status": "active",
                "offset_mins": 9,
                "notes": "T-bone collision between sedan and delivery scooter on tram crossing",
            },
            {
                "status": "in_progress",
                "offset_mins": 20,
                "resolution_offset_mins": 4,
                "units": [1, 2, 3],  # Polizia Locale, Emergenza Sanitaria, Vigili del Fuoco
                "notes": "Major multi-car collision with fuel leak, units actively on-site",
            },
            {
                "status": "resolved",
                "offset_mins": 600,
                "resolution_offset_mins": 540,
                "units": [1, 6],
                "notes": "Tram signal miscommunication accident, resolved",
            },
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440008",
        "name": "Piazza Bernini / Corso Francia",
        "location": [45.0758, 7.6563],
        "state": "offline",
        "battery_level": 12.2,
        "firmware_version": "1.8.2",
        "wifi_signal": -90,
        "zone": "residential_arterial",
        "crashes": [],  # Orderly Metro-1 residential boulevard: 0 crashes
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440009",
        "name": "Corso Novara / Corso Regio Parco",
        "location": [45.0798, 7.7003],
        "state": "online",
        "battery_level": 89.5,
        "firmware_version": "2.1.0",
        "wifi_signal": -68,
        "zone": "industrial_freight_arterial",
        "crashes": [
            {
                "status": "in_progress",
                "offset_mins": 18,
                "resolution_offset_mins": 6,
                "units": [1, 3, 6],  # Polizia Locale, Vigili del Fuoco, Soccorso Stradale
                "notes": "Articulated truck jackknife, heavy towing unit dispatched",
            },
            {
                "status": "resolved",
                "offset_mins": 720,
                "resolution_offset_mins": 660,
                "units": [1, 6],
                "notes": "Delivery van breakdown blocking lane 1, removed",
            },
        ],
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440010",
        "name": "Corso Unione Sovietica / Corso Sebastopoli",
        "location": [45.04135, 7.6562],
        "state": "online",
        "battery_level": 93.0,
        "firmware_version": "2.1.0",
        "wifi_signal": -60,
        "zone": "major_avenue_tram",
        "crashes": [
            {
                "status": "active",
                "offset_mins": 14,
                "notes": "High speed red-light violation collision at tram track junction",
            }
        ],
    },
]

ZONE_PROFILES = {
    "pedestrian_plaza": {
        "allowed_entities": [("pedestrian", 0.88), ("bike", 0.12)],
        "speed_ranges": {
            "pedestrian": (3.0, 5.8),
            "bike": (8.0, 15.0),
        },
        "illegal_entities": [("bike", 1.0)],
        "illegal_rate": 0.04,
    },
    "historic_center": {
        "allowed_entities": [
            ("pedestrian", 0.35),
            ("bike", 0.25),
            ("car", 0.25),
            ("motorbike", 0.15),
        ],
        "speed_ranges": {
            "pedestrian": (3.2, 5.8),
            "bike": (10.0, 20.0),
            "car": (16.0, 32.0),
            "motorbike": (18.0, 34.0),
        },
        "illegal_entities": [("pedestrian", 0.70), ("bike", 0.30)],
        "illegal_rate": 0.10,
    },
    "historic_riverfront": {
        "allowed_entities": [
            ("car", 0.35),
            ("motorbike", 0.25),
            ("bike", 0.20),
            ("pedestrian", 0.20),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 6.0),
            "bike": (12.0, 22.0),
            "car": (22.0, 42.0),
            "motorbike": (24.0, 45.0),
        },
        "illegal_entities": [("pedestrian", 0.50), ("bike", 0.30), ("motorbike", 0.20)],
        "illegal_rate": 0.12,
    },
    "railway_hub_arterial": {
        "allowed_entities": [
            ("car", 0.50),
            ("motorbike", 0.18),
            ("pedestrian", 0.16),
            ("bike", 0.10),
            ("truck", 0.06),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 6.2),
            "bike": (12.0, 22.0),
            "car": (28.0, 52.0),
            "motorbike": (30.0, 56.0),
            "truck": (24.0, 42.0),
        },
        "illegal_entities": [("pedestrian", 0.65), ("bike", 0.20), ("car", 0.15)],
        "illegal_rate": 0.14,
    },
    "underpass_roundabout": {
        "allowed_entities": [
            ("car", 0.65),
            ("motorbike", 0.20),
            ("truck", 0.10),
            ("pedestrian", 0.05),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 5.5),
            "car": (30.0, 52.0),
            "motorbike": (32.0, 55.0),
            "truck": (26.0, 44.0),
        },
        "illegal_entities": [("car", 0.50), ("motorbike", 0.40), ("pedestrian", 0.10)],
        "illegal_rate": 0.10,
    },
    "high_risk_junction": {
        "allowed_entities": [
            ("car", 0.52),
            ("motorbike", 0.22),
            ("truck", 0.12),
            ("bike", 0.08),
            ("pedestrian", 0.06),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 6.0),
            "bike": (14.0, 22.0),
            "car": (34.0, 62.0),
            "motorbike": (36.0, 65.0),
            "truck": (30.0, 50.0),
        },
        "illegal_entities": [("car", 0.45), ("motorbike", 0.35), ("pedestrian", 0.15), ("bike", 0.05)],
        "illegal_rate": 0.20,
    },
    "residential_arterial": {
        "allowed_entities": [
            ("car", 0.60),
            ("bike", 0.20),
            ("pedestrian", 0.15),
            ("motorbike", 0.05),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 5.5),
            "bike": (13.0, 22.0),
            "car": (28.0, 48.0),
            "motorbike": (28.0, 46.0),
        },
        "illegal_entities": [("pedestrian", 0.70), ("bike", 0.30)],
        "illegal_rate": 0.08,
    },
    "industrial_freight_arterial": {
        "allowed_entities": [
            ("car", 0.45),
            ("truck", 0.35),
            ("motorbike", 0.10),
            ("bike", 0.05),
            ("pedestrian", 0.05),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 5.5),
            "bike": (12.0, 20.0),
            "car": (36.0, 62.0),
            "truck": (30.0, 54.0),
            "motorbike": (38.0, 64.0),
        },
        "illegal_entities": [("car", 0.45), ("truck", 0.35), ("pedestrian", 0.20)],
        "illegal_rate": 0.12,
    },
    "major_avenue_tram": {
        "allowed_entities": [
            ("car", 0.55),
            ("motorbike", 0.22),
            ("truck", 0.10),
            ("bike", 0.07),
            ("pedestrian", 0.06),
        ],
        "speed_ranges": {
            "pedestrian": (3.5, 6.0),
            "bike": (14.0, 24.0),
            "car": (40.0, 65.0),
            "motorbike": (42.0, 68.0),
            "truck": (34.0, 55.0),
        },
        "illegal_entities": [("car", 0.50), ("motorbike", 0.35), ("pedestrian", 0.15)],
        "illegal_rate": 0.18,
    },
}


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
        with httpx.Client(base_url=api_url, timeout=30.0, follow_redirects=True) as client:
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
        seed_default_admin_if_needed()
        print("Local database reset to clean state (default admin seeded).")


def cmd_build(api_url: str, num_events_per_cam: int = 15, skip_nuke: bool = False) -> None:
    """Build and seed realistic simulated cameras and events exclusively via API HTTP requests."""
    api_url = api_url.rstrip("/")

    if not skip_nuke:
        cmd_nuke(api_url=api_url)

    print(f"\nConnecting to API at: {api_url}")
    with httpx.Client(base_url=api_url, timeout=30.0, follow_redirects=True) as client:
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
        initial_colors = ["green", "red", "green", "amber", "green", "red", "green", "amber", "green", "red"]

        for idx, cam in enumerate(DEMO_CAMERAS):
            cid = cam["id"]
            zone_key = cam.get("zone", "historic_center")
            profile = ZONE_PROFILES.get(zone_key, ZONE_PROFILES["historic_center"])

            # 1. Initialize camera with heartbeat & PATCH edit for authoritative metadata
            active_color = initial_colors[idx % len(initial_colors)]
            latest_light_time = int((now - timedelta(seconds=random.randint(5, 45))).timestamp() * 1000)
            last_hb = int(now.timestamp() * 1000) - random.randint(5, 60) * 1000

            # Register camera initially in online state so ingestion and initial heartbeats succeed
            hb_resp = client.post(
                f"/cameras/{cid}/heartbeat",
                headers=auth_headers,
                json={
                    "last_heartbeat": last_hb,
                    "last_event_timestamp": latest_light_time,
                    "battery_level": cam["battery_level"],
                    "firmware_version": cam["firmware_version"],
                    "wifi_signal": cam["wifi_signal"],
                },
            )
            if hb_resp.status_code != 200:
                sys.exit(f"API Heartbeat failed for camera {cid} ({hb_resp.status_code}): {hb_resp.text}")

            edit_resp = client.patch(
                f"/cameras/{cid}/edit",
                headers=auth_headers,
                json={
                    "name": cam["name"],
                    "location": cam["location"],
                    "latitude": cam["location"][0],
                    "longitude": cam["location"][1],
                    "state": "online",
                },
            )
            if edit_resp.status_code != 200:
                sys.exit(f"API Edit failed for camera {cid} ({edit_resp.status_code}): {edit_resp.text}")

            # 2. Upload photos and prepare crash events matching camera's danger profile
            events = []
            crashes_to_resolve = []

            for crash_spec in cam.get("crashes", []):
                photo_data, content_type = get_random_crash_photo()
                photo_resp = client.post(
                    f"/cameras/{cid}/photos",
                    headers={**auth_headers, "Content-Type": content_type},
                    content=photo_data,
                )
                if photo_resp.status_code != 200:
                    print(f"  [Warning] Photo upload failed for camera {cid}: {photo_resp.status_code}")
                    continue

                photo_id = photo_resp.json()["photo_id"]
                crash_time = int((now - timedelta(minutes=crash_spec["offset_mins"])).timestamp() * 1000)
                events.append({
                    "type": "crash",
                    "photo_id": photo_id,
                    "timestamp": crash_time,
                })

                if crash_spec.get("status") in ("in_progress", "resolved"):
                    crashes_to_resolve.append((photo_id, crash_spec))

            # 3. Generate realistic background events based on zone profile
            for _ in range(num_events_per_cam):
                delta_mins = random.randint(2, 1440)
                event_time = int((now - timedelta(minutes=delta_mins)).timestamp() * 1000)

                event_type = random.choices(
                    ["light_change", "object_detected", "illegal_crossing"],
                    weights=[0.45, 0.45, profile.get("illegal_rate", 0.10)],
                )[0]

                if event_type == "light_change":
                    color = random.choice(["red", "amber", "green"])
                    events.append({"type": "light_change", "color": color, "timestamp": event_time})

                elif event_type == "object_detected":
                    allowed = profile["allowed_entities"]
                    entity_names = [e[0] for e in allowed]
                    entity_weights = [e[1] for e in allowed]
                    entity = random.choices(entity_names, weights=entity_weights)[0]

                    speed_min, speed_max = profile["speed_ranges"][entity]
                    velocity = round(random.uniform(speed_min, speed_max), 1)

                    events.append({
                        "type": "object_detected",
                        "entity_type": entity,
                        "velocity": velocity,
                        "timestamp": event_time,
                    })

                elif event_type == "illegal_crossing":
                    illegal_ents = profile.get("illegal_entities", [("pedestrian", 1.0)])
                    ent_names = [e[0] for e in illegal_ents]
                    ent_weights = [e[1] for e in illegal_ents]
                    entity = random.choices(ent_names, weights=ent_weights)[0]

                    events.append({
                        "type": "illegal_crossing",
                        "entity_type": entity,
                        "timestamp": event_time,
                    })

            # Ensure the MOST RECENT event is a light_change with current active color
            events.append({
                "type": "light_change",
                "color": active_color,
                "timestamp": latest_light_time,
            })

            # 4. Ingest events
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

            # 5. Resolve designated crashes with dispatched units and resolution timestamps
            for photo_id, spec in crashes_to_resolve:
                res_offset = spec.get("resolution_offset_mins", 10)
                resolution_time = int((now - timedelta(minutes=res_offset)).timestamp() * 1000)
                units = spec.get("units", [1])
                notes = spec.get("notes", "Automated central EMS dispatch")

                res_resp = client.post(
                    f"/crashes/{photo_id}/resolve",
                    headers=auth_headers,
                    json={
                        "dispatched_units": units,
                        "resolved_at": resolution_time,
                        "notes": notes,
                    },
                )
                if res_resp.status_code != 200:
                    print(f"  [Warning] Failed to resolve crash {photo_id}: {res_resp.status_code} {res_resp.text}")

            # 6. Apply final camera operational state (e.g. maintenance or offline)
            if cam["state"] != "online":
                client.patch(
                    f"/cameras/{cid}/edit",
                    headers=auth_headers,
                    json={"state": cam["state"]},
                )

            status_symbol = "🟢" if cam["state"] == "online" else "🟡" if cam["state"] == "maintenance" else "⚪"
            crash_count = len(cam.get("crashes", []))
            print(
                f"  ✓ {status_symbol} {cam['name']}: {len(events)} events, "
                f"{crash_count} crashes (Active Signal: {active_color.upper()}, Zone: {zone_key})"
            )

        # 7. Verify
        read_resp = client.get("/cameras")
        if read_resp.status_code == 200:
            cam_list = read_resp.json().get("cameras", [])
            print(f"\nVerification: {api_url}/cameras returned {len(cam_list)} cameras in Turin.")

        # 8. Local DB Sync: Ensure default admin user exists with access to all 10 cameras
        if "localhost" in api_url or "127.0.0.1" in api_url:
            seed_default_admin_if_needed()
            admin_user = get_user_by_username("admin")
            if admin_user:
                set_user_cameras(admin_user["id"], [c["id"] for c in DEMO_CAMERAS])
                print("  ✓ Admin account verified with access to all 10 Turin cameras (admin / admin).")

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

    with httpx.Client(base_url=api_url, timeout=30.0, follow_redirects=True) as client:
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
