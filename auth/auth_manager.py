"""
KasirKu Auth Manager
Mengelola autentikasi, session, dan hak akses
"""

import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from database.db import db
from database.models import User, LoginAttempt
import config


class AuthManager:
    """Singleton authentication manager"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_user = None
        return cls._instance

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None

    @property
    def is_admin(self) -> bool:
        return self._current_user is not None and self._current_user.role == "admin"

    @property
    def is_kasir(self) -> bool:
        return self._current_user is not None and self._current_user.role == "kasir"

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Login user dengan username dan password.
        Returns: (success: bool, message: str)
        """
        username = username.strip()

        # Cek lockout — baca dari DB agar persistent lintas restart
        if self._is_locked_out(username):
            remaining = self._get_lockout_remaining(username)
            return False, f"Akun terkunci. Coba lagi dalam {remaining} detik."

        with db.get_session() as session:
            user = session.query(User).filter_by(
                username=username, aktif=True
            ).first()

            if not user:
                self._record_failed_attempt(username)
                return False, "Username atau password salah."

            # Verifikasi password
            try:
                password_valid = bcrypt.checkpw(
                    password.encode("utf-8"),
                    user.password_hash.encode("utf-8")
                )
            except Exception:
                return False, "Error verifikasi password."

            if not password_valid:
                self._record_failed_attempt(username)
                attempts_left = config.MAX_LOGIN_ATTEMPTS - self._get_attempts(username)
                if attempts_left <= 0:
                    return False, (
                        f"Terlalu banyak percobaan salah. "
                        f"Akun terkunci {config.LOCKOUT_DURATION} detik."
                    )
                return False, (
                    f"Username atau password salah. "
                    f"({attempts_left} percobaan tersisa)"
                )

            # Login berhasil — simpan data user sebelum session ditutup.
            # make_transient() memutus relasi objek dari session tanpa
            # menghapus data, sehingga aman diakses setelah session close.
            from sqlalchemy.orm import make_transient
            self._clear_failed_attempts(username)
            session.expunge(user)
            make_transient(user)
            self._current_user = user
            return True, f"Selamat datang, {user.nama_lengkap or user.username}!"

    def logout(self):
        """Logout current user"""
        self._current_user = None

    # ------------------------------------------------------------------
    # Login attempt helpers — semua operasi lewat DB agar persistent
    # ------------------------------------------------------------------

    def _get_attempt_row(self, session, username: str) -> Optional[LoginAttempt]:
        """Ambil baris LoginAttempt dari DB. Return None jika belum ada."""
        return session.query(LoginAttempt).filter_by(username=username).first()

    def _is_locked_out(self, username: str) -> bool:
        """Cek apakah username sedang dalam masa lockout."""
        try:
            with db.get_session() as session:
                row = self._get_attempt_row(session, username)
                if row is None:
                    return False
                if row.attempts >= config.MAX_LOGIN_ATTEMPTS:
                    elapsed = (datetime.now() - row.last_attempt_at).total_seconds()
                    if elapsed < config.LOCKOUT_DURATION:
                        return True
                    # Lockout sudah kedaluwarsa — bersihkan
                    session.delete(row)
                return False
        except Exception as e:
            print(f"[AuthManager] _is_locked_out error: {e}")
            return False

    def _get_lockout_remaining(self, username: str) -> int:
        """Sisa waktu lockout dalam detik."""
        try:
            with db.get_session() as session:
                row = self._get_attempt_row(session, username)
                if row is None:
                    return 0
                elapsed = (datetime.now() - row.last_attempt_at).total_seconds()
                remaining = config.LOCKOUT_DURATION - elapsed
                return max(0, int(remaining))
        except Exception as e:
            print(f"[AuthManager] _get_lockout_remaining error: {e}")
            return 0

    def _record_failed_attempt(self, username: str):
        """Catat satu percobaan login gagal ke DB."""
        try:
            with db.get_session() as session:
                row = self._get_attempt_row(session, username)
                if row is None:
                    row = LoginAttempt(
                        username=username,
                        attempts=1,
                        last_attempt_at=datetime.now(),
                    )
                    session.add(row)
                else:
                    row.attempts += 1
                    row.last_attempt_at = datetime.now()
        except Exception as e:
            print(f"[AuthManager] _record_failed_attempt error: {e}")

    def _get_attempts(self, username: str) -> int:
        """Jumlah percobaan gagal saat ini dari DB."""
        try:
            with db.get_session() as session:
                row = self._get_attempt_row(session, username)
                return row.attempts if row else 0
        except Exception as e:
            print(f"[AuthManager] _get_attempts error: {e}")
            return 0

    def _clear_failed_attempts(self, username: str):
        """Hapus catatan percobaan gagal dari DB setelah login berhasil."""
        try:
            with db.get_session() as session:
                row = self._get_attempt_row(session, username)
                if row is not None:
                    session.delete(row)
        except Exception as e:
            print(f"[AuthManager] _clear_failed_attempts error: {e}")

    # ------------------------------------------------------------------
    # Password management
    # ------------------------------------------------------------------

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """Ganti password user"""
        with db.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "User tidak ditemukan."

            if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
                return False, "Password lama salah."

            if len(new_password) < 6:
                return False, "Password baru minimal 6 karakter."

            if new_password == old_password:
                return False, "Password baru tidak boleh sama dengan password lama."

            user.password_hash = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()
            ).decode()
            user.must_change_password = False

            if self._current_user and self._current_user.id == user_id:
                self._current_user.must_change_password = False

            return True, "Password berhasil diubah."

    def reset_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        """Reset password user (admin only) — mewajibkan ganti password saat login berikutnya"""
        with db.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "User tidak ditemukan."
            user.password_hash = bcrypt.hashpw(
                new_password.encode(), bcrypt.gensalt()
            ).decode()
            user.must_change_password = True
            return True, f"Password user '{user.username}' berhasil direset."


# Global instance
auth = AuthManager()
