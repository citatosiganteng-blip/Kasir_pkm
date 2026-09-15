"""
KasirKu Database Manager
Mengelola koneksi database dan inisialisasi
"""

import bcrypt
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pathlib import Path
from typing import Generator

from database.models import Base, User, Barang, Pengaturan, LoginAttempt
import config


class DatabaseManager:
    """Singleton database manager"""
    _instance = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, db_path: str = None):
        """Inisialisasi database dan buat tabel jika belum ada"""
        if db_path is None:
            db_path = config.DB_PATH

        db_url = f"sqlite:///{db_path}"
        self._engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False
        )

        # Aktifkan WAL mode & foreign keys untuk SQLite
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,   # Objek tetap accessible setelah commit
        )

        # Buat semua tabel
        Base.metadata.create_all(self._engine)

        # Jalankan migrasi kolom ringan untuk SQLite
        self._run_migrations()

        # Seed data awal
        self._seed_initial_data()

        return self

    def _run_migrations(self):
        """Migrasi skema database ringan untuk SQLite jika ada kolom baru"""
        try:
            with self._engine.connect() as conn:
                # --- users: tambah must_change_password jika belum ada ---
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]
                if "must_change_password" not in columns:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0"
                    ))
                    conn.commit()

                # --- login_attempts: buat tabel jika belum ada ---
                # (create_all sudah menangani tabel baru, tapi ini sebagai fallback eksplisit)
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS login_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        last_attempt_at DATETIME NOT NULL
                    )
                    """
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_login_attempts_username "
                    "ON login_attempts (username)"
                ))
                conn.commit()
        except Exception as e:
            print(f"[DatabaseManager] Migration warning: {e}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager yang menghasilkan session database.
        Session otomatis di-commit jika tidak ada exception,
        di-rollback jika ada exception, dan selalu di-close.

        Contoh pemakaian:
            with db.get_session() as session:
                user = session.query(User).first()
        """
        if self._SessionLocal is None:
            raise RuntimeError("Database belum diinisialisasi. Panggil initialize() dulu.")

        session: Session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _seed_initial_data(self):
        """Buat data awal jika belum ada"""
        with self.get_session() as session:
            # Buat admin default jika belum ada
            admin = session.query(User).filter_by(username="admin").first()
            if not admin:
                password_hash = bcrypt.hashpw(
                    "admin123".encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                admin = User(
                    username="admin",
                    password_hash=password_hash,
                    role="admin",
                    nama_lengkap="Administrator",
                    must_change_password=True
                )
                session.add(admin)

                # Buat kasir default
                kasir_hash = bcrypt.hashpw(
                    "kasir123".encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")
                kasir = User(
                    username="kasir",
                    password_hash=kasir_hash,
                    role="kasir",
                    nama_lengkap="Kasir Utama",
                    must_change_password=True
                )
                session.add(kasir)
            else:
                # Jika user default masih memakai password bawaan, tandai must_change_password
                try:
                    if bcrypt.checkpw("admin123".encode("utf-8"), admin.password_hash.encode("utf-8")):
                        admin.must_change_password = True
                    kasir_u = session.query(User).filter_by(username="kasir").first()
                    if kasir_u and bcrypt.checkpw("kasir123".encode("utf-8"), kasir_u.password_hash.encode("utf-8")):
                        kasir_u.must_change_password = True
                except Exception:
                    pass

            # Buat pengaturan awal — hanya jika belum ada (first run).
            # Setelah ini, perubahan store info dilakukan via UI Pengaturan.
            settings = {
                "store_name":    config._STORE_NAME_DEFAULT,
                "store_address": config._STORE_ADDRESS_DEFAULT,
                "store_phone":   config._STORE_PHONE_DEFAULT,
                "store_tagline": config._STORE_TAGLINE_DEFAULT,
                "printer_type":  config.PRINTER_TYPE,
                "printer_port":  config.PRINTER_SERIAL_PORT,
                "printer_width": str(config.PRINTER_PAPER_WIDTH),
                "backup_enabled": "1",
            }
            for kunci, nilai in settings.items():
                existing = session.query(Pengaturan).filter_by(kunci=kunci).first()
                if not existing:
                    session.add(Pengaturan(kunci=kunci, nilai=nilai))

            # Data barang contoh
            sample_data = [
                ("Nasi Goreng", "Makanan", 18000, 25000, 45, "porsi"),
                ("Ayam Bakar", "Makanan", 25000, 35000, 40, "porsi"),
                ("Es Teh Manis", "Minuman", 4000, 10000, 100, "gelas"),
                ("Kopi Hitam", "Minuman", 6000, 15000, 80, "cangkir"),
                ("Keripik Singkong", "Jajanan", 5000, 10000, 60, "bks"),
                ("Aqua Botol 600ml", "Minuman", 2500, 4000, 50, "pcs"),
                ("Indomie Goreng", "Makanan", 2800, 4500, 100, "pcs"),
                ("Teh Botol 350ml", "Minuman", 3000, 5000, 15, "pcs"),
                ("Sabun Lifebuoy", "Kebersihan", 3500, 6000, 30, "pcs"),
                ("Pasta Gigi Pepsodent", "Kebersihan", 8000, 13000, 20, "pcs"),
                ("Beras 1kg", "Sembako", 12000, 15000, 10, "kg"),
            ]

            existing_kodes = {b.kode for b in session.query(Barang.kode).all()}
            counter = 1
            for nama, kat, hb, hj, stok, sat in sample_data:
                existing = session.query(Barang).filter_by(nama=nama).first()
                if not existing:
                    while f"BRG{counter:03d}" in existing_kodes:
                        counter += 1
                    kode_cand = f"BRG{counter:03d}"
                    existing_kodes.add(kode_cand)
                    session.add(Barang(
                        kode=kode_cand,
                        nama=nama,
                        kategori=kat,
                        harga_beli=hb,
                        harga_jual=hj,
                        stok=stok,
                        satuan=sat
                    ))

            # commit dilakukan otomatis oleh context manager

    def reconnect(self, db_path: str = None):
        """
        Tutup semua koneksi lama lalu reinisialisasi engine ke file DB yang sama
        (atau ke db_path baru jika diberikan). Dipanggil setelah restore backup
        agar SQLAlchemy membaca file DB yang sudah diganti.
        """
        try:
            if self._engine is not None:
                self._engine.dispose()
                self._engine = None
            self._SessionLocal = None
        except Exception as e:
            print(f"[DatabaseManager] reconnect dispose warning: {e}")

        self.initialize(db_path=db_path)
        print("[DatabaseManager] Koneksi database berhasil di-reload.")

    def get_setting(self, key: str, default=None) -> str:
        """Ambil nilai pengaturan"""
        with self.get_session() as session:
            setting = session.query(Pengaturan).filter_by(kunci=key).first()
            return setting.nilai if setting else default

    def set_setting(self, key: str, value: str):
        """Simpan nilai pengaturan"""
        with self.get_session() as session:
            setting = session.query(Pengaturan).filter_by(kunci=key).first()
            if setting:
                setting.nilai = value
                setting.updated_at = datetime.now()
            else:
                session.add(Pengaturan(kunci=key, nilai=value))
            # commit dilakukan otomatis oleh context manager


# Global instance
db = DatabaseManager()
