from __future__ import annotations

import hashlib
import os
import time
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from traffic_api.user_db import get_user_by_id

USER_JWT_SECRET = os.environ.get(
    "USER_SESSION_SECRET", "traffic-panel-demo-secret-key-9281734"
)
USER_JWT_ALGORITHM = "HS256"

_ph = PasswordHasher()
security_bearer = HTTPBearer(auto_error=False)


def compute_client_hash(username: str, password: str) -> str:
    """Compute deterministic client-side PBKDF2 hash (matching frontend Web Crypto)."""
    clean_user = username.strip().lower()
    salt = f"traffic-auth:{clean_user}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()


def hash_password(client_hash: str) -> str:
    """Hash the client-provided PBKDF2 digest with Argon2id."""
    return _ph.hash(client_hash)


def verify_password(stored_hash: str, client_hash: str) -> bool:
    """Verify an Argon2id hash against the client-provided PBKDF2 digest."""
    try:
        return _ph.verify(stored_hash, client_hash)
    except (VerifyMismatchError, VerificationError):
        return False


def create_user_token(
    user_id: str, username: str, expires_in_seconds: int = 86400 * 7
) -> str:
    """Generate a signed user session JWT."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + expires_in_seconds,
        "type": "user_session",
    }
    return jwt.encode(payload, USER_JWT_SECRET, algorithm=USER_JWT_ALGORITHM)


def decode_user_token(token: str) -> dict | None:
    """Verify and decode a user session JWT."""
    try:
        payload = jwt.decode(
            token, USER_JWT_SECRET, algorithms=[USER_JWT_ALGORITHM]
        )
        if payload.get("type") != "user_session":
            return None
        return payload
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> dict:
    """Extract authenticated user from Bearer header or auth_token cookie."""
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "auth_token" in request.cookies:
        token = request.cookies["auth_token"]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_user_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": user["id"], "username": user["username"]}


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[dict]:
    """Extract authenticated user if credentials exist, or return None."""
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "auth_token" in request.cookies:
        token = request.cookies["auth_token"]

    if not token:
        return None

    payload = decode_user_token(token)
    if not payload:
        return None

    user = get_user_by_id(payload["sub"])
    if not user:
        return None

    return {"id": user["id"], "username": user["username"]}


def seed_default_admin_if_needed() -> None:
    """Seed initial admin/admin user if no users exist in the database."""
    from traffic_api.user_db import create_user, get_user_by_username, list_users

    users = list_users()
    if not users and not get_user_by_username("admin"):
        client_hash = compute_client_hash("admin", "admin")
        server_hash = hash_password(client_hash)
        create_user("admin", server_hash)
