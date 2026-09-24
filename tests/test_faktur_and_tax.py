"""
Unit tests for Faktur Penjualan (A4/PDF), Faktur Pembelian (PO & Restock),
and Perpajakan (PPN/PPh & Rekapitulasi).
"""

import os
from datetime import datetime, timedelta
import pytest
from openpyxl import load_workbook

from database.models import Barang, Transaksi, TransaksiDetail, Supplier, Pelanggan, Pembelian, PembelianDetail
from utils.helpers import (
    terbilang, generate_po_number, generate_supplier_code,
    generate_customer_code, generate_tax_invoice_number
)
from services.invoice_pdf_service import InvoicePdfService


def test_terbilang_conversion():
    """Uji konversi angka nominal ke teks terbilang bahasa Indonesia"""
    assert terbilang(0) == "Nol Rupiah"
    assert terbilang(1000) == "Seribu Rupiah"
    assert terbilang(1500000) == "Satu Juta Lima Ratus Ribu Rupiah"
    assert terbilang(25000) == "Dua Puluh Lima Ribu Rupiah"
    assert terbilang(100100) == "Seratus Ribu Seratus Rupiah"


def test_code_generators(test_db):
    """Uji generator otomatis kode PO, Supplier, Pelanggan, dan Faktur Pajak"""
    with test_db.get_session() as session:
        po_num = generate_po_number(session)
        assert po_num.startswith("PO-")

        sup_code = generate_supplier_code(session)
        assert sup_code.startswith("SUP")

        plg_code = generate_customer_code(session)
        assert plg_code.startswith("PLG")

        fp_num = generate_tax_invoice_number(session)
        assert fp_num.startswith("FP-")


def test_pembelian_and_auto_stock_increment(test_db):
    """Uji faktur pembelian supplier: otomatis menambah stok barang dan update harga beli"""
    with test_db.get_session() as session:
        # 1. Buat supplier & barang
        supplier = Supplier(
            kode="SUP999",
            nama="PT Sumber Makmur Jaya",
            telepon="08123456789",
            npwp="01.999.888.7-654.000"
        )
        session.add(supplier)

        barang = Barang(
            kode="BRG999",
            nama="Biskuit Kaleng Kaliber",
            harga_beli=20000,
            harga_jual=28000,
            stok=15
        )
        session.add(barang)
        session.flush()

        sup_id = supplier.id
        brg_id = barang.id

        # 2. Buat Faktur Pembelian (PO) dengan restock 20 pcs @ Rp 22.000
        qty_masuk = 20
        harga_beli_baru = 22000
        dpp = qty_masuk * harga_beli_baru  # 440.000
        ppn = dpp * 0.11  # 48.400
        grand_total = dpp + ppn

        po = Pembelian(
            no_faktur="INV-VENDOR-7788",
            no_po="PO-20260917-999",
            supplier_id=sup_id,
            tanggal=datetime.now(),
            subtotal=dpp,
            dpp=dpp,
            ppn_persen=11.0,
            ppn_nominal=ppn,
            total=grand_total,
            status_bayar="lunas"
        )
        session.add(po)
        session.flush()

        detail = PembelianDetail(
            pembelian_id=po.id,
            barang_id=brg_id,
            kode_barang=barang.kode,
            nama_barang=barang.nama,
            qty=qty_masuk,
            harga_beli=harga_beli_baru,
            subtotal=dpp
        )
        session.add(detail)

        # Restock stok barang
        barang.stok += qty_masuk
        barang.harga_beli = harga_beli_baru

    # Verifikasi data setelah commit
    with test_db.get_session() as session:
        saved_barang = session.query(Barang).filter_by(kode="BRG999").first()
        assert saved_barang.stok == 35  # 15 + 20
        assert saved_barang.harga_beli == 22000

        saved_po = session.query(Pembelian).filter_by(no_po="PO-20260917-999").first()
        assert saved_po is not None
        assert saved_po.supplier.nama == "PT Sumber Makmur Jaya"
        assert len(saved_po.detail) == 1
        assert saved_po.total == 488400


def test_sales_invoice_pdf_and_html(test_db, tmp_path):
    """Uji pembuatan HTML Faktur Penjualan dan konversi ke file PDF A4"""
    with test_db.get_session() as session:
        pelanggan = Pelanggan(
            kode="PLG001",
            nama="Toko Berkah Abadi",
            telepon="08198765432",
            alamat="Jl. Sudirman No. 12, Jakarta",
            npwp="02.345.678.9-012.000"
        )
        session.add(pelanggan)
        session.flush()

        trx = Transaksi(
            no_invoice="INV-TEST-PDF-001",
            tanggal=datetime.now(),
            pelanggan_id=pelanggan.id,
            nama_pelanggan=pelanggan.nama,
            alamat_pelanggan=pelanggan.alamat,
            telepon_pelanggan=pelanggan.telepon,
            npwp_pelanggan=pelanggan.npwp,
            dpp=100000,
            ppn_persen=11.0,
            ppn_nominal=11000,
            total=111000,
            bayar=120000,
            kembalian=9000,
            metode_bayar="transfer",
            status_bayar="lunas"
        )
        session.add(trx)
        session.flush()

        det = TransaksiDetail(
            transaksi_id=trx.id,
            nama_barang="Produk Unggulan",
            kode_barang="BRG001",
            qty=2,
            harga=50000,
            diskon=0,
            subtotal=100000
        )
        session.add(det)
        session.commit()

        # Generate HTML
        html = InvoicePdfService.generate_sales_invoice_html(trx)
        assert "FAKTUR PENJUALAN" in html
        assert "INV-TEST-PDF-001" in html
        assert "Toko Berkah Abadi" in html
        assert "111,000" in html or "111.000" in html

        # Generate PDF
        pdf_file = tmp_path / "faktur_test.pdf"
        ok = InvoicePdfService.save_html_to_pdf(html, pdf_file)
        assert ok is True
        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 1000  # Valid PDF size


def test_tax_report_excel_generation(test_db, tmp_path):
    """Uji ekspor rekapitulasi SPT Pajak (PPN & PPh) ke file Excel multi-sheet"""
    start_dt = datetime.now() - timedelta(days=1)
    end_dt = datetime.now() + timedelta(days=1)
    excel_path = tmp_path / "rekap_pajak.xlsx"

    ok = InvoicePdfService.export_tax_report_to_excel(start_dt, end_dt, excel_path)
    assert ok is True
    assert excel_path.exists()

    # Periksa lembar kerja di dalam file Excel
    wb = load_workbook(excel_path)
    sheet_names = wb.sheetnames
    assert "Rekap SPT Pajak Masa" in sheet_names
    assert "Pajak Keluaran (Sales)" in sheet_names
    assert "Pajak Masukan (Purchases)" in sheet_names
