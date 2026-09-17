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

    # Jumlah maksimum file backup yang disimpan, terlepas dari usia file.
    # Ini mencegah penumpukan jika backup dibuat sangat sering.
    MAX_BACKUP_COUNT = 30

    def _parse_backup_timestamp(self, filename: str) -> datetime | None:
        """
        Parse timestamp dari nama file backup.
        Format: kasirku_backup_YYYYMMDD_HHMMSS.db
        Menggunakan nama file (bukan mtime) agar tidak terpengaruh
        metadata saat file di-copy oleh shutil.copy2.
        """
        try:
            # Ambil bagian YYYYMMDD_HHMMSS dari nama file
            stem = Path(filename).stem  # kasirku_backup_20260917_180038
            parts = stem.split("_")     # ['kasirku', 'backup', '20260917', '180038']
            if len(parts) >= 4:
                dt_str = f"{parts[2]}_{parts[3]}"
                return datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
        except (ValueError, IndexError):
            pass
        return None

    def _cleanup_old_backups(self):
        """
        Hapus backup berdasarkan dua kriteria:
        1. Usianya melebihi BACKUP_KEEP_DAYS (dihitung dari nama file, bukan mtime)
        2. Jumlah total backup melebihi MAX_BACKUP_COUNT (hapus yang paling lama)
        """
        try:
            cutoff = datetime.now() - timedelta(days=config.BACKUP_KEEP_DAYS)
            all_backups = sorted(
                self.backup_dir.glob("kasirku_backup_*.db"),
                key=lambda f: self._parse_backup_timestamp(f.name) or datetime.min,
                reverse=True,  # Terbaru di depan
            )

            # Kriteria 1: hapus berdasarkan usia (parse dari nama file)
            for backup_file in all_backups:
                file_ts = self._parse_backup_timestamp(backup_file.name)
                if file_ts and file_ts < cutoff:
                    backup_file.unlink()
                    print(f"[BackupService] Hapus backup kadaluarsa: {backup_file.name}")

            # Kriteria 2: hapus yang paling lama jika masih melebihi batas jumlah
            remaining = sorted(
                self.backup_dir.glob("kasirku_backup_*.db"),
                key=lambda f: self._parse_backup_timestamp(f.name) or datetime.min,
                reverse=True,
            )
            if len(remaining) > self.MAX_BACKUP_COUNT:
                for backup_file in remaining[self.MAX_BACKUP_COUNT:]:
                    backup_file.unlink()
                    print(f"[BackupService] Hapus backup (limit {self.MAX_BACKUP_COUNT}): {backup_file.name}")
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
