"""
KasirKu API — JWT Auth Dependency
Digunakan sebagai FastAPI dependency di endpoint yang membutuhkan autentikasi.
"""

import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _get_jwt_secret() -> str:
    """
    Ambil JWT secret key dengan prioritas:
    1. Environment variable KASIRKU_JWT_SECRET (paling aman, untuk production)
    2. Nilai yang tersimpan di database (auto-generated saat pertama kali jalan)
    3. Generate baru, simpan ke DB, lalu gunakan — tidak pernah hardcoded.
    """
    # Prioritas 1: environment variable
    env_secret = os.environ.get("KASIRKU_JWT_SECRET", "").strip()
    if env_secret:
        return env_secret

    # Prioritas 2 & 3: ambil atau buat dari DB
    try:
        from database.db import db
        stored = db.get_setting("jwt_secret_key")
        if stored:
            return stored

        # Belum ada — generate sekali, simpan permanen ke DB
        new_secret = secrets.token_hex(32)  # 256-bit random key
        db.set_setting("jwt_secret_key", new_secret)
        print("[deps] JWT secret key baru di-generate dan disimpan ke DB.")
        return new_secret
    except Exception as e:
        # Fallback darurat — hanya dipakai jika DB belum siap sama sekali.
        # Key ini TIDAK persisten; semua token akan invalid setelah restart.
        print(f"[deps] WARNING: Tidak bisa baca JWT secret dari DB ({e}). "
              "Gunakan env var KASIRKU_JWT_SECRET untuk key yang stabil.")
        return secrets.token_hex(32)


# Lazy-load: key dibaca sekali saat modul pertama kali diakses,
# setelah DB dipastikan sudah terinisialisasi oleh api/main.py
_JWT_SECRET_CACHE: str | None = None


def _jwt_secret() -> str:
    global _JWT_SECRET_CACHE
    if _JWT_SECRET_CACHE is None:
        _JWT_SECRET_CACHE = _get_jwt_secret()
    return _JWT_SECRET_CACHE


# Alias yang digunakan di fungsi-fungsi di bawah
def _get_secret() -> str:
    return _jwt_secret()


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
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode dan validasi JWT token. Return payload atau None jika invalid."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
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
