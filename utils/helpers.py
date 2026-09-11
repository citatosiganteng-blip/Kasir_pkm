"""
KasirKu Utility Helpers
Fungsi-fungsi helper untuk format, tanggal, dan lainnya
"""

from datetime import datetime, date
from typing import Optional


def format_rupiah(amount: float) -> str:
    """Format angka menjadi format Rupiah"""
    try:
        return f"Rp {amount:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def format_rupiah_short(amount: float) -> str:
    """Format rupiah singkat (rb, jt, m)"""
    try:
        if amount >= 1_000_000_000:
            return f"Rp {amount/1_000_000_000:.1f}M"
        elif amount >= 1_000_000:
            return f"Rp {amount/1_000_000:.1f}jt"
        elif amount >= 1_000:
            return f"Rp {amount/1_000:.1f}rb"
        return f"Rp {amount:.0f}"
    except (TypeError, ValueError):
        return "Rp 0"


def format_tanggal(dt: datetime, fmt: str = "%d %B %Y") -> str:
    """Format datetime ke string tanggal Indonesia"""
    if dt is None:
        return ""
    bulan = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    result = dt.strftime("%d {} %Y".format(bulan[dt.month]))
    return result


def format_datetime(dt: datetime) -> str:
    """Format datetime lengkap"""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


def format_tanggal_short(dt: datetime) -> str:
    """Format tanggal pendek"""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse string tanggal"""
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def generate_invoice_number(session) -> str:
    """Generate nomor invoice unik"""
    from database.models import Transaksi
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INV-{today}-"

    # Cari invoice terakhir hari ini
    last = session.query(Transaksi).filter(
        Transaksi.no_invoice.like(f"{prefix}%")
    ).order_by(Transaksi.no_invoice.desc()).first()

    if last:
        try:
            last_num = int(last.no_invoice.split("-")[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1

    return f"{prefix}{new_num:03d}"


def generate_item_code(session) -> str:
    """Generate kode barang otomatis"""
    from database.models import Barang
    last = session.query(Barang).order_by(Barang.id.desc()).first()
    if last:
        try:
            last_num = int(last.kode.replace("BRG", ""))
            new_num = last_num + 1
        except (ValueError, AttributeError):
            new_num = (last.id or 0) + 1
    else:
        new_num = 1
    return f"BRG{new_num:03d}"


def truncate_text(text: str, max_len: int = 30) -> str:
    """Potong teks jika terlalu panjang"""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def get_today_range():
    """Ambil range datetime hari ini"""
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return start, end


def get_month_range(year: int = None, month: int = None):
    """Ambil range datetime satu bulan"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    from calendar import monthrange
    _, last_day = monthrange(year, month)

    start = datetime(year, month, 1, 0, 0, 0)
    end = datetime(year, month, last_day, 23, 59, 59)
    return start, end
