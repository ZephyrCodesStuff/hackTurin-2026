"""RS256 JWT verification and camera-scoped FastAPI authorization."""

import base64
import binascii
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Union
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_ALGORITHM = "RS256"
JWT_ISSUER = "traffic-camera-api"
security = HTTPBearer(auto_error=False)


class CameraToken:
    """The validated identity and camera scope from a bearer token."""

    def __init__(self, subject: str, camera_ids: Set[str]) -> None:
        self.subject = subject
        self.camera_ids = camera_ids


@lru_cache
def _public_key_pem() -> bytes:
    """Load the verification key from the environment without writing it to disk."""
    encoded_key = os.environ.get("JWT_PUBLIC_KEY_B64")
    if not encoded_key:
        try:
            from dotenv import find_dotenv, load_dotenv

            env_file = find_dotenv(usecwd=True)
            if env_file:
                load_dotenv(env_file)
            encoded_key = os.environ.get("JWT_PUBLIC_KEY_B64")
        except ImportError:
            pass

    if not encoded_key:
        raise RuntimeError("JWT_PUBLIC_KEY_B64 must be set before starting the API")

    try:
        pem = base64.b64decode(encoded_key, validate=True)
        key = serialization.load_pem_public_key(pem)
    except (binascii.Error, ValueError) as error:
        raise RuntimeError(
            "JWT_PUBLIC_KEY_B64 must be valid base64 PEM for an RSA public key"
        ) from error

    if not isinstance(key, RSAPublicKey):
        raise RuntimeError("JWT_PUBLIC_KEY_B64 must contain an RSA public key")
    return pem


def validate_jwt_configuration() -> None:
    """Fail application startup early when the verification key is unavailable."""
    _public_key_pem()


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
            _public_key_pem(),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
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
