from datetime import datetime
from uuid import uuid4

import openpyxl
import pytest
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from database.models import Barang, Transaksi, TransaksiDetail
from ui.laporan.laporan_page import LaporanPage


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_excel_export_splits_sales_by_day(qapp, test_db, tmp_path, monkeypatch):
    unique = uuid4().hex
    with test_db.get_session() as session:
        product = Barang(
            kode=f"EXCEL-{unique}",
            nama="Produk Uji Ekspor",
            kategori="Minuman",
            harga_jual=10000,
            stok=20,
        )
        session.add(product)
        session.flush()

        transactions = [
            (datetime(2041, 1, 1, 9), 2, 22200, 20000, "selesai"),
            (datetime(2041, 1, 1, 12), 3, 33300, 30000, "selesai"),
            (datetime(2041, 1, 1, 13), 1, 10000, 10000, "void"),
            (datetime(2041, 1, 2, 10), 1, 11100, 10000, "selesai"),
            (datetime(2041, 1, 3, 11), 2, 20000, 20000, "void"),
        ]
        for index, (sale_date, qty, total, subtotal, status) in enumerate(transactions):
            transaction = Transaksi(
                no_invoice=f"EXCEL-{unique}-{index}",
                tanggal=sale_date,
                total=total,
                status=status,
                ppn_nominal=total - subtotal if status == "selesai" else 0,
                dpp=subtotal,
            )
            transaction.detail.append(TransaksiDetail(
                barang_id=product.id,
                nama_barang=product.nama,
                kode_barang=product.kode,
                qty=qty,
                harga=10000,
                subtotal=subtotal,
            ))
            session.add(transaction)

    filepath = tmp_path / "laporan.xlsx"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(filepath), "Excel Files (*.xlsx)"),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.No)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)

    page = LaporanPage()
    page._set_period("kustom")
    page.date_from.setDate(QDate(2041, 1, 1))
    page.date_to.setDate(QDate(2041, 1, 3))
    page._export_excel()

    workbook = openpyxl.load_workbook(filepath, data_only=True)
    sheet = workbook["Laporan Penjualan"]
    values = [
        sheet.cell(row, column).value
        for row in range(1, sheet.max_row + 1)
        for column in range(1, 7)
    ]

    assert sheet.cell(2, 1).value == "Periode: 01/01/2041 s/d 03/01/2041"
    assert "Periode Penjualan: 01 Januari 2041" in values
    assert "Periode Penjualan: 02 Januari 2041" in values
    assert "Periode Penjualan: 03 Januari 2041" not in values
    header_rows = [
        row for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 1).value == "No"
    ]
    assert len(header_rows) == 2
    daily_totals = [
        row for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 2).value == "TOTAL HARIAN (SUBTOTAL PRODUK)"
    ]
    assert [sheet.cell(row, 4).value for row in daily_totals] == [5, 1]
    assert [sheet.cell(row, 6).value for row in daily_totals] == [50000, 10000]
    daily_sales_rows = [
        row for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 2).value == "TOTAL PENJUALAN"
    ]
    assert [sheet.cell(row, 6).value for row in daily_sales_rows[:2]] == [55500, 11100]
    assert page.card_pendapatan._val_lbl.text() == "Rp 66.600"
    assert page.card_transaksi._val_lbl.text() == "3 Transaksi"
    assert page.card_terjual._val_lbl.text() == "6 Unit"
    assert sum(value for _, value in page.bar_chart._data) == 66600
    assert page.product_table.columnCount() == 6
    assert page._product_data[0]["total_qty"] == 6
    assert "void_qty" not in page._product_data[0]

    report_ranges = [
        ("hari_ini", datetime(2041, 1, 1), datetime(2041, 1, 1, 23, 59, 59), 55500, 2, 5),
        ("minggu_ini", datetime(2041, 1, 1), datetime(2041, 1, 7, 23, 59, 59), 66600, 3, 6),
        ("bulan_ini", datetime(2041, 1, 1), datetime(2041, 1, 31, 23, 59, 59), 66600, 3, 6),
    ]
    for period, date_from, date_to, expected_total, expected_transactions, expected_qty in report_ranges:
        page._current_period = period
        page._load_summary(date_from, date_to)
        page._load_chart(date_from, date_to)
        page._load_payment_methods(date_from, date_to)
        page._load_top_products(date_from, date_to)

        assert page.card_pendapatan._val_lbl.text() == f"Rp {expected_total:,}".replace(",", ".")
        assert page.card_transaksi._val_lbl.text() == f"{expected_transactions} Transaksi"
        assert page.card_terjual._val_lbl.text() == f"{expected_qty} Unit"
        assert sum(value for _, value in page.bar_chart._data) == expected_total
        assert page._product_data[0]["total_qty"] == expected_qty
        assert f"{expected_transactions} Transaksi" in page.total_metode_lbl.text()
    page.close()

    assert sheet.cell(sheet.max_row, 2).value == "TOTAL PENJUALAN"
    assert sheet.cell(sheet.max_row, 6).value == 66600
    grand_subtotal = [
        row for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 2).value == "TOTAL SUBTOTAL PRODUK"
    ]
    assert sheet.cell(grand_subtotal[-1], 4).value == 6
    grand_ppn = [
        sheet.cell(row, 6).value
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 2).value == "PPN"
    ]
    assert grand_ppn[-1] == 6600
