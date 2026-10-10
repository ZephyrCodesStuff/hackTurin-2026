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


def create_camera_token(
    subject: str, camera_ids: list[UUID], expires_in: timedelta
) -> str:
    """Sign a camera token locally using the symmetric CAMERA_JWT_SECRET string."""
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
    return jwt.encode(payload, get_camera_jwt_secret(), algorithm=CAMERA_JWT_ALGORITHM)


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
    parser = argparse.ArgumentParser(
        description="Create an RS256 JWT scoped to one or more camera UUIDs."
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
    args = parser.parse_args()

    if args.expires_hours <= 0:
        parser.error("--expires-hours must be greater than zero")

    try:
        token = create_camera_token(
            subject=args.subject,
            camera_ids=args.camera_ids,
            expires_in=timedelta(hours=args.expires_hours),
        )
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
