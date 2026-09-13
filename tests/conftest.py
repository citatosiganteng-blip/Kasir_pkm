"""
Pytest configuration & fixtures for KasirKu
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Pastikan root workspace ada di sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from database.db import DatabaseManager
from database.models import Base, User, Barang, Pengaturan


@pytest.fixture(scope="session")
def test_db():
    """Fixture database test terisolasi menggunakan SQLite temporary file"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = Path(tmp.name)

    # Override config DB_PATH
    orig_db_path = config.DB_PATH
    config.DB_PATH = test_db_path

    # Inisialisasi DatabaseManager
    db_mgr = DatabaseManager()
    db_mgr._engine = None
    db_mgr._SessionLocal = None
    db_mgr.initialize()

    yield db_mgr

    # Cleanup
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass
    config.DB_PATH = orig_db_path
