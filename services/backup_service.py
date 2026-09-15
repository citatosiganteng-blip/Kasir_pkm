"""
KasirKu Backup Service
Layanan backup database otomatis
"""

import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
import config


class BackupService:
    """Service untuk backup database"""

    def __init__(self):
        self.backup_dir = config.BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self) -> str | None:
        """Buat backup database"""
        try:
            if not config.DB_PATH.exists():
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"kasirku_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_name

            shutil.copy2(config.DB_PATH, backup_path)
            print(f"[BackupService] Backup berhasil: {backup_path}")

            # Hapus backup lama
            self._cleanup_old_backups()

            return str(backup_path)
        except Exception as e:
            print(f"[BackupService] Error backup: {e}")
            return None

    def _cleanup_old_backups(self):
        """Hapus backup yang sudah lebih dari BACKUP_KEEP_DAYS hari"""
        try:
            cutoff = datetime.now() - timedelta(days=config.BACKUP_KEEP_DAYS)
            for backup_file in self.backup_dir.glob("kasirku_backup_*.db"):
                if backup_file.stat().st_mtime < cutoff.timestamp():
                    backup_file.unlink()
                    print(f"[BackupService] Hapus backup lama: {backup_file.name}")
        except Exception as e:
            print(f"[BackupService] Cleanup error: {e}")

    def get_backup_list(self) -> list[dict]:
        """Daftar file backup"""
        backups = []
        for f in sorted(self.backup_dir.glob("kasirku_backup_*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime)
            })
        return backups

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database dari backup.
        Setelah file di-copy, engine SQLAlchemy di-reload agar koneksi
        menunjuk ke data yang baru saja di-restore.
        """
        try:
            # Buat backup kondisi saat ini sebelum di-overwrite
            self.create_backup()
            # Salin file backup ke lokasi DB aktif
            shutil.copy2(backup_path, config.DB_PATH)
            print(f"[BackupService] Restore dari: {backup_path}")

            # Reload koneksi DB — wajib agar SQLAlchemy tidak membaca
            # data stale dari engine/connection pool lama
            from database.db import db
            db.reconnect()
            return True
        except Exception as e:
            print(f"[BackupService] Restore error: {e}")
            return False
