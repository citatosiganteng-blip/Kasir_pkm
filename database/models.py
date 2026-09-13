"""
KasirKu Database Models
SQLAlchemy ORM models
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text,
    ForeignKey, Boolean, create_engine
)
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="kasir")  # admin / kasir
    nama_lengkap = Column(String(100), nullable=True)
    aktif = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    transaksi = relationship("Transaksi", back_populates="kasir")
    pengeluaran = relationship("Pengeluaran", back_populates="user")
    log_drawer = relationship("LogDrawer", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Barang(Base):
    __tablename__ = "barang"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(50), unique=True, nullable=False)
    barcode = Column(String(100), unique=True, nullable=True)
    nama = Column(String(200), nullable=False)
    kategori = Column(String(100), nullable=True)
    harga_beli = Column(Float, default=0)
    harga_jual = Column(Float, nullable=False)
    stok = Column(Integer, default=0)
    stok_min = Column(Integer, default=5)
    satuan = Column(String(20), default="pcs")
    deskripsi = Column(Text, nullable=True)
    aktif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    detail_transaksi = relationship("TransaksiDetail", back_populates="barang")

    def __repr__(self):
        return f"<Barang {self.kode} - {self.nama}>"

    @property
    def is_low_stock(self):
        return self.stok <= self.stok_min


class Transaksi(Base):
    __tablename__ = "transaksi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    no_invoice = Column(String(50), unique=True, nullable=False)
    tanggal = Column(DateTime, default=datetime.now)
    kasir_id = Column(Integer, ForeignKey("users.id"))
    total = Column(Float, default=0)
    diskon_total = Column(Float, default=0)
    bayar = Column(Float, default=0)
    kembalian = Column(Float, default=0)
    metode_bayar = Column(String(20), default="cash")  # cash / qris / transfer
    status = Column(String(20), default="selesai")  # selesai / void
    catatan = Column(Text, nullable=True)

    kasir = relationship("User", back_populates="transaksi")
    detail = relationship("TransaksiDetail", back_populates="transaksi",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaksi {self.no_invoice}>"


class TransaksiDetail(Base):
    __tablename__ = "transaksi_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaksi_id = Column(Integer, ForeignKey("transaksi.id"))
    barang_id = Column(Integer, ForeignKey("barang.id"), nullable=True)
    nama_barang = Column(String(200), nullable=False)
    kode_barang = Column(String(50), nullable=True)
    qty = Column(Integer, default=1)
    harga = Column(Float, default=0)
    diskon = Column(Float, default=0)  # dalam persen
    subtotal = Column(Float, default=0)

    transaksi = relationship("Transaksi", back_populates="detail")
    barang = relationship("Barang", back_populates="detail_transaksi")

    def __repr__(self):
        return f"<TransaksiDetail {self.nama_barang} x{self.qty}>"


class Pengeluaran(Base):
    __tablename__ = "pengeluaran"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tanggal = Column(DateTime, default=datetime.now)
    kategori = Column(String(100), nullable=False)
    deskripsi = Column(Text, nullable=True)
    nominal = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="pengeluaran")

    def __repr__(self):
        return f"<Pengeluaran {self.kategori} Rp{self.nominal:,.0f}>"


class LogDrawer(Base):
    __tablename__ = "log_drawer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"))
    aksi = Column(String(50), nullable=False)  # auto / manual
    keterangan = Column(Text, nullable=True)

    user = relationship("User", back_populates="log_drawer")

    def __repr__(self):
        return f"<LogDrawer {self.aksi} at {self.timestamp}>"


class Pengaturan(Base):
    __tablename__ = "pengaturan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kunci = Column(String(100), unique=True, nullable=False)
    nilai = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Pengaturan {self.kunci}={self.nilai}>"
