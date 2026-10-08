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
        store_tagline = db.get_setting("store_tagline", "Terima kasih telah berbelanja!")

        try:
            paper_width = int(db.get_setting("printer_width", str(config.PRINTER_PAPER_WIDTH)))
        except (TypeError, ValueError):
            paper_width = 57

        # Printer thermal 57/58 mm dengan font A normal umumnya muat 32 kolom.
        chars = 32 if paper_width < 80 else 42

        def clean(value):
            return " ".join(str(value or "").split())

        def wrapped(value, width=chars):
            value = clean(value)
            if not value:
                return [""]
            return textwrap.wrap(value, width=width, break_long_words=False,
                                 break_on_hyphens=False) or [""]

        def centered(value):
            for part in wrapped(value):
                printer.text(part.center(chars) + "\n")

        def line_separator():
            printer.text("-" * chars + "\n")

        def amount_line(label, amount, bold=False):
            label = clean(label)
            amount_str = f"Rp{amount:,.0f}"
            if len(label) + len(amount_str) + 1 > chars:
                printer.set(bold=bold)
                printer.text(label[:chars] + "\n")
                printer.text(amount_str.rjust(chars) + "\n")
                printer.set(bold=False)
                return
            spaces = chars - len(label) - len(amount_str)
            printer.set(bold=bold)
            printer.text(label + " " * max(1, spaces) + amount_str + "\n")
            printer.set(bold=False)

        # Jangan gunakan double_width pada kertas 57/58 mm.
        printer.set(align="left", font="a", bold=False,
                    double_height=False, double_width=False)

        printer.set(align="center", bold=True, double_height=False, double_width=False)
        centered(store_name)
        printer.set(align="center", bold=False, double_height=False, double_width=False)
        centered(store_address)
        if clean(store_phone):
            centered(f"Tel: {store_phone}")
        line_separator()

        printer.set(align="left", bold=False, double_height=False, double_width=False)
        for label, value in (
            ("No:", transaksi.no_invoice),
            ("Tgl:", transaksi.tanggal.strftime("%d/%m/%Y %H:%M")),
            ("Kasir:", transaksi.kasir.username if transaksi.kasir else "-"),
            ("Bayar:", transaksi.metode_bayar.upper()),
        ):
            for part in wrapped(f"{label} {value}"):
                printer.text(part + "\n")
        line_separator()

        for detail in transaksi.detail:
            for part in wrapped(detail.nama_barang):
                printer.text(part + "\n")

            diskon_str = f" (-{detail.diskon:.0f}%)" if detail.diskon > 0 else ""
            qty_price = f"{detail.qty} x Rp{detail.harga:,.0f}{diskon_str}"
            subtotal_str = f"Rp{detail.subtotal:,.0f}"

            if len(qty_price) + len(subtotal_str) + 2 <= chars:
                spaces = chars - len(qty_price) - len(subtotal_str)
                printer.text(qty_price + " " * max(2, spaces) + subtotal_str + "\n")
            else:
                for part in wrapped(qty_price):
                    printer.text("  " + part + "\n")
                printer.text(subtotal_str.rjust(chars) + "\n")

        line_separator()
        if transaksi.diskon_total > 0:
            amount_line("Diskon:", transaksi.diskon_total)
        amount_line("TOTAL:", transaksi.total, bold=True)
        amount_line("Bayar:", transaksi.bayar)
        amount_line("Kembalian:", transaksi.kembalian)

        line_separator()
        printer.set(align="center", bold=False, double_height=False, double_width=False)
        centered(store_tagline)
        centered(f"Powered by {config.APP_NAME}")
        printer.text("\n")

        try:
            printer.cut()
        except Exception:
            printer.text("\n\n\n")

    def _print_fallback(self, transaksi):
        """Fallback: print via Windows default printer atau simpan file"""
        receipt_text = self._generate_receipt_text(transaksi)
        # Coba Windows print
        if sys.platform == "win32":
            try:
                import tempfile, os, subprocess
                tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                                  delete=False, encoding="utf-8")
                tmp.write(receipt_text)
                tmp.close()
                os.startfile(tmp.name, "print")
            except Exception as e:
                print(f"[PrinterService] Windows print fallback error: {e}")

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
