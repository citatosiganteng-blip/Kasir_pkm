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


class Pelanggan(Base):
    __tablename__ = "pelanggan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(50), unique=True, nullable=False)
    nama = Column(String(150), nullable=False)
    telepon = Column(String(50), nullable=True)
    alamat = Column(Text, nullable=True)
    email = Column(String(100), nullable=True)
    npwp = Column(String(50), nullable=True)
    aktif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    transaksi = relationship("Transaksi", back_populates="pelanggan")

    def __repr__(self):
        return f"<Pelanggan {self.kode} - {self.nama}>"


class Supplier(Base):
    __tablename__ = "supplier"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(50), unique=True, nullable=False)
    nama = Column(String(150), nullable=False)
    kontak = Column(String(100), nullable=True)
    telepon = Column(String(50), nullable=True)
    alamat = Column(Text, nullable=True)
    email = Column(String(100), nullable=True)
    npwp = Column(String(50), nullable=True)
    aktif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    pembelian = relationship("Pembelian", back_populates="supplier")

    def __repr__(self):
        return f"<Supplier {self.kode} - {self.nama}>"


class Transaksi(Base):
    __tablename__ = "transaksi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    no_invoice = Column(String(50), unique=True, nullable=False)
    tanggal = Column(DateTime, default=datetime.now)
    kasir_id = Column(Integer, ForeignKey("users.id"))
    pelanggan_id = Column(Integer, ForeignKey("pelanggan.id"), nullable=True)
    nama_pelanggan = Column(String(150), nullable=True)
    alamat_pelanggan = Column(Text, nullable=True)
    telepon_pelanggan = Column(String(50), nullable=True)
    npwp_pelanggan = Column(String(50), nullable=True)
    total = Column(Float, default=0)
    diskon_total = Column(Float, default=0)
    bayar = Column(Float, default=0)
    kembalian = Column(Float, default=0)
    metode_bayar = Column(String(20), default="cash")  # cash / qris / transfer
    status = Column(String(20), default="selesai")  # selesai / void
    status_bayar = Column(String(20), default="lunas")  # lunas / tempo
    jatuh_tempo = Column(DateTime, nullable=True)
    catatan = Column(Text, nullable=True)

    # Rincian Pajak (PPN / PPh)
    dpp = Column(Float, default=0)
    ppn_persen = Column(Float, default=0)
    ppn_nominal = Column(Float, default=0)
    pph_persen = Column(Float, default=0)
    pph_nominal = Column(Float, default=0)
    no_faktur_pajak = Column(String(50), nullable=True)

    kasir = relationship("User", back_populates="transaksi")
    pelanggan = relationship("Pelanggan", back_populates="transaksi")
    detail = relationship("TransaksiDetail", back_populates="transaksi",
                          cascade="all, delete-orphan")
    retur = relationship("ReturPenjualan", back_populates="transaksi",
                         cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaksi {self.no_invoice}>"


class ReturPenjualan(Base):
    __tablename__ = "retur_penjualan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    no_retur = Column(String(50), unique=True, nullable=False)  # RJ-YYYYMMDD-001
    transaksi_id = Column(Integer, ForeignKey("transaksi.id"), nullable=False)
    no_invoice = Column(String(50), nullable=False)
    tanggal = Column(DateTime, default=datetime.now)
    total_retur = Column(Float, default=0)
    alasan = Column(Text, nullable=True)
    metode_kembali = Column(String(20), default="cash")  # cash / potong_piutang / tukar_barang
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    transaksi = relationship("Transaksi", back_populates="retur")
    user = relationship("User")
    detail = relationship("ReturPenjualanDetail", back_populates="retur", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReturPenjualan {self.no_retur} for {self.no_invoice}>"


class ReturPenjualanDetail(Base):
    __tablename__ = "retur_penjualan_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    retur_id = Column(Integer, ForeignKey("retur_penjualan.id"), nullable=False)
    barang_id = Column(Integer, ForeignKey("barang.id"), nullable=True)
    kode_barang = Column(String(50), nullable=True)
    nama_barang = Column(String(200), nullable=False)
    qty = Column(Integer, default=1)
    harga_satuan = Column(Float, default=0)
    subtotal = Column(Float, default=0)

    retur = relationship("ReturPenjualan", back_populates="detail")
    barang = relationship("Barang")

    def __repr__(self):
        return f"<ReturPenjualanDetail {self.nama_barang} x{self.qty}>"


class Pembelian(Base):
    __tablename__ = "pembelian"

    id = Column(Integer, primary_key=True, autoincrement=True)
    no_faktur = Column(String(50), nullable=False)  # Nomor faktur dari vendor/supplier
    no_po = Column(String(50), unique=True, nullable=False)  # Nomor PO internal toko
    supplier_id = Column(Integer, ForeignKey("supplier.id"), nullable=True)
    tanggal = Column(DateTime, default=datetime.now)
    jatuh_tempo = Column(DateTime, nullable=True)
    subtotal = Column(Float, default=0)
    dpp = Column(Float, default=0)
    ppn_persen = Column(Float, default=0)
    ppn_nominal = Column(Float, default=0)
    pph_persen = Column(Float, default=0)
    pph_nominal = Column(Float, default=0)
    total = Column(Float, default=0)
    status_bayar = Column(String(20), default="lunas")  # lunas / tempo
    status_barang = Column(String(20), default="diterima")  # diterima / dipesan
    metode_bayar = Column(String(20), default="transfer")
    catatan = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="pembelian")
    user = relationship("User")
    detail = relationship("PembelianDetail", back_populates="pembelian",
                          cascade="all, delete-orphan")
    retur = relationship("ReturPembelian", back_populates="pembelian",
                         cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pembelian {self.no_po} ({self.no_faktur})>"


class PembelianDetail(Base):
    __tablename__ = "pembelian_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pembelian_id = Column(Integer, ForeignKey("pembelian.id"))
    barang_id = Column(Integer, ForeignKey("barang.id"), nullable=True)
    kode_barang = Column(String(50), nullable=True)
    nama_barang = Column(String(200), nullable=False)
    qty = Column(Integer, default=1)
    harga_beli = Column(Float, default=0)
    subtotal = Column(Float, default=0)

    pembelian = relationship("Pembelian", back_populates="detail")
    barang = relationship("Barang")

    def __repr__(self):
        return f"<PembelianDetail {self.nama_barang} x{self.qty}>"


class ReturPembelian(Base):
    __tablename__ = "retur_pembelian"

    id = Column(Integer, primary_key=True, autoincrement=True)
    no_retur = Column(String(50), unique=True, nullable=False)  # RB-YYYYMMDD-001
    pembelian_id = Column(Integer, ForeignKey("pembelian.id"), nullable=False)
    no_po = Column(String(50), nullable=False)
    supplier_id = Column(Integer, ForeignKey("supplier.id"), nullable=True)
    tanggal = Column(DateTime, default=datetime.now)
    total_retur = Column(Float, default=0)
    alasan = Column(Text, nullable=True)
    metode_kembali = Column(String(20), default="potong_hutang")  # potong_hutang / refund_cash
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    pembelian = relationship("Pembelian", back_populates="retur")
    supplier = relationship("Supplier")
    user = relationship("User")
    detail = relationship("ReturPembelianDetail", back_populates="retur", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReturPembelian {self.no_retur} for {self.no_po}>"


class ReturPembelianDetail(Base):
    __tablename__ = "retur_pembelian_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    retur_id = Column(Integer, ForeignKey("retur_pembelian.id"), nullable=False)
    barang_id = Column(Integer, ForeignKey("barang.id"), nullable=True)
    kode_barang = Column(String(50), nullable=True)
    nama_barang = Column(String(200), nullable=False)
    qty = Column(Integer, default=1)
    harga_beli = Column(Float, default=0)
    subtotal = Column(Float, default=0)

    retur = relationship("ReturPembelian", back_populates="detail")
    barang = relationship("Barang")

    def __repr__(self):
        return f"<ReturPembelianDetail {self.nama_barang} x{self.qty}>"


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


class LoginAttempt(Base):
    """Menyimpan percobaan login gagal agar persistent setelah restart."""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, index=True, unique=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<LoginAttempt {self.username} attempts={self.attempts}>"
