"""
KasirKu API — Pydantic Schemas
Request & response body types untuk semua endpoint
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ──────────────────────────── AUTH ────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    nama_lengkap: Optional[str] = None
    must_change_password: bool = False


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    nama_lengkap: Optional[str] = None
    aktif: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


# ──────────────────────────── BARANG ────────────────────────────

class BarangOut(BaseModel):
    id: int
    kode: str
    barcode: Optional[str] = None
    nama: str
    kategori: Optional[str] = None
    harga_beli: float
    harga_jual: float
    stok: int
    stok_min: int
    satuan: str
    deskripsi: Optional[str] = None
    aktif: bool
    is_low_stock: bool

    model_config = {"from_attributes": True}


class BarangCreate(BaseModel):
    kode: Optional[str] = None          # auto-generate jika kosong
    barcode: Optional[str] = None
    nama: str
    kategori: Optional[str] = None
    harga_beli: float = 0
    harga_jual: float
    stok: int = 0
    stok_min: int = 5
    satuan: str = "pcs"
    deskripsi: Optional[str] = None


class BarangUpdate(BaseModel):
    barcode: Optional[str] = None
    nama: Optional[str] = None
    kategori: Optional[str] = None
    harga_beli: Optional[float] = None
    harga_jual: Optional[float] = None
    stok: Optional[int] = None
    stok_min: Optional[int] = None
    satuan: Optional[str] = None
    deskripsi: Optional[str] = None
    aktif: Optional[bool] = None


# ──────────────────────────── TRANSAKSI ────────────────────────────

class TransaksiDetailIn(BaseModel):
    barang_id: Optional[int] = None
    nama_barang: str
    kode_barang: Optional[str] = None
    qty: int = Field(gt=0)
    harga: float = Field(ge=0)
    diskon: float = Field(default=0, ge=0, le=100)  # persen


class TransaksiCreate(BaseModel):
    items: List[TransaksiDetailIn]
    bayar: float = Field(ge=0)
    metode_bayar: str = "cash"          # cash / qris / transfer
    catatan: Optional[str] = None


class TransaksiDetailOut(BaseModel):
    id: int
    barang_id: Optional[int] = None
    nama_barang: str
    kode_barang: Optional[str] = None
    qty: int
    harga: float
    diskon: float
    subtotal: float

    model_config = {"from_attributes": True}


class TransaksiOut(BaseModel):
    id: int
    no_invoice: str
    tanggal: datetime
    kasir_id: Optional[int] = None
    kasir_username: Optional[str] = None
    total: float
    diskon_total: float
    bayar: float
    kembalian: float
    metode_bayar: str
    status: str
    catatan: Optional[str] = None
    detail: List[TransaksiDetailOut] = []

    model_config = {"from_attributes": True}


# ──────────────────────────── PENGELUARAN ────────────────────────────

class PengeluaranCreate(BaseModel):
    kategori: str
    deskripsi: Optional[str] = None
    nominal: float = Field(gt=0)


class PengeluaranOut(BaseModel):
    id: int
    tanggal: datetime
    kategori: str
    deskripsi: Optional[str] = None
    nominal: float
    user_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ──────────────────────────── LAPORAN ────────────────────────────

class DashboardSummaryOut(BaseModel):
    total_penjualan_hari_ini: float
    jumlah_transaksi_hari_ini: int
    total_penjualan_bulan_ini: float
    jumlah_transaksi_bulan_ini: int
    total_pengeluaran_hari_ini: float
    laba_bersih_hari_ini: float
    stok_menipis_count: int
    top_produk: List[dict]


# ──────────────────────────── PENGATURAN ────────────────────────────

class PengaturanOut(BaseModel):
    kunci: str
    nilai: Optional[str] = None

    model_config = {"from_attributes": True}


class PengaturanUpdate(BaseModel):
    nilai: Optional[str] = None


# ──────────────────────────── RETUR ────────────────────────────

class ReturItemCreate(BaseModel):
    barang_id: Optional[int] = None
    qty: int = Field(gt=0)


class ReturPenjualanCreate(BaseModel):
    transaksi_id: int
    items: List[ReturItemCreate]
    alasan: str
    metode_kembali: str = "cash"  # cash / potong_piutang / tukar_barang


class ReturDetailOut(BaseModel):
    id: int
    barang_id: Optional[int] = None
    kode_barang: Optional[str] = None
    nama_barang: str
    qty: int
    harga_satuan: float
    subtotal: float

    model_config = {"from_attributes": True}


class ReturPenjualanOut(BaseModel):
    id: int
    no_retur: str
    transaksi_id: int
    no_invoice: str
    tanggal: datetime
    total_retur: float
    alasan: Optional[str] = None
    metode_kembali: str
    user_id: Optional[int] = None
    detail: List[ReturDetailOut] = []

    model_config = {"from_attributes": True}


class ReturPembelianCreate(BaseModel):
    pembelian_id: int
    items: List[ReturItemCreate]
    alasan: str
    metode_kembali: str = "potong_hutang"  # potong_hutang / refund_cash


class ReturPembelianDetailOut(BaseModel):
    id: int
    barang_id: Optional[int] = None
    kode_barang: Optional[str] = None
    nama_barang: str
    qty: int
    harga_beli: float
    subtotal: float

    model_config = {"from_attributes": True}


class ReturPembelianOut(BaseModel):
    id: int
    no_retur: str
    pembelian_id: int
    no_po: str
    supplier_id: Optional[int] = None
    tanggal: datetime
    total_retur: float
    alasan: Optional[str] = None
    metode_kembali: str
    user_id: Optional[int] = None
    detail: List[ReturPembelianDetailOut] = []

    model_config = {"from_attributes": True}


# ──────────────────────────── GENERIC ────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True

