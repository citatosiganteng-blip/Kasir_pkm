"""
KasirKu - Configuration File
Konfigurasi global untuk aplikasi kasir
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Database
DB_NAME = "kasirku.db"
DB_PATH = BASE_DIR / DB_NAME

# App Info
APP_NAME = "KasirKu"
APP_VERSION = "1.0.0"
APP_AUTHOR = "PKM Team"

# Store Info — TIDAK dipakai langsung di kode.
# Nilai ini hanya digunakan sekali saat seed awal database (first run).
# Setelah itu, baca store info SELALU dari DB via db.get_setting().
# Ubah info toko melalui menu Pengaturan > Info Toko di aplikasi.
_STORE_NAME_DEFAULT    = "Toko Kami"
_STORE_ADDRESS_DEFAULT = "Jl. Contoh No. 1, Kota"
_STORE_PHONE_DEFAULT   = "08xx-xxxx-xxxx"
_STORE_TAGLINE_DEFAULT = "Terima kasih telah berbelanja!"

# Security
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 60  # seconds

# --- Role & Registrasi Mandiri ---
# Nama role di database TETAP "admin" / "kasir" (jangan diubah, dipakai di seluruh kode).
# ROLE_LABELS hanya mengubah LABEL yang tampil di layar (misal untuk tema sekolah: Guru/Murid).
ROLE_LABELS = {
    "admin": "Admin",
    "kasir": "Kasir",
}

def get_role_label(role: str) -> str:
    """Ambil label tampilan untuk sebuah role. Fallback ke nama role apa adanya.
    Role dinormalisasi (lower + strip) agar 'Admin'/'ADMIN'/' admin ' tetap dikenali."""
    key = (role or "").strip().lower()
    return ROLE_LABELS.get(key, (role or "").capitalize())

# Registrasi mandiri (tombol "Daftar Akun" di layar login) diaktifkan/nonaktifkan di sini.
SELF_REGISTRATION_ENABLED = True

# Kode rahasia yang wajib dimasukkan agar pendaftar mandiri bisa memilih role "admin".
# Tanpa kode yang benar, akun baru otomatis dibuat sebagai "kasir".
# Kosongkan string ini ("") untuk melarang total pembuatan admin baru lewat layar login.
ADMIN_REGISTER_CODE = "ADMIN2024"

# Stock
DEFAULT_MIN_STOCK = 5

# Printer
PRINTER_TYPE = "usb"  # usb, serial, network
PRINTER_VENDOR_ID = None
PRINTER_PRODUCT_ID = None
PRINTER_SERIAL_PORT = "COM1"
PRINTER_BAUD_RATE = 9600
PRINTER_NETWORK_HOST = "192.168.1.100"
PRINTER_NETWORK_PORT = 9100
PRINTER_PAPER_WIDTH = 80  # 58 or 80

# Backup
BACKUP_DIR = BASE_DIR / "backup"
BACKUP_ENABLED = True
BACKUP_KEEP_DAYS = 30

# Theme
THEME = "dark"

# Colors (Dark Theme)
COLORS = {
    "bg_primary": "#0F1117",
    "bg_secondary": "#1A1D27",
    "bg_card": "#21263A",
    "bg_hover": "#2A2F45",
    "accent": "#6C63FF",
    "accent_light": "#8B84FF",
    "accent_dark": "#4A44CC",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "border": "#2D3250",
    "border_light": "#3D4466",
}
