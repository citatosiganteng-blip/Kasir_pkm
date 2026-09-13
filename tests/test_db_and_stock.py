"""
Unit tests for Database session lifecycle & Optimistic Stock Management
"""

import pytest
from database.models import Barang, Transaksi, TransaksiDetail


def test_session_commit_on_success(test_db):
    """Pastikan context manager get_session() otomatis melakukan commit saat tidak ada error"""
    with test_db.get_session() as session:
        test_item = Barang(
            kode="TEST001",
            nama="Barang Uji Komitmen",
            harga_jual=10000,
            stok=50
        )
        session.add(test_item)

    # Verifikasi data tersimpan di session baru
    with test_db.get_session() as session:
        saved = session.query(Barang).filter_by(kode="TEST001").first()
        assert saved is not None
        assert saved.nama == "Barang Uji Komitmen"
        assert saved.stok == 50


def test_session_rollback_on_exception(test_db):
    """Pastikan context manager get_session() otomatis rollback saat terjadi exception"""
    with pytest.raises(RuntimeError):
        with test_db.get_session() as session:
            test_item = Barang(
                kode="TEST_ROLLBACK",
                nama="Barang Uji Rollback",
                harga_jual=5000,
                stok=20
            )
            session.add(test_item)
            raise RuntimeError("Simulasi kegagalan di tengah transaksi")

    # Verifikasi data tidak pernah tersimpan
    with test_db.get_session() as session:
        not_saved = session.query(Barang).filter_by(kode="TEST_ROLLBACK").first()
        assert not_saved is None


def test_optimistic_stock_check_success(test_db):
    """Pengurangan stok berhasil saat stok mencukupi"""
    with test_db.get_session() as session:
        b = Barang(kode="STK_OK", nama="Barang Cukup", harga_jual=1000, stok=10)
        session.add(b)

    # Simulasikan transaksi kasir_page: validasi & kurangi stok
    qty_beli = 3
    with test_db.get_session() as session:
        item = session.query(Barang).filter_by(kode="STK_OK").first()
        assert item.stok >= qty_beli
        item.stok -= qty_beli

    # Verifikasi stok berkurang
    with test_db.get_session() as session:
        updated = session.query(Barang).filter_by(kode="STK_OK").first()
        assert updated.stok == 7


def test_optimistic_stock_check_insufficient_rollback(test_db):
    """Transaksi ditolak dan di-rollback jika kuantitas melebihi stok yang tersedia"""
    with test_db.get_session() as session:
        b = Barang(kode="STK_KURANG", nama="Barang Terbatas", harga_jual=2000, stok=2)
        session.add(b)

    qty_beli = 5

    # Simulasikan logika kasir_page: raise ValueError jika stok kurang
    with pytest.raises(ValueError) as excinfo:
        with test_db.get_session() as session:
            item = session.query(Barang).filter_by(kode="STK_KURANG").first()
            if item.stok < qty_beli:
                raise ValueError(f"Stok '{item.nama}' tidak cukup. Tersedia: {item.stok}, diminta: {qty_beli}")
            item.stok -= qty_beli

    assert "tidak cukup" in str(excinfo.value)

    # Verifikasi stok tetap utuh (tidak berkurang / tidak minus)
    with test_db.get_session() as session:
        checked = session.query(Barang).filter_by(kode="STK_KURANG").first()
        assert checked.stok == 2
