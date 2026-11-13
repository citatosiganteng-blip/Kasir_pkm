import asyncio
import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from uuid import uuid4

import openpyxl
import pytest
from fastapi import HTTPException

from api.routers.laporan import export_csv, export_xlsx, laporan_rentang
from database.models import Barang, Transaksi, TransaksiDetail


def _insert_report_transactions(test_db, year=2042):
    unique = uuid4().hex
    with test_db.get_session() as session:
        product = Barang(
            kode=f"MOBILE-{unique}",
            nama="Produk Laporan Mobile",
            kategori="Minuman",
            harga_jual=10000,
            stok=20,
        )
        session.add(product)
        session.flush()

        transactions = [
            (datetime(year, 2, 1, 9), 2, 22200, 20000, 2200, "selesai"),
            (datetime(year, 2, 1, 10), 1, 10000, 10000, 0, "void"),
            (datetime(year, 2, 2, 11), 1, 11100, 10000, 1100, "selesai"),
            (datetime(year, 2, 3, 12), 4, 40000, 40000, 0, "void"),
        ]
        for index, (sale_date, qty, total, subtotal, ppn, status) in enumerate(transactions):
            transaction = Transaksi(
                no_invoice=f"MOBILE-{unique}-{index}",
                tanggal=sale_date,
                total=total,
                dpp=subtotal,
                ppn_nominal=ppn,
                status=status,
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


def test_mobile_report_range_excludes_void_transactions(test_db):
    _insert_report_transactions(test_db)

    report = laporan_rentang(
        tanggal_mulai=date(2042, 2, 1),
        tanggal_selesai=date(2042, 2, 3),
        _={},
    )

    assert report["jumlah_transaksi"] == 2
    assert report["jumlah_barang_terjual"] == 3
    assert report["total_subtotal_produk"] == 30000
    assert report["total_ppn"] == 3300
    assert report["total_penjualan"] == 33300
    assert report["top_produk"] == [{
        "nama": "Produk Laporan Mobile",
        "qty": 3,
        "subtotal": 30000,
    }]


def test_mobile_excel_export_groups_completed_sales_by_day(test_db):
    _insert_report_transactions(test_db, year=2043)

    response = export_xlsx(
        tanggal_mulai=date(2043, 2, 1),
        tanggal_selesai=date(2043, 2, 3),
        _={},
    )

    async def read_body():
        return b"".join([chunk async for chunk in response.body_iterator])

    workbook_bytes = asyncio.run(read_body())
    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes), data_only=True)
    sheet = workbook["Laporan Penjualan"]

    period_titles = [
        sheet.cell(row, 1).value
        for row in range(1, sheet.max_row + 1)
        if str(sheet.cell(row, 1).value or "").startswith("Periode Penjualan:")
    ]
    assert period_titles == [
        "Periode Penjualan: 01 Februari 2043",
        "Periode Penjualan: 02 Februari 2043",
    ]
    headers = [
        row for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 1).value == "No"
    ]
    assert len(headers) == 2
    assert "Tidak Terjual/Batal (Qty)" not in [
        sheet.cell(headers[0], column).value for column in range(1, 7)
    ]
    assert sheet.cell(sheet.max_row, 2).value == "TOTAL PENJUALAN"
    assert sheet.cell(sheet.max_row, 6).value == 33300
    assert "Pembelian & Restock" in workbook.sheetnames


def test_mobile_csv_export_excludes_void_transactions(test_db):
    _insert_report_transactions(test_db, year=2044)

    response = export_csv(
        tanggal_mulai=date(2044, 2, 1),
        tanggal_selesai=date(2044, 2, 3),
        _={},
    )

    async def read_body():
        return b"".join([chunk async for chunk in response.body_iterator])

    rows = list(csv.reader(StringIO(asyncio.run(read_body()).decode("utf-8-sig"))))

    assert rows[0][-1] == "Subtotal Produk"
    assert len(rows) == 2
    assert rows[1][1] == "Produk Laporan Mobile"
    assert rows[1][3] == "3"
    assert rows[1][5] == "30000.0"


def test_mobile_report_rejects_reversed_date_range():
    with pytest.raises(HTTPException, match="Tanggal selesai tidak boleh"):
        laporan_rentang(
            tanggal_mulai=date(2042, 2, 3),
            tanggal_selesai=date(2042, 2, 1),
            _={},
        )
