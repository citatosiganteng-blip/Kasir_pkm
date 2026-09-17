"""
Test Theme switching, DB persistence, and page theme hooks
"""
import os
import sys
import pytest
from PyQt5.QtWidgets import QApplication

from database.db import db
from database.models import User
from auth.auth_manager import auth
from ui.styles import get_theme_stylesheet, LIGHT_STYLESHEET, DARK_STYLESHEET
from ui.main_window import MainWindow

# Ensure QApp exists
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([sys.argv[0]])
    return app


def test_theme_stylesheets_valid():
    """Verify that light and dark stylesheets are non-empty and have no forbidden cursor property"""
    light = get_theme_stylesheet("light")
    dark = get_theme_stylesheet("dark")

    assert len(light) > 1000
    assert len(dark) > 1000
    assert "cursor: pointer" not in light.lower()
    assert "cursor: pointer" not in dark.lower()


def test_theme_toggle_and_persistence(qapp, monkeypatch):
    """Test instantiating MainWindow, toggling theme, and verifying DB persistence"""
    from PyQt5.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    db.initialize()

    with db.get_session() as session:
        user = session.query(User).filter_by(username="admin").first()
        if not user:
            user = User(username="admin", nama_lengkap="Administrator", role="admin", aktif=True)
            session.add(user)
            session.commit()
        session.expunge(user)
        auth._current_user = user

    # Force initial theme to light
    db.set_setting("app_theme", "light")

    win = MainWindow()

    assert win._current_theme == "light"
    assert "Mode Gelap" in win.btn_theme_toggle.text()

    # Toggle to dark
    win._toggle_theme()

    assert win._current_theme == "dark"
    assert db.get_setting("app_theme") == "dark"
    assert "Mode Terang" in win.btn_theme_toggle.text()

    # Toggle back to light
    win._toggle_theme()

    assert win._current_theme == "light"
    assert db.get_setting("app_theme") == "light"
    assert "Mode Gelap" in win.btn_theme_toggle.text()

    # Navigate through all pages to ensure no errors
    for key in ["dashboard", "kasir", "barang", "pembelian", "riwayat", "pengeluaran", "laporan", "users", "settings"]:
        if key in win._pages:
            win._navigate(key)
            page = win._pages[key]
            if hasattr(page, "on_theme_changed"):
                page.on_theme_changed("dark")
                page.on_theme_changed("light")

    win.close()
