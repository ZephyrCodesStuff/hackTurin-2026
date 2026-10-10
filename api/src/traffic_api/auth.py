"""HS256 JWT verification and camera-scoped FastAPI authorization."""

import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Union
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

CAMERA_JWT_ALGORITHM = "HS256"
CAMERA_JWT_ISSUER = "traffic-camera-api"
DEFAULT_CAMERA_SECRET = "traffic-camera-demo-secret-key-8371946"

security = HTTPBearer(auto_error=False)


class CameraToken:
    """The validated identity and camera scope from a bearer token."""

    def __init__(self, subject: str, camera_ids: Set[str]) -> None:
        self.subject = subject
        self.camera_ids = camera_ids


@lru_cache
def get_camera_jwt_secret() -> str:
    """Load the camera signing/verification secret string from the environment."""
    secret = os.environ.get("CAMERA_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if not secret:
        try:
            from pathlib import Path
            from dotenv import find_dotenv, load_dotenv

            env_file = find_dotenv(usecwd=True)
            if env_file:
                load_dotenv(env_file)
            else:
                project_dir = Path(__file__).resolve().parents[2]
                load_dotenv(project_dir / ".env")
            secret = os.environ.get("CAMERA_JWT_SECRET") or os.environ.get("JWT_SECRET")
        except ImportError:
            pass

    return secret or DEFAULT_CAMERA_SECRET


def validate_jwt_configuration() -> None:
    """Ensure camera JWT secret is accessible."""
    get_camera_jwt_secret()


def normalize_camera_ids(camera_ids: Iterable[Union[str, UUID]]) -> List[str]:
    """Validate, canonicalize, and deduplicate camera UUIDs."""
    normalized = {str(UUID(str(camera_id))) for camera_id in camera_ids}
    if not normalized:
        raise ValueError("A camera token must authorize at least one camera ID")
    return sorted(normalized)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_camera_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CameraToken:
    """Validate a bearer token and extract its camera authorization scope."""
    if credentials is None:
        raise _unauthorized("Bearer token required")

    try:
        payload: Dict[str, Any] = jwt.decode(
            credentials.credentials,
            get_camera_jwt_secret(),
            algorithms=[CAMERA_JWT_ALGORITHM],
            issuer=CAMERA_JWT_ISSUER,
            options={"require": ["sub", "iss", "iat", "exp", "authorized_camera_ids"]},
        )
        camera_ids = normalize_camera_ids(payload["authorized_camera_ids"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise _unauthorized("Invalid or expired bearer token")

    return CameraToken(subject=payload["sub"], camera_ids=set(camera_ids))


def require_camera_access(
    camera_id: UUID,
    token: CameraToken = Depends(get_current_camera_token),
) -> CameraToken:
    """Ensure the bearer token is allowed to submit data for this camera."""
    if str(camera_id) not in token.camera_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not authorized for this camera",
        )
    return token


def get_current_camera_token_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CameraToken]:
    """Extract CameraToken if present and valid; otherwise return None without raising."""
    if credentials is None:
        return None
    try:
        payload: Dict[str, Any] = jwt.decode(
            credentials.credentials,
            get_camera_jwt_secret(),
            algorithms=[CAMERA_JWT_ALGORITHM],
            issuer=CAMERA_JWT_ISSUER,
            options={"require": ["sub", "iss", "iat", "exp", "authorized_camera_ids"]},
        )
        camera_ids = normalize_camera_ids(payload["authorized_camera_ids"])
        return CameraToken(subject=payload["sub"], camera_ids=set(camera_ids))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None
