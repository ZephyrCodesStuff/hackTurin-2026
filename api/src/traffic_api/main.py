import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from traffic_api.auth import (
    CameraToken,
    get_current_camera_token,
    require_camera_access,
    validate_jwt_configuration,
)
from traffic_api.database import (
    PHOTOS_DIR,
    get_all_cameras,
    get_camera_by_id,
    get_camera_events,
    initialize_database,
    insert_events,
    reset_database,
    update_camera_heartbeat,
    upsert_camera,
)
from traffic_api.structs import CameraHeartbeatPayload, IngestPayload

logger = logging.getLogger("traffic_api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_jwt_configuration()
    initialize_database()
    yield


app = FastAPI(
    title="Traffic Camera API",
    version="0.1.0",
    description="Camera-scoped traffic-event ingestion API.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for the frontend demo website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/nuke")
async def nuke_database(token: CameraToken = Depends(get_current_camera_token)):
    """Authorized endpoint: wipe all database tables and uploaded photos. Only enabled when DEVELOPMENT_MODE=true."""
    if os.environ.get("DEVELOPMENT_MODE", "").strip().lower() != "true":
        raise HTTPException(status_code=404, detail="Not Found")
    reset_database()
    logger.warning("Database and photos nuked by %s via /nuke", token.subject)
    return {
        "status": "ok",
        "message": "Database and photos nuked successfully",
        "nuked_by": token.subject,
    }


@app.get("/cameras")
async def list_cameras():
    """Public read-only endpoint: list all registered cameras."""
    cameras = get_all_cameras()
    return {"cameras": cameras}


@app.get("/cameras/{camera_id}")
async def get_camera(camera_id: UUID):
    """Public read-only endpoint: get camera details by ID."""
    camera = get_camera_by_id(str(camera_id))
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"camera": camera}


@app.get("/cameras/{camera_id}/events")
async def list_camera_events(camera_id: UUID):
    """Public read-only endpoint: list all events captured by this camera (newest first)."""
    camera_id_str = str(camera_id)
    camera = get_camera_by_id(camera_id_str)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    events = get_camera_events(camera_id_str)
    return {
        "camera_id": camera_id_str,
        "camera": camera,
        "total_events": len(events),
        "events": events,
    }


@app.post("/cameras/{camera_id}/heartbeat")
async def camera_heartbeat(
    camera_id: UUID,
    body: CameraHeartbeatPayload,
    token: CameraToken = Depends(require_camera_access),
):
    """Camera heartbeat: broadcasts state, location, battery, and diagnostic metadata."""
    camera_id_str = str(camera_id)
    lat, lon = body.location if body.location else (None, None)

    updated_camera = update_camera_heartbeat(
        camera_id=camera_id_str,
        name=body.name,
        state=body.state.value,
        latitude=lat,
        longitude=lon,
        last_heartbeat=body.last_heartbeat,
        last_event_timestamp=body.last_event_timestamp,
        battery_level=body.battery_level,
        firmware_version=body.firmware_version,
        wifi_signal=body.wifi_signal,
    )

    logger.info(
        "Heartbeat received from camera %s: state=%s, location=%s, battery=%s",
        camera_id_str,
        body.state.value,
        body.location,
        body.battery_level,
    )

    return {
        "message": "Heartbeat updated successfully",
        "camera_id": camera_id_str,
        "submitted_by": token.subject,
        "camera": updated_camera,
    }


@app.post("/cameras/{camera_id}/ingest")
async def ingest_data(
    camera_id: UUID,
    body: IngestPayload,
    token: CameraToken = Depends(require_camera_access),
):
    camera_id_str = str(camera_id)
    camera_name = f"Camera {camera_id_str[:8]}"
    camera_location = "Unknown"
    upsert_camera(camera_id=camera_id_str, name=camera_name, location=camera_location)

    counts = insert_events(camera_id=camera_id_str, events=body.events)
    total_events = sum(counts.values())

    logger.info(
        "Camera %s ingested %d events (crashes=%d, light_changes=%d, illegal_crossings=%d, objects=%d)",
        camera_id_str,
        total_events,
        counts["crashes"],
        counts["light_changes"],
        counts["illegal_crossings"],
        counts["objects_detected"],
    )

    return {
        "message": f"Successfully ingested {total_events} event(s)",
        "camera_id": camera_id_str,
        "submitted_by": token.subject,
        "counts": counts,
    }


@app.post("/cameras/{camera_id}/photos")
async def upload_photo(
    camera_id: UUID,
    request: Request,
    token: CameraToken = Depends(require_camera_access),
):
    """Upload raw image bytes for this camera. Generates and returns a valid UUIDv4 photo_id."""
    camera_id_str = str(camera_id)
    camera_name = f"Camera {camera_id_str[:8]}"
    camera_location = "Unknown"
    upsert_camera(camera_id=camera_id_str, name=camera_name, location=camera_location)

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Photo payload cannot be empty")

    photo_id = uuid4()
    photo_path = PHOTOS_DIR / f"{photo_id}.bin"
    photo_path.write_bytes(body)

    logger.info("Saved photo %s (%d bytes) for camera %s", photo_id, len(body), camera_id_str)
    return {
        "photo_id": str(photo_id),
        "camera_id": camera_id_str,
        "bytes_received": len(body),
    }


@app.get("/photos/{photo_id}")
async def get_photo(photo_id: UUID):
    """Retrieve raw image bytes for a photo_id."""
    photo_path = PHOTOS_DIR / f"{photo_id}.bin"
    if not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    data = photo_path.read_bytes()
    if data.startswith(b"\x89PNG"):
        media_type = "image/png"
    elif data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"
    return Response(content=data, media_type=media_type)
