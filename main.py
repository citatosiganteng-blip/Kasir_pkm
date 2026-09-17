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
import socket

# Pastikan path benar saat dijalankan dari folder lain
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import config
from ui.styles import MAIN_STYLESHEET


class StartupBackupWorker(QThread):
    """Background worker untuk backup database saat startup tanpa membekukan UI"""
    backup_finished = pyqtSignal(bool, str)

    def run(self):
        try:
            from services.backup_service import BackupService
            from database.db import db
            # Hanya backup jika diaktifkan di pengaturan dan DB sudah ada
            if db.get_setting("backup_enabled", "1") == "1" and config.DB_PATH.exists():
                backup_path = BackupService().create_backup()
                success = backup_path is not None
                if success:
                    print(f"[KasirKu] Startup background backup selesai: {backup_path}")
                self.backup_finished.emit(success, str(backup_path or ""))
        except Exception as e:
            print(f"[KasirKu] Startup background backup warning: {e}")
            self.backup_finished.emit(False, str(e))


class ApiServerThread(QThread):
    """Background thread yang menjalankan FastAPI/Uvicorn bersamaan dengan desktop app"""

    def run(self):
        try:
            import uvicorn
            port = self._find_free_port(
                int(os.environ.get("KASIRKU_API_PORT", "8000"))
            )
            if port is None:
                print("[ApiServer] Tidak ada port yang tersedia (8000-8010). API tidak dijalankan.")
                return

            local_ip = self._get_local_ip()
            print("=" * 55)
            print("  [*]  KasirKu REST API Server (background)")
            print("=" * 55)
            print(f"  [HP]  Web UI / LAN : http://{local_ip}:{port}")
            print(f"  [Doc] API Docs     : http://{local_ip}:{port}/docs")
            print("  Bagikan URL ke HP/Tablet di WiFi yang sama")
            print("=" * 55)
            uvicorn.run(
                "api.main:app",
                host="0.0.0.0",
                port=port,
                reload=False,
                log_level="warning",
            )
        except Exception as e:
            print(f"[ApiServer] Gagal menjalankan API server: {e}")

    @staticmethod
    def _find_free_port(start_port: int) -> int | None:
        """Cari port kosong mulai dari start_port hingga +10"""
        for port in range(start_port, start_port + 11):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                    return port  # Port kosong ditemukan
                except OSError:
                    continue  # Port sudah dipakai, coba berikutnya
        return None

    @staticmethod
    def _get_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


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

        # Terapkan preferensi tema yang tersimpan di DB
        saved_theme = db.get_setting("app_theme", "light")
        from ui.styles import get_theme_stylesheet
        app.setStyleSheet(get_theme_stylesheet(saved_theme))
    except Exception as e:
        QMessageBox.critical(
            None, "Database Error",
            f"Gagal menginisialisasi database:\n{e}\n\nAplikasi akan ditutup."
        )
        sys.exit(1)

    # Jalankan backup di background thread (non-blocking)
    backup_worker = StartupBackupWorker()
    backup_worker.start()
    app._backup_worker = backup_worker  # Cegah garbage collection

    # Jalankan API server di background thread (non-blocking)
    api_worker = ApiServerThread()
    api_worker.start()
    app._api_worker = api_worker  # Cegah garbage collection

    # Tampilkan login window
    show_login(app)

    return app.exec_()


def show_login(app: QApplication):
    """Tampilkan login window"""
    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    login = LoginWindow()
    app._login_window = login

    def on_login_success():
        login.close()
        app._login_window = None
        main_window = MainWindow()
        app._main_window = main_window
        main_window.show()
        main_window.logout_requested.connect(lambda: _on_logout(app))

    def _on_logout(app_inst):
        if hasattr(app_inst, "_main_window") and app_inst._main_window:
            app_inst._main_window.close()
            app_inst._main_window = None
        show_login(app_inst)

    login.login_success.connect(on_login_success)
    login.show()


if __name__ == "__main__":
    sys.exit(main())
