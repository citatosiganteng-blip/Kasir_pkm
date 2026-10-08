"""Dialog tambah/edit item menu custom."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QFormLayout,
    QFileDialog, QMessageBox
)

import config
from auth.auth_manager import auth
from database.db import db
from database.models import MenuItem
from services.photo_manager import PhotoManager


class MenuFormDialog(QDialog):
    """Form untuk menambah atau mengedit item menu."""

    saved = pyqtSignal()

    def __init__(self, menu_item: MenuItem | None = None, parent=None):
        super().__init__(parent)
        self.menu_item = menu_item
        self._selected_photo_path = None
        self._photo_removed = False
        self._setup_ui()
        self._apply_theme()
        if menu_item:
            self._populate_fields()

    def _setup_ui(self):
        self.setWindowTitle("Tambah Menu" if not self.menu_item else "Edit Menu")
        self.setModal(True)
        self.resize(520, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        photo_row = QHBoxLayout()
        self.photo_preview = QLabel("📷")
        self.photo_preview.setFixedSize(68, 68)
        self.photo_preview.setAlignment(Qt.AlignCenter)
        self.photo_preview.setStyleSheet("background: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 10px; font-size: 24px;")
        photo_row.addWidget(self.photo_preview)

        photo_actions = QVBoxLayout()
        self.btn_select_photo = QPushButton("📁 Pilih Foto")
        self.btn_remove_photo = QPushButton("🗑 Hapus Foto")
        self.btn_select_photo.clicked.connect(self._choose_photo)
        self.btn_remove_photo.clicked.connect(self._remove_photo)
        photo_actions.addWidget(self.btn_select_photo)
        photo_actions.addWidget(self.btn_remove_photo)
        photo_row.addLayout(photo_actions)
        layout.addLayout(photo_row)

        form = QFormLayout()
        self.nama_input = QLineEdit()
        self.harga_input = QDoubleSpinBox()
        self.harga_input.setRange(0.01, 999999999)
        self.harga_input.setDecimals(2)
        self.harga_input.setPrefix("Rp ")
        self.urutan_input = QSpinBox()
        self.urutan_input.setRange(0, 9999)

        form.addRow("Nama Menu", self.nama_input)
        form.addRow("Harga", self.harga_input)
        form.addRow("Urutan Tampilan", self.urutan_input)
        layout.addLayout(form)

        self.error_lbl = QLabel()
        self.error_lbl.setStyleSheet("color: #DC2626; font-size: 11px;")
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        button_row = QHBoxLayout()
        self.btn_save = QPushButton("Simpan")
        self.btn_cancel = QPushButton("Batal")
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_save)
        layout.addLayout(button_row)

    def _apply_theme(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_dark:
            self.setStyleSheet("QDialog { background: #0B2036; color: #F9FAFB; } QLabel { color: #F9FAFB; } QLineEdit, QDoubleSpinBox, QSpinBox { background: #112D4E; color: #F9FAFB; border: 1px solid #274568; border-radius: 8px; padding: 8px; } QPushButton { background: #2572AF; color: white; border-radius: 8px; padding: 8px 12px; } QPushButton#btn_secondary { background: #112D4E; border: 1px solid #274568; }")
        else:
            self.setStyleSheet("QDialog { background: #F9FAFB; color: #112D4E; } QLabel { color: #112D4E; } QLineEdit, QDoubleSpinBox, QSpinBox { background: white; color: #112D4E; border: 1px solid #E5E7EB; border-radius: 8px; padding: 8px; } QPushButton { background: #3F72AF; color: white; border-radius: 8px; padding: 8px 12px; } QPushButton#btn_secondary { background: white; border: 1px solid #E5E7EB; }")

    def _populate_fields(self):
        self.nama_input.setText((self.menu_item.nama or ""))
        self.harga_input.setValue(float(self.menu_item.harga or 0))
        self.urutan_input.setValue(int(self.menu_item.urutan or 0))
        if self.menu_item.foto:
            rel = self.menu_item.foto
            abs_path = config.BASE_DIR / rel if not Path(rel).is_absolute() else Path(rel)
            if abs_path.exists():
                self._display_photo(abs_path)

    def _choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Foto Menu", str(config.BASE_DIR),
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self._selected_photo_path = path
            self._photo_removed = False
            self._display_photo(path)

    def _remove_photo(self):
        self._selected_photo_path = None
        self._photo_removed = True
        self.photo_preview.setText("📷")
        self.photo_preview.setStyleSheet("background: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 10px; font-size: 24px;")

    def _display_photo(self, path):
        pixmap = QPixmap(str(path)).scaled(68, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if pixmap.isNull():
            self.photo_preview.setText("📷")
            return
        self.photo_preview.setPixmap(pixmap)
        self.photo_preview.setStyleSheet("background: transparent; border: 1px solid #D1D5DB; border-radius: 10px;")

    def _show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _save(self):
        nama = (self.nama_input.text() or "").strip()
        harga = self.harga_input.value()
        if not nama:
            self._show_error("Nama menu tidak boleh kosong.")
            return
        if harga <= 0:
            self._show_error("Harga menu harus lebih dari 0.")
            return

        with db.get_session() as session:
            if self.menu_item is None:
                item = MenuItem(nama=nama, harga=float(harga), urutan=int(self.urutan_input.value()), aktif=True)
                session.add(item)
                session.flush()
            else:
                item = session.query(MenuItem).filter_by(id=self.menu_item.id).first()
                if item is None:
                    item = MenuItem(nama=nama, harga=float(harga), urutan=int(self.urutan_input.value()), aktif=True)
                    session.add(item)
                    session.flush()
                item.nama = nama
                item.harga = float(harga)
                item.urutan = int(self.urutan_input.value())

            if self._selected_photo_path:
                relative = PhotoManager.copy_photo(self._selected_photo_path, nama)
                if relative:
                    item.foto = relative
            elif self._photo_removed:
                if item.foto:
                    PhotoManager.delete_photo(item.foto)
                item.foto = None
            elif self.menu_item and self.menu_item.foto and not item.foto:
                item.foto = self.menu_item.foto

            session.add(item)

        self.saved.emit()
        self.accept()
