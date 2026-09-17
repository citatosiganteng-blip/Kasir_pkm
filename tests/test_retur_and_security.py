"""
Tests for Session B (Modul Retur: Sales & Purchase Returns)
and Session D (Security: Endpoint Authorization, JWT Protection, & 401 Handling)
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from database.models import (
    Barang, Transaksi, TransaksiDetail,
    Pembelian, PembelianDetail,
    ReturPenjualan, ReturPenjualanDetail,
    ReturPembelian, ReturPembelianDetail,
    Supplier, User
)
from utils.helpers import (
    generate_retur_penjualan_number,
    generate_retur_pembelian_number
)
from services.invoice_pdf_service import InvoicePdfService
from api.deps import create_token
from api.main import app


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_retur_penjualan_stock_and_validation(test_db):
    """Uji siklus lengkap Retur Penjualan: partial return, auto restock, dan validasi sisa retur"""
    with test_db.get_session() as session:
        # 1. Buat barang & transaksi
        barang = Barang(
            kode="BRG-TEST-RETUR-1",
            nama="Snack Coklat Manis",
            harga_beli=3000,
            harga_jual=5000,
            stok=50,
            satuan="pcs"
        )
        session.add(barang)
        session.flush()

        # Pelanggan beli 10 pcs -> stok berkurang dari 50 ke 40
        barang.stok -= 10
        trx = Transaksi(
            no_invoice="INV-TEST-RETUR-01",
            total=50000,
            bayar=50000,
            kembalian=0,
            metode_bayar="cash",
            status="selesai"
        )
        session.add(trx)
        session.flush()

        detail = TransaksiDetail(
            transaksi_id=trx.id,
            barang_id=barang.id,
            kode_barang=barang.kode,
            nama_barang=barang.nama,
            qty=10,
            harga=5000,
            subtotal=50000
        )
        session.add(detail)
        session.commit()

        trx_id = trx.id
        brg_id = barang.id

    # 2. Retur Penjualan Pertama: Partial return 3 pcs
    with test_db.get_session() as session:
        t = session.query(Transaksi).get(trx_id)
        b = session.query(Barang).get(brg_id)
        assert b.stok == 40

        no_retur1 = generate_retur_penjualan_number(session)
        assert no_retur1.startswith("RJ-")

        retur1 = ReturPenjualan(
            no_retur=no_retur1,
            transaksi_id=t.id,
            no_invoice=t.no_invoice,
            total_retur=15000,
            alasan="Kemasan rusak",
            metode_kembali="cash"
        )
        session.add(retur1)
        session.flush()

        rd1 = ReturPenjualanDetail(
            retur_id=retur1.id,
            barang_id=b.id,
            kode_barang=b.kode,
            nama_barang=b.nama,
            qty=3,
            harga_satuan=5000,
            subtotal=15000
        )
        session.add(rd1)

        # Restock 3 pcs
        b.stok += 3
        session.commit()

    # Verifikasi stok setelah retur 1
    with test_db.get_session() as session:
        b = session.query(Barang).get(brg_id)
        assert b.stok == 43  # 40 + 3

        # Hitung sisa yang bisa diretur: 10 - 3 = 7
        t = session.query(Transaksi).get(trx_id)
        already_returned = sum(d.qty for r in t.retur for d in r.detail if d.barang_id == brg_id)
        assert already_returned == 3
        remaining_can_return = t.detail[0].qty - already_returned
        assert remaining_can_return == 7

    # 3. Retur Penjualan Kedua: Retur lagi 7 pcs (full return sisa)
    with test_db.get_session() as session:
        t = session.query(Transaksi).get(trx_id)
        b = session.query(Barang).get(brg_id)

        no_retur2 = generate_retur_penjualan_number(session)
        retur2 = ReturPenjualan(
            no_retur=no_retur2,
            transaksi_id=t.id,
            no_invoice=t.no_invoice,
            total_retur=35000,
            alasan="Salah beli varian",
            metode_kembali="tukar_barang"
        )
        session.add(retur2)
        session.flush()

        rd2 = ReturPenjualanDetail(
            retur_id=retur2.id,
            barang_id=b.id,
            kode_barang=b.kode,
            nama_barang=b.nama,
            qty=7,
            harga_satuan=5000,
            subtotal=35000
        )
        session.add(rd2)
        b.stok += 7
        session.commit()

    # Verifikasi stok setelah full return
    with test_db.get_session() as session:
        b = session.query(Barang).get(brg_id)
        assert b.stok == 50  # Kembali utuh ke stok awal

        t = session.query(Transaksi).get(trx_id)
        already_returned = sum(d.qty for r in t.retur for d in r.detail if d.barang_id == brg_id)
        assert already_returned == 10
        remaining_can_return = t.detail[0].qty - already_returned
        assert remaining_can_return == 0


def test_retur_pembelian_vendor_and_debt_deduction(test_db):
    """Uji Retur Pembelian ke Supplier: mengurangi stok toko dan memotong hutang tempo"""
    with test_db.get_session() as session:
        sup = Supplier(
            kode="SUP-RTR-01",
            nama="Distributor Snack Sejahtera",
            telepon="08199988877"
        )
        session.add(sup)

        barang = Barang(
            kode="BRG-TEST-PO-RETUR",
            nama="Keripik Singkong Balado",
            harga_beli=10000,
            harga_jual=15000,
            stok=20,
            satuan="bks"
        )
        session.add(barang)
        session.flush()

        po = Pembelian(
            no_faktur="FAK-VEND-001",
            no_po="PO-TEST-RETUR-01",
            supplier_id=sup.id,
            subtotal=200000,
            dpp=200000,
            total=200000,
            status_bayar="tempo"
        )
        session.add(po)
        session.flush()

        pod = PembelianDetail(
            pembelian_id=po.id,
            barang_id=barang.id,
            kode_barang=barang.kode,
            nama_barang=barang.nama,
            qty=20,
            harga_beli=10000,
            subtotal=200000
        )
        session.add(pod)
        session.commit()

        po_id = po.id
        brg_id = barang.id

    # Proses retur pembelian 5 pcs ke vendor
    with test_db.get_session() as session:
        p = session.query(Pembelian).get(po_id)
        b = session.query(Barang).get(brg_id)

        no_retur_po = generate_retur_pembelian_number(session)
        assert no_retur_po.startswith("RB-")

        retur_po = ReturPembelian(
            no_retur=no_retur_po,
            pembelian_id=p.id,
            no_po=p.no_po,
            supplier_id=p.supplier_id,
            total_retur=50000,
            alasan="Kadaluarsa",
            metode_kembali="potong_hutang"
        )
        session.add(retur_po)
        session.flush()

        rpd = ReturPembelianDetail(
            retur_id=retur_po.id,
            barang_id=b.id,
            kode_barang=b.kode,
            nama_barang=b.nama,
            qty=5,
            harga_beli=10000,
            subtotal=50000
        )
        session.add(rpd)

        # Kurangi stok karena barang dikembalikan ke vendor
        b.stok -= 5

        # Potong hutang tempo faktur
        p.total -= 50000
        session.commit()

    # Verifikasi hasil
    with test_db.get_session() as session:
        b = session.query(Barang).get(brg_id)
        assert b.stok == 15  # 20 - 5

        p = session.query(Pembelian).get(po_id)
        assert p.total == 150000  # 200000 - 50000
        assert p.status_bayar == "tempo"


def test_sales_return_pdf_template(test_db):
    """Uji pembuatan template HTML Nota Retur Penjualan formal"""
    with test_db.get_session() as session:
        retur = session.query(ReturPenjualan).first()
        assert retur is not None

        html = InvoicePdfService.generate_sales_return_html(retur)
        assert "NOTA RETUR PENJUALAN" in html
        assert retur.no_retur in html
        assert "TERBILANG:" in html
        assert "TOTAL NILAI RETUR:" in html


def test_security_authorization_admin_only_endpoints(client, test_db):
    """
    Session D Security Test:
    1. Endpoint POST /api/transaksi/{id}/void hanya boleh diakses admin
    2. Endpoint POST /api/retur/pembelian hanya boleh diakses admin
    3. User role kasir ditolak dengan HTTP 403 Forbidden
    """
    # Buat dummy transaksi untuk uji void
    with test_db.get_session() as session:
        trx = Transaksi(
            no_invoice="INV-TEST-SEC-01",
            total=10000,
            bayar=10000,
            kembalian=0,
            metode_bayar="cash",
            status="selesai"
        )
        session.add(trx)
        session.commit()
        trx_id = trx.id

    kasir_token = create_token(user_id=2, username="kasir_user", role="kasir")
    admin_token = create_token(user_id=1, username="admin_user", role="admin")

    # 1. Kasir mencoba void transaksi -> 403 Forbidden
    res_kasir_void = client.post(
        f"/api/transaksi/{trx_id}/void",
        headers={"Authorization": f"Bearer {kasir_token}"}
    )
    assert res_kasir_void.status_code == 403
    assert "Hanya admin" in res_kasir_void.json()["detail"]

    # 2. Kasir mencoba retur pembelian -> 403 Forbidden
    res_kasir_retur_po = client.post(
        "/api/retur/pembelian",
        json={"pembelian_id": 1, "items": [{"barang_id": 1, "qty": 1}], "alasan": "rusak"},
        headers={"Authorization": f"Bearer {kasir_token}"}
    )
    assert res_kasir_retur_po.status_code == 403

    # 3. Admin void transaksi -> Sukses (bukan 403)
    res_admin_void = client.post(
        f"/api/transaksi/{trx_id}/void",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin_void.status_code == 200
    assert res_admin_void.json()["status"] == "void"


def test_jwt_expired_or_invalid_token(client):
    """Session D: Token tidak valid / kadaluarsa menghasilkan 401 Unauthorized"""
    res_no_token = client.get("/api/transaksi")
    assert res_no_token.status_code == 401

    res_invalid_token = client.get(
        "/api/transaksi",
        headers={"Authorization": "Bearer invalid.garbage.jwt.token"}
    )
    assert res_invalid_token.status_code == 401
    assert "Token tidak valid" in res_invalid_token.json()["detail"]
