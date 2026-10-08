"""Helper untuk mengelola foto menu custom."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

import config


class PhotoManager:
    """Utility copy/delete foto untuk menu display custom."""

    @staticmethod
    def ensure_upload_dir() -> Path:
        config.UPLOAD_MENU_DIR.mkdir(parents=True, exist_ok=True)
        return config.UPLOAD_MENU_DIR

    @staticmethod
    def slugify(value: str) -> str:
        clean = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean[:30] or "menu"

    @staticmethod
    def copy_photo(source_path: str | Path | None, menu_name: str) -> Optional[str]:
        """Salin file foto ke uploads/menu/ dan kembalikan path relatif."""
        if not source_path:
            return None

        src = Path(source_path)
        if not src.exists() or not src.is_file():
            return None

        ext = src.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return None

        try:
            PhotoManager.ensure_upload_dir()
            filename = f"menu_{PhotoManager.slugify(menu_name)}_{uuid.uuid4().hex[:6]}{ext}"
            dest = config.UPLOAD_MENU_DIR / filename
            shutil.copy2(src, dest)
            return f"uploads/menu/{filename}"
        except Exception:
            return None

    @staticmethod
    def delete_photo(rel_path: str | None) -> None:
        """Hapus file foto lama jika path valid."""
        if not rel_path:
            return
        try:
            file_path = Path(config.BASE_DIR) / rel_path
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
        except Exception:
            pass
