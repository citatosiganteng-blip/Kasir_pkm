"""
Unit tests for Authentication & Password Management
"""

import pytest
from auth.auth_manager import auth
from database.models import User, LoginAttempt


def test_default_seed_must_change_password(test_db):
    """Pastikan user default di-seed dengan flag must_change_password = True"""
    with test_db.get_session() as session:
        admin = session.query(User).filter_by(username="admin").first()
        kasir = session.query(User).filter_by(username="kasir").first()

        assert admin is not None
        assert admin.must_change_password is True
        assert kasir is not None
        assert kasir.must_change_password is True


def test_login_success(test_db):
    """Login berhasil dengan kredensial default"""
    auth._clear_failed_attempts("admin")
    success, msg = auth.login("admin", "admin123")
    assert success is True
    assert "Selamat datang" in msg
    assert auth.current_user is not None
    assert auth.current_user.username == "admin"
    assert auth.current_user.must_change_password is True


def test_login_wrong_password_and_lockout(test_db):
    """Uji throttling dan lockout login setelah percobaan salah berturut-turut"""
    test_user = "kasir"
    auth._clear_failed_attempts(test_user)

    # 1st attempt
    ok1, msg1 = auth.login(test_user, "wrong1")
    assert ok1 is False
    assert "2 percobaan tersisa" in msg1

    # 2nd attempt
    ok2, msg2 = auth.login(test_user, "wrong2")
    assert ok2 is False
    assert "1 percobaan tersisa" in msg2

    # 3rd attempt -> Terkunci
    ok3, msg3 = auth.login(test_user, "wrong3")
    assert ok3 is False
    assert "terkunci" in msg3.lower()

    # 4th attempt saat terkunci — password benar pun harus ditolak
    ok4, msg4 = auth.login(test_user, "kasir123")
    assert ok4 is False
    assert "terkunci" in msg4.lower()

    # Cleanup lockout
    auth._clear_failed_attempts(test_user)


def test_login_attempts_persisted_in_db(test_db):
    """
    Verifikasi bahwa percobaan login gagal tersimpan di tabel login_attempts.
    Ini memastikan data tidak hilang jika aplikasi di-restart.
    """
    test_user = "kasir"
    auth._clear_failed_attempts(test_user)

    # Lakukan 2 percobaan gagal
    auth.login(test_user, "salah1")
    auth.login(test_user, "salah2")

    # Cek langsung di DB
    with test_db.get_session() as session:
        row = session.query(LoginAttempt).filter_by(username=test_user).first()
        assert row is not None, "Baris LoginAttempt harus ada di DB setelah percobaan gagal"
        assert row.attempts == 2
        assert row.last_attempt_at is not None

    # Setelah login berhasil, baris harus dihapus
    auth.login(test_user, "kasir123")
    with test_db.get_session() as session:
        row = session.query(LoginAttempt).filter_by(username=test_user).first()
        assert row is None, "Baris LoginAttempt harus dihapus setelah login berhasil"


def test_login_attempts_cleared_after_success(test_db):
    """Verifikasi _clear_failed_attempts menghapus data dari DB."""
    test_user = "admin"
    auth._clear_failed_attempts(test_user)

    # Catat beberapa percobaan
    auth._record_failed_attempt(test_user)
    auth._record_failed_attempt(test_user)
    assert auth._get_attempts(test_user) == 2

    # Clear
    auth._clear_failed_attempts(test_user)
    assert auth._get_attempts(test_user) == 0

    # Pastikan baris benar-benar tidak ada di DB
    with test_db.get_session() as session:
        row = session.query(LoginAttempt).filter_by(username=test_user).first()
        assert row is None


def test_change_password_validations(test_db):
    """Uji validasi dan keberhasilan penggantian password"""
    auth._clear_failed_attempts("admin")
    auth.login("admin", "admin123")
    user_id = auth.current_user.id

    # 1. Password lama salah
    ok, msg = auth.change_password(user_id, "passSalah", "adminBaru123")
    assert ok is False
    assert "lama salah" in msg.lower()

    # 2. Password baru terlalu pendek (< 6)
    ok, msg = auth.change_password(user_id, "admin123", "123")
    assert ok is False
    assert "minimal 6 karakter" in msg.lower()

    # 3. Password baru sama dengan password lama
    ok, msg = auth.change_password(user_id, "admin123", "admin123")
    assert ok is False
    assert "tidak boleh sama" in msg.lower()

    # 4. Ganti password sukses
    ok, msg = auth.change_password(user_id, "admin123", "adminBaru123")
    assert ok is True
    assert "berhasil" in msg.lower()

    # Cek flag must_change_password di database sudah False
    with test_db.get_session() as session:
        updated_admin = session.query(User).filter_by(id=user_id).first()
        assert updated_admin.must_change_password is False

    # Login dengan password lama gagal
    ok_old, _ = auth.login("admin", "admin123")
    assert ok_old is False

    # Login dengan password baru sukses dan must_change_password False
    ok_new, _ = auth.login("admin", "adminBaru123")
    assert ok_new is True
    assert auth.current_user.must_change_password is False


def test_reset_password_sets_must_change(test_db):
    """Uji admin mereset password user lain mengaktifkan kembali flag must_change_password"""
    with test_db.get_session() as session:
        kasir = session.query(User).filter_by(username="kasir").first()
        kasir_id = kasir.id

    # Reset password kasir
    ok, msg = auth.reset_password(kasir_id, "kasirBaru456")
    assert ok is True

    with test_db.get_session() as session:
        updated_kasir = session.query(User).filter_by(id=kasir_id).first()
        assert updated_kasir.must_change_password is True
