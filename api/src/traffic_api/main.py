import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from traffic_api.auth import (
    CameraToken,
    get_current_camera_token,
    get_current_camera_token_optional,
    require_camera_access,
    validate_jwt_configuration,
)
from traffic_api.auth_user import (
    create_user_token,
    get_current_user,
    get_current_user_optional,
    seed_default_admin_if_needed,
    verify_password,
)
from traffic_api.database import (
    PHOTOS_DIR,
    get_all_cameras,
    get_camera_by_id,
    get_camera_events,
    initialize_database,
    insert_events,
    reset_database,
    update_camera_details,
    update_camera_heartbeat,
    upsert_camera,
)
from traffic_api.structs import CameraHeartbeatPayload, IngestPayload
from traffic_api.user_db import get_user_by_username, get_user_camera_ids

logger = logging.getLogger("traffic_api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_jwt_configuration()
    initialize_database()
    seed_default_admin_if_needed()
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


from pydantic import BaseModel
from typing import Optional

class LoginPayload(BaseModel):
    username: str
    client_hash: Optional[str] = None
    password: Optional[str] = None


@app.post("/auth/login")
async def auth_login(body: LoginPayload, response: Response):
    """Authenticate user with PBKDF2 client_hash (or fallback password) and set session cookie."""
    clean_username = body.username.strip().lower()
    user = get_user_by_username(clean_username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    from traffic_api.auth_user import compute_client_hash
    hash_to_verify = body.client_hash
    if not hash_to_verify and body.password:
        hash_to_verify = compute_client_hash(clean_username, body.password)

    if not hash_to_verify or not verify_password(user["password_hash"], hash_to_verify):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_user_token(user["id"], user["username"])
    # Set auth_token cookie
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )

    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
        },
    }


@app.post("/auth/logout")
async def auth_logout(response: Response):
    """Clear session cookie and log user out."""
    response.delete_cookie(key="auth_token")
    return {"status": "ok", "message": "Logged out successfully"}


@app.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """Return currently authenticated user info."""
    return {"user": current_user}


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


class CameraPatchPayload(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None


@app.get("/cameras")
async def list_cameras(user: Optional[dict] = Depends(get_current_user_optional)):
    """List cameras. If user is logged in, filters to authorized cameras."""
    cameras = get_all_cameras()
    if user:
        allowed_ids = set(get_user_camera_ids(user["id"], user["username"]))
        cameras = [c for c in cameras if c["id"] in allowed_ids]
    return {"cameras": cameras}


@app.get("/cameras/{camera_id}")
async def get_camera(
    camera_id: UUID,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Get camera details by ID, checking user permissions."""
    camera_id_str = str(camera_id)
    if user:
        allowed_ids = set(get_user_camera_ids(user["id"], user["username"]))
        if camera_id_str not in allowed_ids:
            raise HTTPException(
                status_code=403, detail="Forbidden: You do not have access to this camera"
            )

    camera = get_camera_by_id(camera_id_str)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"camera": camera}


@app.patch("/cameras/{camera_id}")
async def patch_camera(
    camera_id: UUID,
    body: CameraPatchPayload,
    user: Optional[dict] = Depends(get_current_user_optional),
    camera_token: Optional[CameraToken] = Depends(get_current_camera_token_optional),
):
    """Authorized endpoint: edit camera details for an assigned user or the camera itself."""
    camera_id_str = str(camera_id)

    # 1. Check if authorized via camera token
    is_authorized_camera = camera_token and camera_id_str in camera_token.camera_ids

    # 2. Check if authorized via user session
    is_authorized_user = False
    if user:
        allowed_ids = set(get_user_camera_ids(user["id"], user["username"]))
        if camera_id_str in allowed_ids:
            is_authorized_user = True

    if not is_authorized_camera and not is_authorized_user:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You do not have access to edit this camera",
        )

    camera = get_camera_by_id(camera_id_str)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    updated = update_camera_details(
        camera_id=camera_id_str,
        name=body.name,
        location=body.location,
        latitude=body.latitude,
        longitude=body.longitude,
        state=body.state,
    )
    actor = f"Camera {camera_id_str[:8]}" if is_authorized_camera else f"User {user['username']}"
    logger.info("%s updated camera %s", actor, camera_id_str)
    return {"camera": updated}


@app.get("/cameras/{camera_id}/events")
async def list_camera_events(
    camera_id: UUID,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """List all events captured by this camera, checking user permissions."""
    camera_id_str = str(camera_id)
    if user:
        allowed_ids = set(get_user_camera_ids(user["id"], user["username"]))
        if camera_id_str not in allowed_ids:
            raise HTTPException(
                status_code=403, detail="Forbidden: You do not have access to this camera"
            )

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
    """Camera heartbeat: broadcasts operational state, battery, and diagnostic telemetry only."""
    camera_id_str = str(camera_id)
    existing_camera = get_camera_by_id(camera_id_str)
    if existing_camera and existing_camera.get("state") == "offline":
        raise HTTPException(
            status_code=409,
            detail="Camera is offline (taken down). Heartbeats are rejected.",
        )

    updated_camera = update_camera_heartbeat(
        camera_id=camera_id_str,
        state=body.state.value,
        last_heartbeat=body.last_heartbeat,
        last_event_timestamp=body.last_event_timestamp,
        battery_level=body.battery_level,
        firmware_version=body.firmware_version,
        wifi_signal=body.wifi_signal,
    )

    logger.info(
        "Heartbeat received from camera %s: state=%s, battery=%s, wifi=%s",
        camera_id_str,
        body.state.value,
        body.battery_level,
        body.wifi_signal,
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
    existing_camera = get_camera_by_id(camera_id_str)
    if existing_camera and existing_camera.get("state") == "offline":
        raise HTTPException(
            status_code=409,
            detail="Camera is offline (taken down). Event ingestion is blocked.",
        )

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
    existing_camera = get_camera_by_id(camera_id_str)
    if existing_camera and existing_camera.get("state") == "offline":
        raise HTTPException(
            status_code=409,
            detail="Camera is offline (taken down). Photo upload is blocked.",
        )

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
