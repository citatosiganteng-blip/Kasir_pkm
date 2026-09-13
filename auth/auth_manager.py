"""
KasirKu Auth Manager
Mengelola autentikasi, session, dan hak akses
"""

import bcrypt
import time
from datetime import datetime
from typing import Optional
from database.db import db
from database.models import User
import config


class AuthManager:
    """Singleton authentication manager"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_user = None
            cls._instance._login_attempts = {}  # {username: (attempts, last_attempt_time)}
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

        # Cek lockout
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
                    return False, f"Terlalu banyak percobaan salah. Akun terkunci {config.LOCKOUT_DURATION} detik."
                return False, f"Username atau password salah. ({attempts_left} percobaan tersisa)"

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

    def _is_locked_out(self, username: str) -> bool:
        if username not in self._login_attempts:
            return False
        attempts, last_time = self._login_attempts[username]
        if attempts >= config.MAX_LOGIN_ATTEMPTS:
            if time.time() - last_time < config.LOCKOUT_DURATION:
                return True
            else:
                # Lockout expired
                del self._login_attempts[username]
        return False

    def _get_lockout_remaining(self, username: str) -> int:
        if username not in self._login_attempts:
            return 0
        _, last_time = self._login_attempts[username]
        remaining = config.LOCKOUT_DURATION - (time.time() - last_time)
        return max(0, int(remaining))

    def _record_failed_attempt(self, username: str):
        attempts = self._get_attempts(username) + 1
        self._login_attempts[username] = (attempts, time.time())

    def _get_attempts(self, username: str) -> int:
        if username not in self._login_attempts:
            return 0
        return self._login_attempts[username][0]

    def _clear_failed_attempts(self, username: str):
        if username in self._login_attempts:
            del self._login_attempts[username]

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
        """Reset password user (admin only) - mewajibkan ganti password saat login berikutnya"""
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
