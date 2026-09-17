"""
KasirKu API — JWT Auth Dependency
Digunakan sebagai FastAPI dependency di endpoint yang membutuhkan autentikasi.
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Secret key untuk JWT — bisa override via env variable JWT_SECRET
JWT_SECRET = os.environ.get("KASIRKU_JWT_SECRET", "kasirku-secret-change-in-production-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

bearer_scheme = HTTPBearer(auto_error=False)


# ──────────────────────────── Token Helpers ────────────────────────────

def create_token(user_id: int, username: str, role: str) -> str:
    """Buat JWT token untuk user yang login"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode dan validasi JWT token. Return payload atau None jika invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ──────────────────────────── FastAPI Dependencies ────────────────────────────

def get_current_user_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency: verifikasi token dan kembalikan payload.
    Raise 401 jika token tidak valid atau tidak ada.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi diperlukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kadaluarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_admin(payload: dict = Depends(get_current_user_payload)) -> dict:
    """
    FastAPI dependency: hanya admin yang boleh akses endpoint ini.
    Raise 403 jika bukan admin.
    """
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang diizinkan mengakses endpoint ini",
        )
    return payload


def get_current_user_id(payload: dict = Depends(get_current_user_payload)) -> int:
    """Kembalikan user_id dari token payload"""
    return int(payload["sub"])
