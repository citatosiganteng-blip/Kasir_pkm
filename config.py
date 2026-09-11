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

# Store Info (bisa diubah via settings)
STORE_NAME = "Toko Kami"
STORE_ADDRESS = "Jl. Contoh No. 1, Kota"
STORE_PHONE = "08xx-xxxx-xxxx"
STORE_TAGLINE = "Terima kasih telah berbelanja!"

# Security
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 60  # seconds

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
