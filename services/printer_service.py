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
        """Cetak struk menggunakan ESC/POS commands"""
        store_name = db.get_setting("store_name", config.STORE_NAME)
        store_address = db.get_setting("store_address", config.STORE_ADDRESS)
        store_phone = db.get_setting("store_phone", config.STORE_PHONE)
        store_tagline = db.get_setting("store_tagline", config.STORE_TAGLINE)
        paper_width = int(db.get_setting("printer_width", str(config.PRINTER_PAPER_WIDTH)))

        chars = 42 if paper_width >= 80 else 32

        def line_separator():
            printer.text("-" * chars + "\n")

        # Header
        printer.set(align="center", bold=True, double_height=True, double_width=True)
        printer.text(f"{store_name}\n")
        printer.set(align="center", bold=False, double_height=False, double_width=False)
        printer.text(f"{store_address}\n")
        printer.text(f"Tel: {store_phone}\n")
        line_separator()

        # Info transaksi
        printer.set(align="left")
        printer.text(f"No: {transaksi.no_invoice}\n")
        printer.text(f"Tgl: {transaksi.tanggal.strftime('%d/%m/%Y %H:%M')}\n")
        kasir_name = transaksi.kasir.username if transaksi.kasir else "-"
        printer.text(f"Kasir: {kasir_name}\n")
        printer.text(f"Bayar: {transaksi.metode_bayar.upper()}\n")
        line_separator()

        # Items
        for detail in transaksi.detail:
            diskon_str = f" (-{detail.diskon:.0f}%)" if detail.diskon > 0 else ""
            printer.text(f"{detail.nama_barang}\n")
            qty_price = f"  {detail.qty} x Rp{detail.harga:,.0f}{diskon_str}"
            subtotal_str = f"Rp{detail.subtotal:,.0f}"
            spaces = chars - len(qty_price) - len(subtotal_str)
            printer.text(qty_price + " " * max(1, spaces) + subtotal_str + "\n")

        line_separator()

        # Totals
        def amount_line(label, amount, bold=False):
            amount_str = f"Rp{amount:,.0f}"
            spaces = chars - len(label) - len(amount_str)
            printer.set(bold=bold)
            printer.text(label + " " * max(1, spaces) + amount_str + "\n")
            printer.set(bold=False)

        if transaksi.diskon_total > 0:
            amount_line("Diskon:", transaksi.diskon_total)

        amount_line("TOTAL:", transaksi.total, bold=True)
        amount_line("Bayar:", transaksi.bayar)
        amount_line("Kembalian:", transaksi.kembalian)

        line_separator()

        # Footer
        printer.set(align="center")
        printer.text(f"\n{store_tagline}\n")
        printer.text(f"Powered by {config.APP_NAME}\n\n")

        # Cut paper
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
        store_name = db.get_setting("store_name", config.STORE_NAME)
        store_address = db.get_setting("store_address", config.STORE_ADDRESS)
        store_tagline = db.get_setting("store_tagline", config.STORE_TAGLINE)
        chars = 40

        lines = [
            store_name.center(chars),
            store_address.center(chars),
            "-" * chars,
            f"No  : {transaksi.no_invoice}",
            f"Tgl : {transaksi.tanggal.strftime('%d/%m/%Y %H:%M')}",
            f"Kasir: {transaksi.kasir.username if transaksi.kasir else '-'}",
            "-" * chars,
        ]

        for d in transaksi.detail:
            lines.append(d.nama_barang)
            diskon = f" (-{d.diskon:.0f}%)" if d.diskon > 0 else ""
            lines.append(f"  {d.qty} x Rp{d.harga:,.0f}{diskon}")
            lines.append(f"  = Rp{d.subtotal:,.0f}")

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
