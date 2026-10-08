"""
Unit tests for Pelanggan (Customer Management) and Pengeluaran (Expense Management)
Covering CRUD, search, role authorization, and POS integration.
"""

import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient

from database.models import Pelanggan, Pengeluaran, Barang, Transaksi
from api.deps import create_token
from api.main import app


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_pelanggan_crud_and_validation(client, test_db):
    """Uji CRUD pelanggan lengkap, auto kode, dan validasi duplikat kode."""
    admin_token = create_token(user_id=1, username="admin_plg", role="admin")
    kasir_token = create_token(user_id=2, username="kasir_plg", role="kasir")
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    kasir_hdr = {"Authorization": f"Bearer {kasir_token}"}

    # 1. Tambah pelanggan baru tanpa kode (otomatis digenerate)
    res_add1 = client.post(
        "/api/pelanggan",
        json={
            "nama": "Budi Santoso",
            "telepon": "081234567890",
            "alamat": "Jl. Merdeka No. 10",
            "email": "budi@example.com",
            "npwp": "01.234.567.8-901.000"
        },
        headers=kasir_hdr
    )
    assert res_add1.status_code == 201
    data1 = res_add1.json()
    assert data1["nama"] == "Budi Santoso"
    assert data1["kode"].startswith("PLG")
    assert data1["aktif"] is True
    plg1_id = data1["id"]

    # 2. Tambah pelanggan dengan custom kode
    res_add2 = client.post(
        "/api/pelanggan",
        json={
            "kode": "VIP-001",
            "nama": "Siti Rahma",
            "telepon": "089876543210",
            "alamat": "Jl. Sudirman 45"
        },
        headers=kasir_hdr
    )
    assert res_add2.status_code == 201
    assert res_add2.json()["kode"] == "VIP-001"

    # 3. Uji validasi nama kosong -> 400
    res_bad = client.post("/api/pelanggan", json={"nama": "  "}, headers=kasir_hdr)
    assert res_bad.status_code == 400

    # 4. Uji duplikat kode -> 409 Conflict
    res_dup = client.post("/api/pelanggan", json={"kode": "VIP-001", "nama": "Siti Kloning"}, headers=kasir_hdr)
    assert res_dup.status_code == 409

    # 5. List pelanggan dengan search query
    res_list = client.get("/api/pelanggan?q=Budi", headers=kasir_hdr)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert any(p["nama"] == "Budi Santoso" for p in items)

    # 6. Update pelanggan
    res_upd = client.put(
        f"/api/pelanggan/{plg1_id}",
        json={"nama": "Budi Santoso, S.Kom", "telepon": "08111222333"},
        headers=kasir_hdr
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["nama"] == "Budi Santoso, S.Kom"
    assert res_upd.json()["telepon"] == "08111222333"

    # 7. Detail pelanggan
    res_get = client.get(f"/api/pelanggan/{plg1_id}", headers=kasir_hdr)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == plg1_id

    # 8. Soft-delete pelanggan: Kasir dilarang (403), Admin diizinkan (200)
    res_del_kasir = client.delete(f"/api/pelanggan/{plg1_id}", headers=kasir_hdr)
    assert res_del_kasir.status_code == 403

    res_del_admin = client.delete(f"/api/pelanggan/{plg1_id}", headers=admin_hdr)
    assert res_del_admin.status_code == 200
    assert "dinonaktifkan" in res_del_admin.json()["message"]

    # 9. List hanya yang aktif -> Budi tidak muncul lagi
    res_active = client.get("/api/pelanggan?aktif_only=true", headers=kasir_hdr)
    assert not any(p["id"] == plg1_id for p in res_active.json())

    # 10. List semua -> Budi tetap ada dengan aktif=False
    res_all = client.get("/api/pelanggan?aktif_only=false", headers=kasir_hdr)
    budi = next((p for p in res_all.json() if p["id"] == plg1_id), None)
    assert budi is not None
    assert budi["aktif"] is False


def test_transaksi_with_pelanggan_integration(client, test_db):
    """Uji transaksi kasir yang mengaitkan pelanggan (customer) dan menyimpan riwayatnya."""
    kasir_token = create_token(user_id=1, username="kasir_trx", role="kasir")
    kasir_hdr = {"Authorization": f"Bearer {kasir_token}"}

    # Buat pelanggan & barang
    with test_db.get_session() as session:
        plg = Pelanggan(kode="PLG-TRX-1", nama="CV Maju Makmur", telepon="081999888777", alamat="Semarang")
        brg = Barang(kode="BRG-PLG-1", nama="Teh Botol Kotak", harga_beli=2500, harga_jual=4000, stok=100, satuan="pcs")
        session.add_all([plg, brg])
        session.commit()
        plg_id = plg.id
        brg_id = brg.id

    # Buat transaksi dengan pelanggan_id
    trx_payload = {
        "items": [
            {"barang_id": brg_id, "nama_barang": "Teh Botol Kotak", "kode_barang": "BRG-PLG-1", "qty": 3, "harga": 4000, "diskon": 0}
        ],
        "bayar": 20000,
        "metode_bayar": "cash",
        "pelanggan_id": plg_id
    }
    res_trx = client.post("/api/transaksi", json=trx_payload, headers=kasir_hdr)
    assert res_trx.status_code == 201
    trx_data = res_trx.json()
    assert trx_data["total"] == 12000
    assert trx_data["kembalian"] == 8000
    assert trx_data["pelanggan_id"] == plg_id
    assert trx_data["nama_pelanggan"] == "CV Maju Makmur"
    assert trx_data["telepon_pelanggan"] == "081999888777"

    # Detail transaksi via GET /api/transaksi/{id}
    res_detail = client.get(f"/api/transaksi/{trx_data['id']}", headers=kasir_hdr)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["nama_pelanggan"] == "CV Maju Makmur"


def test_pengeluaran_crud_and_reporting(client, test_db):
    """Uji pengeluaran: tambah, list per rentang tanggal & kategori, list kategori, dan hapus."""
    admin_token = create_token(user_id=1, username="admin_exp", role="admin")
    kasir_token = create_token(user_id=2, username="kasir_exp", role="kasir")
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    kasir_hdr = {"Authorization": f"Bearer {kasir_token}"}

    # 1. Kategori pengeluaran endpoint
    res_cats = client.get("/api/pengeluaran/kategori", headers=kasir_hdr)
    assert res_cats.status_code == 200
    cats = res_cats.json()
    assert isinstance(cats, list)
    assert "Listrik & Air" in cats
    assert "Operasional" in cats

    # 2. Tambah pengeluaran baru
    today_str = date.today().isoformat()
    res_add = client.post(
        "/api/pengeluaran",
        json={
            "kategori": "Operasional",
            "nominal": 75000,
            "deskripsi": "Beli kertas thermal dan lakban kasir"
        },
        headers=kasir_hdr
    )
    assert res_add.status_code == 201
    exp_data = res_add.json()
    assert exp_data["kategori"] == "Operasional"
    assert exp_data["nominal"] == 75000
    exp_id = exp_data["id"]

    # 3. List pengeluaran dengan filter tanggal & kategori
    res_list = client.get(
        f"/api/pengeluaran?tanggal_mulai={today_str}&tanggal_selesai={today_str}&kategori=Operasional",
        headers=kasir_hdr
    )
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert any(x["id"] == exp_id for x in items)

    # 4. Hapus pengeluaran: kasir dilarang (403), admin berhasil (200)
    res_del_kasir = client.delete(f"/api/pengeluaran/{exp_id}", headers=kasir_hdr)
    assert res_del_kasir.status_code == 403

    res_del_admin = client.delete(f"/api/pengeluaran/{exp_id}", headers=admin_hdr)
    assert res_del_admin.status_code == 200
    assert res_del_admin.json()["success"] is True

    # 5. Verifikasi pengeluaran telah terhapus
    res_after = client.get(f"/api/pengeluaran?tanggal_mulai={today_str}&tanggal_selesai={today_str}", headers=kasir_hdr)
    assert not any(x["id"] == exp_id for x in res_after.json())
