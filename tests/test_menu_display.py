from pathlib import Path

from sqlalchemy import create_engine

from database.models import Base, MenuItem
from services.photo_manager import PhotoManager


def test_menu_item_model_and_table_schema():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    cols = {column.name for column in MenuItem.__table__.columns}
    assert {"id", "barang_id", "nama", "harga", "foto", "urutan", "aktif", "created_at"}.issubset(cols)


def test_photo_manager_copies_photo_to_upload_dir(tmp_path):
    source = tmp_path / "food.png"
    source.write_bytes(b"fake-png")

    rel_path = PhotoManager.copy_photo(source, "Nasi Goreng")

    assert rel_path is not None
    assert rel_path.startswith("uploads/menu/")
    saved_path = Path(__file__).resolve().parents[1] / rel_path
    assert saved_path.exists()
    assert saved_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
