"""
KasirKu Printer Service
Layanan cetak struk thermal (ESC/POS)
"""

import sys
import traceback
from datetime import datetime
from database.db import db
import config


class PrinterService:
    """Service untuk cetak struk thermal printer"""

    def print_receipt(self, transaksi) -> bool:
        """
        Cetak struk transaksi ke thermal printer.
        Menggunakan ESC/POS via python-escpos.
        Fallback ke Windows Print jika printer tidak terhubung.
        """
        try:
            printer = self._get_printer()
            if printer:
                self._print_escpos(printer, transaksi)
                return True
            else:
                # Fallback: simpan ke file atau print via Windows
                self._print_fallback(transaksi)
                return True
        except Exception as e:
            print(f"[PrinterService] Error: {e}")
            traceback.print_exc()
            # Fallback ke file
            try:
                self._save_receipt_file(transaksi)
            except Exception:
                pass
            return False

    def _get_printer(self):
        """Dapatkan koneksi printer ESC/POS"""
        try:
            from escpos.printer import Usb, Serial, Network

            printer_type = db.get_setting("printer_type", config.PRINTER_TYPE)

            if printer_type == "usb":
                vendor_id = config.PRINTER_VENDOR_ID
                product_id = config.PRINTER_PRODUCT_ID
                if vendor_id and product_id:
                    return Usb(vendor_id, product_id)

            elif printer_type == "serial":
                port = db.get_setting("printer_port", config.PRINTER_SERIAL_PORT)
                return Serial(port, baudrate=config.PRINTER_BAUD_RATE)

            elif printer_type == "network":
                host = db.get_setting("printer_host", config.PRINTER_NETWORK_HOST)
                port = int(db.get_setting("printer_network_port", str(config.PRINTER_NETWORK_PORT)))
                return Network(host, port)

        except Exception as e:
            print(f"[PrinterService] Printer tidak tersedia: {e}")
        return None

    def _print_escpos(self, printer, transaksi):
        """Cetak struk ESC/POS dengan layout khusus thermal 57/58 mm atau 80 mm."""
        import textwrap

        store_name = db.get_setting("store_name", "Toko Kami")
        store_address = db.get_setting("store_address", "")
        store_phone = db.get_setting("store_phone", "")
        store_tagline = db.get_setting("store_tagline", "Terima kasih!")

        try:
            paper_width = int(db.get_setting("printer_width", str(config.PRINTER_PAPER_WIDTH)))
        except (TypeError, ValueError):
            paper_width = 57

        chars = 32 if paper_width < 80 else 42

        # Hard reset printer ke kondisi bersih via ESC @
        # Ini menghapus state double-width/double-height dari job sebelumnya
        try:
            printer._raw(b'\x1b\x40')  # ESC @ = Initialize printer
        except Exception:
            pass

        # Set font A, no scaling, align left sebagai baseline global
        printer.set(align="left", font="a", bold=False,
                    double_height=False, double_width=False,
                    custom_size=False, width=1, height=1)

        def clean(value):
            return " ".join(str(value or "").split())

        def wrapped(value, width=chars):
            value = clean(value)
            if not value:
                return [""]
            return textwrap.wrap(value, width=width, break_long_words=True,
                                 break_on_hyphens=False) or [""]

        def centered(value):
            for part in wrapped(value):
                printer.text(part.center(chars) + "\n")

        def sep():
            printer.text("-" * chars + "\n")

        def amount_line(label, amount, bold=False):
            label = clean(label)
            amount_str = f"Rp{amount:,.0f}"
            spaces = chars - len(label) - len(amount_str)
            if spaces < 1:
                # Tidak muat satu baris — pecah jadi dua
                printer.set(align="left", font="a", bold=bold,
                            double_height=False, double_width=False)
                printer.text(label + "\n")
                printer.text(amount_str.rjust(chars) + "\n")
                printer.set(align="left", font="a", bold=False,
                            double_height=False, double_width=False)
                return
            printer.set(align="left", font="a", bold=bold,
                        double_height=False, double_width=False)
            printer.text(label + " " * spaces + amount_str + "\n")
            printer.set(align="left", font="a", bold=False,
                        double_height=False, double_width=False)

        # --- Header toko ---
        printer.set(align="center", font="a", bold=True,
                    double_height=False, double_width=False)
        centered(store_name)
        printer.set(align="center", font="a", bold=False,
                    double_height=False, double_width=False)
        if clean(store_address):
            centered(store_address)
        if clean(store_phone):
            printer.text(f"Tel: {clean(store_phone)}".center(chars) + "\n")
        sep()

        # --- Info transaksi (compact, 1 baris per field) ---
        printer.set(align="left", font="a", bold=False,
                    double_height=False, double_width=False)
        no_inv = clean(str(transaksi.no_invoice))
        tgl    = transaksi.tanggal.strftime("%d/%m/%y %H:%M")
        kasir  = clean(transaksi.kasir.username if transaksi.kasir else "-")
        bayar  = clean(transaksi.metode_bayar.upper())

        printer.text(f"No : {no_inv}\n")
        printer.text(f"Tgl: {tgl}  {kasir}\n")
        printer.text(f"Byr: {bayar}\n")
        sep()

        # --- Item ---
        for detail in transaksi.detail:
            nama = clean(detail.nama_barang)
            # Nama barang — potong jika melebihi chars, jangan wrap
            if len(nama) > chars:
                nama = nama[:chars - 1] + "."
            printer.text(nama + "\n")

            diskon_str = f"(-{detail.diskon:.0f}%) " if detail.diskon > 0 else ""
            qty_price  = f"  {diskon_str}{detail.qty}x Rp{detail.harga:,.0f}"
            subtotal   = f"Rp{detail.subtotal:,.0f}"
            spaces = chars - len(qty_price) - len(subtotal)
            if spaces >= 1:
                printer.text(qty_price + " " * spaces + subtotal + "\n")
            else:
                printer.text(qty_price + "\n")
                printer.text(subtotal.rjust(chars) + "\n")

        sep()

        # --- Total ---
        if transaksi.diskon_total > 0:
            amount_line("Diskon :", transaksi.diskon_total)
        amount_line("TOTAL  :", transaksi.total, bold=True)
        amount_line("Bayar  :", transaksi.bayar)
        amount_line("Kembali:", transaksi.kembalian)

        # --- Footer ---
        sep()
        printer.set(align="center", font="a", bold=False,
                    double_height=False, double_width=False)
        if clean(store_tagline):
            printer.text(clean(store_tagline).center(chars) + "\n")

        # Feed 3 baris lalu cut
        printer.text("\n\n\n")
        try:
            printer.cut()
        except Exception:
            pass

    def _print_fallback(self, transaksi):
        """Fallback: kirim raw ESC/POS ke printer Windows via win32print, lalu simpan file."""
        # Coba raw ESC/POS ke POS printer via win32print (tidak lewat driver/GDI)
        if sys.platform == "win32":
            if self._print_win32raw(transaksi):
                return
        # Last resort: simpan ke file
        try:
            self._save_receipt_file(transaksi)
        except Exception as e:
            print(f"[PrinterService] Fallback save error: {e}")

    def _find_pos_printer_name(self) -> str | None:
        """Cari nama printer POS/thermal di Windows. Return None jika tidak ada."""
        try:
            import win32print
            # Cek setting dulu
            saved = db.get_setting("printer_name_windows", "")
            if saved:
                return saved
            # Auto-detect: cari printer yang namanya mengandung kata khas thermal
            keywords = ["pos", "thermal", "receipt", "58", "80", "xprinter",
                        "epson tm", "star", "bixolon", "sewoo", "rongta"]
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
                None, 4
            )
            for p in printers:
                name_lower = p["pPrinterName"].lower()
                if any(k in name_lower for k in keywords):
                    print(f"[PrinterService] Auto-detected printer: {p['pPrinterName']}")
                    return p["pPrinterName"]
        except Exception as e:
            print(f"[PrinterService] Printer detect error: {e}")
        return None

    def _print_win32raw(self, transaksi) -> bool:
        """Kirim raw ESC/POS bytes langsung ke printer Windows. Return True jika berhasil."""
        try:
            import win32print

            printer_name = self._find_pos_printer_name()
            if not printer_name:
                print("[PrinterService] Tidak ada printer POS terdeteksi untuk win32raw.")
                return False

            # Build raw ESC/POS bytes
            raw = self._build_escpos_bytes(transaksi)

            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Receipt", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, raw)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)

            print(f"[PrinterService] Raw ESC/POS dikirim ke: {printer_name}")
            return True

        except Exception as e:
            print(f"[PrinterService] win32raw error: {e}")
            traceback.print_exc()
            return False

    def _build_escpos_bytes(self, transaksi) -> bytes:
        """Build raw ESC/POS byte sequence untuk struk 58mm (32 kolom)."""
        store_name    = db.get_setting("store_name",    "Toko Kami")
        store_address = db.get_setting("store_address", "")
        store_phone   = db.get_setting("store_phone",   "")
        store_tagline = db.get_setting("store_tagline", "Terima kasih!")

        try:
            paper_width = int(db.get_setting("printer_width", str(config.PRINTER_PAPER_WIDTH)))
        except (TypeError, ValueError):
            paper_width = 57
        chars = 32 if paper_width < 80 else 42

        def clean(v):
            return " ".join(str(v or "").split())

        def enc(s):
            """Encode string ke bytes, ganti karakter tidak dikenal."""
            return s.encode("ascii", errors="replace")

        def line(s=""):
            return enc(s) + b"\n"

        def sep():
            return enc("-" * chars) + b"\n"

        def center(s):
            return enc(clean(s).center(chars)) + b"\n"

        def rjust_pair(left, right):
            """Kiri-kanan dalam satu baris, pad dengan spasi."""
            left = clean(left)
            spaces = chars - len(left) - len(right)
            if spaces < 1:
                return enc(left) + b"\n" + enc(right.rjust(chars)) + b"\n"
            return enc(left + " " * spaces + right) + b"\n"

        # ESC/POS constants
        ESC_INIT      = b'\x1b\x40'          # Initialize (reset)
        ESC_FONT_A    = b'\x1b\x4d\x00'      # Font A (12x24)
        ESC_ALIGN_L   = b'\x1b\x61\x00'      # Align left
        ESC_ALIGN_C   = b'\x1b\x61\x01'      # Align center
        ESC_BOLD_ON   = b'\x1b\x45\x01'      # Bold on
        ESC_BOLD_OFF  = b'\x1b\x45\x00'      # Bold off
        ESC_DW_OFF    = b'\x1d\x21\x00'      # Normal size (no double width/height)
        GS_CUT        = b'\x1d\x56\x41\x03'  # Full cut with 3-line feed

        buf = bytearray()
        buf += ESC_INIT       # Hard reset — clear state dari job sebelumnya
        buf += ESC_FONT_A     # Pastikan Font A
        buf += ESC_DW_OFF     # No scaling
        buf += ESC_BOLD_OFF

        # --- Header ---
        sn = clean(store_name)
        sa = clean(store_address)
        sp = clean(store_phone)

        buf += ESC_ALIGN_C
        buf += ESC_BOLD_ON
        buf += center(sn)
        buf += ESC_BOLD_OFF
        if sa:
            buf += center(sa)
        if sp:
            buf += enc(f"Tel: {sp}".center(chars)) + b"\n"
        buf += ESC_ALIGN_L
        buf += sep()

        # --- Info transaksi ---
        no_inv = clean(str(transaksi.no_invoice))
        tgl    = transaksi.tanggal.strftime("%d/%m/%y %H:%M")
        kasir  = clean(transaksi.kasir.username if transaksi.kasir else "-")
        bayar  = clean(transaksi.metode_bayar.upper())

        buf += line(f"No : {no_inv}")
        buf += line(f"Tgl: {tgl}  {kasir}")
        buf += line(f"Byr: {bayar}")
        buf += sep()

        # --- Item ---
        for d in transaksi.detail:
            nama = clean(d.nama_barang)
            if len(nama) > chars:
                nama = nama[:chars - 1] + "."
            buf += line(nama)

            diskon_str = f"(-{d.diskon:.0f}%) " if d.diskon > 0 else ""
            qty_price  = f"  {diskon_str}{d.qty}x Rp{d.harga:,.0f}"
            subtotal   = f"Rp{d.subtotal:,.0f}"
            spaces = chars - len(qty_price) - len(subtotal)
            if spaces >= 1:
                buf += enc(qty_price + " " * spaces + subtotal) + b"\n"
            else:
                buf += line(qty_price)
                buf += enc(subtotal.rjust(chars)) + b"\n"

        buf += sep()

        # --- Total ---
        if transaksi.diskon_total > 0:
            buf += rjust_pair("Diskon :", f"Rp{transaksi.diskon_total:,.0f}")
        buf += ESC_BOLD_ON
        buf += rjust_pair("TOTAL  :", f"Rp{transaksi.total:,.0f}")
        buf += ESC_BOLD_OFF
        buf += rjust_pair("Bayar  :", f"Rp{transaksi.bayar:,.0f}")
        buf += rjust_pair("Kembali:", f"Rp{transaksi.kembalian:,.0f}")
        buf += sep()

        # --- Footer ---
        st = clean(store_tagline)
        if st:
            buf += ESC_ALIGN_C
            buf += enc(st.center(chars)) + b"\n"
            buf += ESC_ALIGN_L

        # Cut
        buf += GS_CUT

        return bytes(buf)

    def _save_receipt_file(self, transaksi):
        """Simpan struk ke file teks"""
        receipt_text = self._generate_receipt_text(transaksi)
        receipts_dir = config.BASE_DIR / "receipts"
        receipts_dir.mkdir(exist_ok=True)
        filename = receipts_dir / f"{transaksi.no_invoice}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(receipt_text)
        print(f"[PrinterService] Struk disimpan ke: {filename}")

    def _generate_receipt_text(self, transaksi) -> str:
        """Generate teks struk"""
        import textwrap
        store_name    = db.get_setting("store_name",    "Toko Kami")
        store_address = db.get_setting("store_address", "")
        store_phone   = db.get_setting("store_phone",   "")
        store_tagline = db.get_setting("store_tagline", "Terima kasih telah berbelanja!")
        try:
            paper_width = int(db.get_setting("printer_width", str(config.PRINTER_PAPER_WIDTH)))
        except (TypeError, ValueError):
            paper_width = 57
        chars = 32 if paper_width < 80 else 42

        def wrap(value):
            return textwrap.wrap(
                " ".join(str(value or "").split()), width=chars,
                break_long_words=False, break_on_hyphens=False
            ) or [""]

        lines = [
            *[x.center(chars) for x in wrap(store_name)],
            *[x.center(chars) for x in wrap(store_address)],
            *([x.center(chars) for x in wrap(f"Tel: {store_phone}")] if store_phone.strip() else []),
            "-" * chars,
            f"No  : {transaksi.no_invoice}",
            f"Tgl : {transaksi.tanggal.strftime('%d/%m/%Y %H:%M')}",
            f"Kasir: {transaksi.kasir.username if transaksi.kasir else '-'}",
            "-" * chars,
        ]

        for d in transaksi.detail:
            lines.extend(wrap(d.nama_barang))
            diskon = f" (-{d.diskon:.0f}%)" if d.diskon > 0 else ""
            qty_price = f"{d.qty} x Rp{d.harga:,.0f}{diskon}"
            subtotal = f"Rp{d.subtotal:,.0f}"
            if len(qty_price) + len(subtotal) + 2 <= chars:
                lines.append(qty_price + " " * max(2, chars-len(qty_price)-len(subtotal)) + subtotal)
            else:
                lines.extend("  " + x for x in wrap(qty_price))
                lines.append(subtotal.rjust(chars))

        lines += [
            "-" * chars,
            f"TOTAL    : Rp{transaksi.total:,.0f}",
            f"Bayar    : Rp{transaksi.bayar:,.0f}",
            f"Kembalian: Rp{transaksi.kembalian:,.0f}",
            "-" * chars,
            store_tagline.center(chars),
            f"Powered by {config.APP_NAME}".center(chars),
            "",
        ]
        return "\n".join(lines)
