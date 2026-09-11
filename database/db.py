"""
KasirKu Database Manager
Mengelola koneksi database dan inisialisasi
"""

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pathlib import Path

from database.models import Base, User, Barang, Pengaturan
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
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

        # Buat semua tabel
        Base.metadata.create_all(self._engine)

        # Seed data awal
        self._seed_initial_data()

        return self

    def get_session(self) -> Session:
        """Ambil session database"""
        if self._SessionLocal is None:
            raise RuntimeError("Database belum diinisialisasi. Panggil initialize() dulu.")
        return self._SessionLocal()

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
                    nama_lengkap="Administrator"
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
                    nama_lengkap="Kasir Utama"
                )
                session.add(kasir)

            # Buat pengaturan awal
            settings = {
                "store_name": config.STORE_NAME,
                "store_address": config.STORE_ADDRESS,
                "store_phone": config.STORE_PHONE,
                "store_tagline": config.STORE_TAGLINE,
                "printer_type": config.PRINTER_TYPE,
                "printer_port": config.PRINTER_SERIAL_PORT,
                "printer_width": str(config.PRINTER_PAPER_WIDTH),
                "backup_enabled": "1",
            }
            for kunci, nilai in settings.items():
                existing = session.query(Pengaturan).filter_by(kunci=kunci).first()
                if not existing:
                    session.add(Pengaturan(kunci=kunci, nilai=nilai))

            # Data barang contoh
            barang_count = session.query(Barang).count()
            if barang_count == 0:
                sample_items = [
                    Barang(kode="BRG001", barcode="8991234567890", nama="Aqua Botol 600ml",
                           kategori="Minuman", harga_beli=2500, harga_jual=4000, stok=50, satuan="pcs"),
                    Barang(kode="BRG002", barcode="8992345678901", nama="Indomie Goreng",
                           kategori="Makanan", harga_beli=2800, harga_jual=4500, stok=100, satuan="pcs"),
                    Barang(kode="BRG003", barcode="8993456789012", nama="Teh Botol 350ml",
                           kategori="Minuman", harga_beli=3000, harga_jual=5000, stok=3, stok_min=5, satuan="pcs"),
                    Barang(kode="BRG004", barcode="8994567890123", nama="Sabun Lifebuoy",
                           kategori="Kebersihan", harga_beli=3500, harga_jual=6000, stok=30, satuan="pcs"),
                    Barang(kode="BRG005", barcode="8995678901234", nama="Pasta Gigi Pepsodent",
                           kategori="Kebersihan", harga_beli=8000, harga_jual=13000, stok=20, satuan="pcs"),
                    Barang(kode="BRG006", barcode="8996789012345", nama="Beras 1kg",
                           kategori="Sembako", harga_beli=12000, harga_jual=15000, stok=2, stok_min=5, satuan="kg"),
                ]
                for item in sample_items:
                    session.add(item)

            session.commit()

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
            session.commit()


# Global instance
db = DatabaseManager()
