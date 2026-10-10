import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from traffic_api.auth import CameraToken, require_camera_access, validate_jwt_configuration
from traffic_api.database import PHOTOS_DIR, initialize_database, insert_events, upsert_camera
from traffic_api.structs import IngestPayload

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

@app.get("/")
async def root():
    return {"message": "Hello World"}

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
    return Response(content=photo_path.read_bytes(), media_type="application/octet-stream")
