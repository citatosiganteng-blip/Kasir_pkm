"""
KasirKu API — Auth Router
Endpoint: login, logout, me, change-password, refresh-token
"""

from fastapi import APIRouter, HTTPException, status, Depends

from database.db import db
from database.models import User
from auth.auth_manager import auth as auth_manager
from api.deps import (
    create_token, create_refresh_token, decode_token,
    get_current_user_payload, get_current_user_id,
)
from api.schemas import (
    LoginRequest, TokenResponse, UserOut,
    ChangePasswordRequest, MessageResponse,
    RefreshTokenRequest, AccessTokenResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Login dengan username + password.
    Return JWT access token (24 jam) dan refresh token (30 hari).

    auth_manager.login() digunakan HANYA untuk verifikasi password dan
    mencatat percobaan gagal. User data diambil langsung dari DB setelahnya
    — tidak bergantung pada auth_manager.current_user (singleton state)
    yang tidak aman untuk concurrent API requests.
    """
    success, message = auth_manager.login(body.username, body.password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    # Ambil data user langsung dari DB — thread-safe, tidak pakai singleton state
    with db.get_session() as session:
        user = session.query(User).filter_by(
            username=body.username.strip(), aktif=True
        ).first()
        if user is None:
            raise HTTPException(status_code=500, detail="Login state error")

        access_token = create_token(user.id, user.username, user.role)
        refresh_token = create_refresh_token(user.id, user.username, user.role)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            username=user.username,
            role=user.role,
            nama_lengkap=user.nama_lengkap,
            must_change_password=user.must_change_password or False,
        )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(body: RefreshTokenRequest):
    """
    Perbarui access token menggunakan refresh token yang masih valid.
    Kirim refresh_token yang didapat saat login, dapatkan access_token baru.
    Refresh token tidak di-rotate (tetap sama sampai expire 30 hari).
    """
    payload = decode_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid atau sudah kadaluarsa. Silakan login ulang.",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token yang diberikan bukan refresh token.",
        )

    user_id = int(payload["sub"])

    # Pastikan user masih aktif di database
    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id, aktif=True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User tidak ditemukan atau sudah dinonaktifkan. Silakan login ulang.",
            )
        new_access_token = create_token(user.id, user.username, user.role)

    return AccessTokenResponse(access_token=new_access_token)


@router.get("/me", response_model=UserOut)
def me(payload: dict = Depends(get_current_user_payload)):
    """Info user yang sedang login (dari token)."""
    user_id = int(payload["sub"])
    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id, aktif=True).first()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        return UserOut.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Ganti password user yang sedang login."""
    success, message = auth_manager.change_password(
        user_id, body.old_password, body.new_password
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return MessageResponse(message=message)


@router.post("/logout", response_model=MessageResponse)
def logout():
    """
    Logout (stateless JWT — token tidak di-blacklist server side).
    Client harus hapus access token DAN refresh token dari storage lokal.
    """
    return MessageResponse(message="Logout berhasil. Silakan hapus token di perangkat Anda.")
