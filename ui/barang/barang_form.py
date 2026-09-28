"""
KasirKu Barang Form Dialog
Form tambah/edit barang
"""

import os
import shutil
import uuid
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame, QFormLayout, QMessageBox, QTextEdit, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QCursor, QPixmap

from database.db import db
from database.models import Barang
from utils.helpers import generate_item_code
import config
from ui.widgets import ThemedComboBox, apply_dialog_theme


KATEGORI_LIST = [
    "Makanan", "Minuman", "Sembako", "Kebersihan",
    "Kesehatan", "Elektronik", "Pakaian", "ATK", "Lain-lain"
]

SATUAN_LIST = ["pcs", "kg", "gram", "liter", "ml", "box", "pak", "lusin", "meter", "buah"]


class BarangFormDialog(QDialog):
    """Dialog form tambah/edit barang"""
    saved = pyqtSignal()

    def __init__(self, barang: Barang = None, parent=None):
        super().__init__(parent)
        self.barang = barang  # None = tambah baru, otherwise = edit
        self.setWindowTitle("Tambah Barang" if not barang else "Edit Barang")
        self.setFixedSize(540, 720)
        self.setModal(True)
        self._selected_photo_path = None
        self._photo_removed = False
        self._current_photo_rel = None

        # Dialog ini adalah top-level window. Untuk memastikan tampilannya
        # selalu mengikuti mode aplikasi (terutama setelah user berpindah
        # dari Dark -> Light), terapkan tema secara eksplisit ke dialog.
        self._setup_ui()
        self._apply_theme()

        if barang:
            self._populate_fields()

    def _apply_theme(self):
        """Terapkan warna dialog sesuai tema aplikasi yang sedang aktif."""
        theme = db.get_setting("app_theme", "light")

        if theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #0B2036;
                    color: #F9FAFB;
                }
                QDialog QLabel {
                    color: #F9FAFB;
                }
                QFrame#card {
                    background-color: #112D4E;
                    border: 1px solid #274568;
                    border-radius: 12px;
                }
                QLineEdit {
                    background-color: #112D4E;
                    color: #F9FAFB;
                    border: 1.5px solid #274568;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QLineEdit:focus {
                    background-color: #17324F;
                    border-color: #2572AF;
                }
                QLineEdit::placeholder {
                    color: #8CA0BC;
                }
                QComboBox {
                    background-color: #112D4E;
                    color: #F9FAFB;
                    border: 1.5px solid #274568;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QComboBox:focus {
                    border-color: #2572AF;
                }
                QComboBox QAbstractItemView {
                    background-color: #112D4E;
                    color: #F9FAFB;
                    border: 1px solid #274568;
                    selection-background-color: #2572AF;
                    selection-color: #FFFFFF;
                }
                QComboBox QLineEdit {
                    background: transparent;
                    border: none;
                    color: #F9FAFB;
                    padding: 0;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #112D4E;
                    color: #F9FAFB;
                    border: 1.5px solid #274568;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QSpinBox::up-button, QSpinBox::down-button,
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                    background: #17324F;
                    border: none;
                    width: 20px;
                }
                QPushButton#btn_secondary {
                    background-color: #112D4E;
                    color: #F9FAFB;
                    border: 1.5px solid #274568;
                    border-radius: 8px;
                }
                QPushButton#btn_secondary:hover {
                    background-color: #17324F;
                }
                QPushButton#btn_danger_subtle {
                    background-color: #3F1D1D;
                    color: #FCA5A5;
                    border: 1px solid #7F1D1D;
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton#btn_danger_subtle:hover {
                    background-color: #551D1D;
                    color: #FECACA;
                }
                QPushButton {
                    background-color: #2572AF;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #1D5F95;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #F9FAFB;
                    color: #112D4E;
                }
                QDialog QLabel {
                    color: #112D4E;
                }
                QFrame#card {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                }
                QLineEdit {
                    background-color: #FFFFFF;
                    color: #112D4E;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QLineEdit:focus {
                    background-color: #FFFFFF;
                    border-color: #3F72AF;
                }
                QLineEdit::placeholder {
                    color: #7C8CA6;
                }
                QComboBox {
                    background-color: #FFFFFF;
                    color: #112D4E;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QComboBox:focus {
                    border-color: #3F72AF;
                }
                QComboBox QAbstractItemView {
                    background-color: #FFFFFF;
                    color: #112D4E;
                    border: 1px solid #E5E7EB;
                    selection-background-color: #DBE2EF;
                    selection-color: #3F72AF;
                }
                QComboBox QLineEdit {
                    background: transparent;
                    border: none;
                    color: #112D4E;
                    padding: 0;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #FFFFFF;
                    color: #112D4E;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QSpinBox::up-button, QSpinBox::down-button,
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                    background: #F9FAFB;
                    border: none;
                    width: 20px;
                }
                QPushButton#btn_secondary {
                    background-color: #FFFFFF;
                    color: #3E4C63;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 8px;
                }
                QPushButton#btn_secondary:hover {
                    background-color: #F9FAFB;
                    color: #112D4E;
                }
                QPushButton#btn_danger_subtle {
                    background-color: #FEE2E2;
                    color: #DC2626;
                    border: 1px solid #FECACA;
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton#btn_danger_subtle:hover {
                    background-color: #FCA5A5;
                    color: #991B1B;
                }
                QPushButton {
                    background-color: #3F72AF;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #2F5A8C;
                }
            """)
        if hasattr(self, "photo_preview") and not self._selected_photo_path and not getattr(self, "_current_photo_rel", None):
            self._reset_photo_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Header
        header_lbl = QLabel("📦 " + ("Edit Barang" if self.barang else "Tambah Barang Baru"))
        header_lbl.setStyleSheet("font-size: 18px; font-weight: 800; margin-bottom: 4px; background: transparent;")
        layout.addWidget(header_lbl)

        sub_lbl = QLabel("Isi semua informasi barang dengan benar")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B; margin-bottom: 20px; background: transparent;")
        layout.addWidget(sub_lbl)
        layout.addSpacing(20)

        # Form
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_frame.setProperty("theme_form", True)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignRight)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
            return lbl

        def make_input(placeholder=""):
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(38)
            return inp

        # Foto Produk
        photo_row = QHBoxLayout()
        photo_row.setSpacing(14)

        self.photo_preview = QLabel("📷")
        self.photo_preview.setFixedSize(68, 68)
        self.photo_preview.setAlignment(Qt.AlignCenter)
        self.photo_preview.setCursor(QCursor(Qt.PointingHandCursor))
        self.photo_preview.setToolTip("Klik untuk memilih foto produk")
        self.photo_preview.mousePressEvent = lambda _: self._choose_photo()
        photo_row.addWidget(self.photo_preview)

        photo_btn_layout = QVBoxLayout()
        photo_btn_layout.setSpacing(6)

        btn_action_row = QHBoxLayout()
        btn_action_row.setSpacing(8)

        self.btn_choose_photo = QPushButton("📁 Pilih Foto")
        self.btn_choose_photo.setObjectName("btn_secondary")
        self.btn_choose_photo.setFixedHeight(32)
        self.btn_choose_photo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_choose_photo.clicked.connect(self._choose_photo)
        btn_action_row.addWidget(self.btn_choose_photo)

        self.btn_remove_photo = QPushButton("🗑 Hapus")
        self.btn_remove_photo.setObjectName("btn_danger_subtle")
        self.btn_remove_photo.setFixedHeight(32)
        self.btn_remove_photo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_remove_photo.clicked.connect(self._remove_photo)
        self.btn_remove_photo.hide()
        btn_action_row.addWidget(self.btn_remove_photo)
        btn_action_row.addStretch()

        photo_btn_layout.addLayout(btn_action_row)

        photo_hint = QLabel("Format: JPG, PNG, WEBP (Opsional)")
        photo_hint.setStyleSheet("font-size: 11px; color: #64748B; background: transparent;")
        photo_btn_layout.addWidget(photo_hint)

        photo_row.addLayout(photo_btn_layout)
        form_layout.addRow(make_label("Foto Produk"), photo_row)

        # Kode Barang
        self.kode_input = make_input("Auto-generate jika kosong")
        form_layout.addRow(make_label("Kode Barang"), self.kode_input)

        # Barcode
        self.barcode_input = make_input("Scan atau ketik barcode")
        form_layout.addRow(make_label("Barcode"), self.barcode_input)

        # Nama
        self.nama_input = make_input("Nama barang")
        form_layout.addRow(make_label("Nama Barang *"), self.nama_input)

        # Kategori
        self.kategori_combo = ThemedComboBox()
        self.kategori_combo.addItems(KATEGORI_LIST)
        self.kategori_combo.setEditable(True)
        self.kategori_combo.setFixedHeight(38)
        form_layout.addRow(make_label("Kategori"), self.kategori_combo)

        # Satuan
        self.satuan_combo = ThemedComboBox()
        self.satuan_combo.addItems(SATUAN_LIST)
        self.satuan_combo.setEditable(True)
        self.satuan_combo.setFixedHeight(38)
        form_layout.addRow(make_label("Satuan"), self.satuan_combo)

        # Harga Beli
        self.harga_beli_input = QDoubleSpinBox()
        self.harga_beli_input.setPrefix("Rp ")
        self.harga_beli_input.setMaximum(999_999_999)
        self.harga_beli_input.setSingleStep(1000)
        self.harga_beli_input.setGroupSeparatorShown(True)
        self.harga_beli_input.setFixedHeight(38)
        form_layout.addRow(make_label("Harga Beli"), self.harga_beli_input)

        # Harga Jual
        self.harga_jual_input = QDoubleSpinBox()
        self.harga_jual_input.setPrefix("Rp ")
        self.harga_jual_input.setMaximum(999_999_999)
        self.harga_jual_input.setSingleStep(1000)
        self.harga_jual_input.setGroupSeparatorShown(True)
        self.harga_jual_input.setFixedHeight(38)
        form_layout.addRow(make_label("Harga Jual *"), self.harga_jual_input)

        # Stok
        stok_row = QHBoxLayout()
        self.stok_input = QSpinBox()
        self.stok_input.setMaximum(999_999)
        self.stok_input.setFixedHeight(38)
        stok_row.addWidget(self.stok_input)

        stok_min_lbl = QLabel("Min:")
        stok_min_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        stok_row.addWidget(stok_min_lbl)

        self.stok_min_input = QSpinBox()
        self.stok_min_input.setMaximum(9999)
        self.stok_min_input.setValue(config.DEFAULT_MIN_STOCK)
        self.stok_min_input.setFixedHeight(38)
        self.stok_min_input.setFixedWidth(80)
        stok_row.addWidget(self.stok_min_input)

        form_layout.addRow(make_label("Stok"), stok_row)
        layout.addWidget(form_frame)

        # Error
        layout.addSpacing(12)
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("""
            color: #EF4444;
            font-size: 12px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 8px 12px;
        """)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Simpan Barang")
        btn_save.setFixedHeight(44)
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _choose_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Foto Produk",
            "",
            "Gambar (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            self._selected_photo_path = file_path
            self._photo_removed = False
            self._display_photo(file_path)
            self.btn_remove_photo.show()

    def _remove_photo(self):
        self._selected_photo_path = None
        self._photo_removed = True
        self._current_photo_rel = None
        self._reset_photo_preview()
        self.btn_remove_photo.hide()

    def _display_photo(self, path_str: str):
        pixmap = QPixmap(path_str)
        if not pixmap.isNull():
            scaled = pixmap.scaled(68, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.photo_preview.setPixmap(scaled)
            self.photo_preview.setText("")
            self.photo_preview.setStyleSheet("""
                QLabel {
                    border: 1.5px solid #3F72AF;
                    border-radius: 10px;
                    background-color: transparent;
                }
            """)
        else:
            self._reset_photo_preview()

    def _reset_photo_preview(self):
        self.photo_preview.setPixmap(QPixmap())
        self.photo_preview.setText("📷")
        theme = db.get_setting("app_theme", "light")
        if theme == "dark":
            self.photo_preview.setStyleSheet("""
                QLabel {
                    background-color: #17324F;
                    border: 1.5px dashed #274568;
                    border-radius: 10px;
                    color: #8CA0BC;
                    font-size: 24px;
                }
            """)
        else:
            self.photo_preview.setStyleSheet("""
                QLabel {
                    background-color: #F8FAFC;
                    border: 1.5px dashed #CBD5E1;
                    border-radius: 10px;
                    color: #94A3B8;
                    font-size: 24px;
                }
            """)

    def _populate_fields(self):
        """Isi form dengan data barang yang diedit"""
        b = self.barang
        self.kode_input.setText(b.kode or "")
        self.barcode_input.setText(b.barcode or "")
        self.nama_input.setText(b.nama or "")

        # Tampilkan foto produk jika ada
        if getattr(b, "foto", None):
            self._current_photo_rel = b.foto
            full_path = (config.BASE_DIR / b.foto) if not os.path.isabs(b.foto) else Path(b.foto)
            if full_path.exists():
                self._display_photo(str(full_path))
                self.btn_remove_photo.show()

        idx = self.kategori_combo.findText(b.kategori or "")
        if idx >= 0:
            self.kategori_combo.setCurrentIndex(idx)
        elif b.kategori:
            self.kategori_combo.setCurrentText(b.kategori)

        idx_s = self.satuan_combo.findText(b.satuan or "pcs")
        if idx_s >= 0:
            self.satuan_combo.setCurrentIndex(idx_s)
        elif b.satuan:
            self.satuan_combo.setCurrentText(b.satuan)

        self.harga_beli_input.setValue(b.harga_beli or 0)
        self.harga_jual_input.setValue(b.harga_jual or 0)
        self.stok_input.setValue(b.stok or 0)
        self.stok_min_input.setValue(b.stok_min or config.DEFAULT_MIN_STOCK)

    def _save(self):
        nama = self.nama_input.text().strip()
        harga_jual = self.harga_jual_input.value()

        if not nama:
            self._show_error("Nama barang harus diisi!")
            return
        if harga_jual <= 0:
            self._show_error("Harga jual harus lebih dari 0!")
            return

        kode = self.kode_input.text().strip()
        barcode = self.barcode_input.text().strip() or None
        kategori = self.kategori_combo.currentText().strip()
        satuan = self.satuan_combo.currentText().strip()
        harga_beli = self.harga_beli_input.value()
        stok = self.stok_input.value()
        stok_min = self.stok_min_input.value()

        with db.get_session() as session:
            # Auto-generate kode if empty
            if not kode:
                kode = generate_item_code(session)

            # Cek duplikat kode
            existing = session.query(Barang).filter(
                Barang.kode == kode
            )
            if self.barang:
                existing = existing.filter(Barang.id != self.barang.id)
            if existing.first():
                self._show_error(f"Kode barang '{kode}' sudah digunakan!")
                return

            # Cek duplikat barcode
            if barcode:
                dup_barcode = session.query(Barang).filter(Barang.barcode == barcode)
                if self.barang:
                    dup_barcode = dup_barcode.filter(Barang.id != self.barang.id)
                if dup_barcode.first():
                    self._show_error(f"Barcode '{barcode}' sudah digunakan!")
                    return

            # Proses foto produk
            new_foto = getattr(self.barang, 'foto', None) if self.barang else None
            if self._photo_removed:
                new_foto = None
            elif self._selected_photo_path:
                ext = Path(self._selected_photo_path).suffix.lower() or ".jpg"
                clean_name = f"brg_{kode.lower()}_{uuid.uuid4().hex[:6]}{ext}"
                target_path = config.UPLOAD_PRODUK_DIR / clean_name
                try:
                    shutil.copy2(self._selected_photo_path, target_path)
                    new_foto = f"uploads/produk/{clean_name}"
                except Exception as e:
                    print(f"[BarangForm] Gagal menyimpan file foto: {e}")

            if self.barang:
                # Edit
                b = session.query(Barang).filter_by(id=self.barang.id).first()
                if b:
                    b.kode = kode
                    b.barcode = barcode
                    b.nama = nama
                    b.kategori = kategori
                    b.satuan = satuan
                    b.harga_beli = harga_beli
                    b.harga_jual = harga_jual
                    b.stok = stok
                    b.stok_min = stok_min
                    b.foto = new_foto
            else:
                # Tambah baru
                b = Barang(
                    kode=kode, barcode=barcode, nama=nama,
                    kategori=kategori, satuan=satuan,
                    harga_beli=harga_beli, harga_jual=harga_jual,
                    stok=stok, stok_min=stok_min,
                    foto=new_foto
                )
                session.add(b)

            session.commit()

        self.saved.emit()
        self.accept()

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()
