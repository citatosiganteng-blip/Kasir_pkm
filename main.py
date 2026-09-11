"""
KasirKu - Aplikasi Kasir Native
Entry point utama aplikasi

Cara menjalankan:
    python main.py

Requirements:
    pip install -r requirements.txt
"""

import sys
import os

# Pastikan path benar saat dijalankan dari folder lain
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config
from ui.styles import MAIN_STYLESHEET


def main():
    """Entry point utama"""
    # Set environment untuk Windows DPI scaling
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName("PKM Team")
    app.setStyleSheet(MAIN_STYLESHEET)

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Inisialisasi database
    try:
        from database.db import db
        db.initialize()
        print(f"[KasirKu] Database siap: {config.DB_PATH}")
    except Exception as e:
        QMessageBox.critical(
            None, "Database Error",
            f"Gagal menginisialisasi database:\n{e}\n\nAplikasi akan ditutup."
        )
        sys.exit(1)

    # Buat backup awal saat startup
    try:
        from services.backup_service import BackupService
        # Hanya backup jika DB sudah ada sebelumnya (bukan pertama kali)
        if config.DB_PATH.exists():
            BackupService().create_backup()
    except Exception as e:
        print(f"[KasirKu] Startup backup warning: {e}")

    # Tampilkan login window
    show_login(app)

    return app.exec_()


def show_login(app: QApplication):
    """Tampilkan login window"""
    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    login = LoginWindow()

    def on_login_success():
        login.close()
        main_window = MainWindow()
        main_window.show()
        main_window.logout_requested.connect(lambda: show_login(app))

    login.login_success.connect(on_login_success)
    login.show()


if __name__ == "__main__":
    sys.exit(main())
