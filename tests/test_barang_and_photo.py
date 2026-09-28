"""
Unit tests untuk fitur penghapusan barang & upload foto produk
"""

import os
import shutil
from pathlib import Path
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QImage, QColor

import config
from database.db import db
from database.models import Barang, Pengaturan


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sample_data_cleared_persistence(test_db):
    """Memastikan flag sample_data_cleared bekerja dan mencegah re-seeding sample barang."""
    with test_db.get_session() as session:
        flag = session.query(Pengaturan).filter_by(kunci="sample_data_cleared").first()
        if not flag:
            session.add(Pengaturan(kunci="sample_data_cleared", nilai="1"))
            session.commit()

    test_db._seed_initial_data()

    with test_db.get_session() as session:
        flag = session.query(Pengaturan).filter_by(kunci="sample_data_cleared").first()
        assert flag is not None
        assert flag.nilai == "1"


def test_barang_crud_with_photo(test_db, tmp_path):
    """Test pembuatan barang, upload foto, dan pembaruan foto produk."""
    # Buat file gambar dummy
    dummy_img_path = tmp_path / "test_product.png"
    img = QImage(100, 100, QImage.Format_RGB32)
    img.fill(QColor("blue"))
    assert img.save(str(dummy_img_path))

    with test_db.get_session() as session:
        # Tambah barang dengan foto
        dest_filename = "test_prod_brg001.png"
        dest_rel = f"uploads/produk/{dest_filename}"
        dest_full = config.BASE_DIR / dest_rel
        shutil.copy2(dummy_img_path, dest_full)

        b = Barang(
            kode="TEST-BRG-001",
            nama="Produk Test Foto",
            kategori="Makanan",
            harga_beli=5000,
            harga_jual=10000,
            stok=20,
            foto=dest_rel
        )
        session.add(b)
        session.commit()
        b_id = b.id

    # Verifikasi tersimpan di DB
    with test_db.get_session() as session:
        b_saved = session.query(Barang).filter_by(id=b_id).first()
        assert b_saved is not None
        assert b_saved.foto == dest_rel
        assert (config.BASE_DIR / b_saved.foto).exists()

        # Update: hapus foto
        b_saved.foto = None
        session.commit()

    with test_db.get_session() as session:
        b_updated = session.query(Barang).filter_by(id=b_id).first()
        assert b_updated.foto is None

        # Bersihkan data test
        session.delete(b_updated)
        session.commit()

    if dest_full.exists():
        dest_full.unlink()


def test_product_card_ui_rendering(qapp):
    """Test ProductCard di kasir POS dapat merender produk dengan atau tanpa foto."""
    from ui.transaksi.kasir_page import ProductCard

    # Buat barang dummy tanpa foto
    b_no_photo = Barang(
        id=9991,
        kode="TEST-UI-1",
        nama="Kopi Test",
        kategori="Minuman",
        harga_jual=15000,
        stok=10,
        foto=None
    )
    card1 = ProductCard(b_no_photo)
    assert card1 is not None

    # Buat barang dummy dengan foto
    dummy_foto = config.UPLOAD_PRODUK_DIR / "dummy_card.png"
    img = QImage(64, 64, QImage.Format_RGB32)
    img.fill(QColor("red"))
    img.save(str(dummy_foto))

    b_with_photo = Barang(
        id=9992,
        kode="TEST-UI-2",
        nama="Kopi Foto",
        kategori="Minuman",
        harga_jual=18000,
        stok=5,
        foto="uploads/produk/dummy_card.png"
    )
    card2 = ProductCard(b_with_photo)
    assert card2 is not None

    if dummy_foto.exists():
        dummy_foto.unlink()


def test_barang_form_dialog_photo_flow(qapp, tmp_path):
    """Test dialog form barang membuka, mengatur foto, dan reset foto."""
    from ui.barang.barang_form import BarangFormDialog

    dummy_img = tmp_path / "test_dialog.jpg"
    img = QImage(80, 80, QImage.Format_RGB32)
    img.fill(QColor("green"))
    img.save(str(dummy_img))

    dialog = BarangFormDialog()
    assert dialog.photo_preview is not None
    assert dialog.btn_choose_photo is not None
    assert dialog.btn_remove_photo is not None

    # Simulasi pilih foto
    dialog._selected_photo_path = str(dummy_img)
    dialog._display_photo(str(dummy_img))
    assert dialog.photo_preview.text() == ""

    # Simulasi hapus foto
    dialog._remove_photo()
    assert dialog._selected_photo_path is None
    assert dialog._photo_removed is True
    assert dialog.photo_preview.text() == "📷"
