"""
KasirKu Barang Form Dialog
Form tambah/edit barang
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame, QFormLayout, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator

from database.db import db
from database.models import Barang
from utils.helpers import generate_item_code
import config


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
        self.setFixedSize(520, 640)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1A1D27;
                border-radius: 12px;
            }}
        """)
        self._setup_ui()
        if barang:
            self._populate_fields()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Header
        header_lbl = QLabel("📦 " + ("Edit Barang" if self.barang else "Tambah Barang Baru"))
        header_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #F1F5F9; margin-bottom: 4px;")
        layout.addWidget(header_lbl)

        sub_lbl = QLabel("Isi semua informasi barang dengan benar")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B; margin-bottom: 20px;")
        layout.addWidget(sub_lbl)
        layout.addSpacing(20)

        # Form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background: #21263A;
                border-radius: 10px;
                border: 1px solid #2D3250;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignRight)

        label_style = "color: #94A3B8; font-size: 12px; font-weight: 600;"

        def make_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            return lbl

        def make_input(placeholder=""):
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(38)
            inp.setStyleSheet("""
                QLineEdit {
                    background: #2D3250;
                    border: 1px solid #3D4466;
                    border-radius: 8px;
                    padding: 0 10px;
                    color: #F1F5F9;
                    font-size: 13px;
                }
                QLineEdit:focus { border-color: #6C63FF; }
            """)
            return inp

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
        self.kategori_combo = QComboBox()
        self.kategori_combo.addItems(KATEGORI_LIST)
        self.kategori_combo.setEditable(True)
        self.kategori_combo.setFixedHeight(38)
        self.kategori_combo.setStyleSheet("""
            QComboBox {
                background: #2D3250;
                border: 1px solid #3D4466;
                border-radius: 8px;
                padding: 0 10px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QComboBox:focus { border-color: #6C63FF; }
            QComboBox QAbstractItemView {
                background: #2D3250;
                border: 1px solid #3D4466;
                selection-background-color: #6C63FF;
            }
        """)
        form_layout.addRow(make_label("Kategori"), self.kategori_combo)

        # Satuan
        self.satuan_combo = QComboBox()
        self.satuan_combo.addItems(SATUAN_LIST)
        self.satuan_combo.setEditable(True)
        self.satuan_combo.setFixedHeight(38)
        self.satuan_combo.setStyleSheet(self.kategori_combo.styleSheet())
        form_layout.addRow(make_label("Satuan"), self.satuan_combo)

        # Harga Beli
        self.harga_beli_input = QDoubleSpinBox()
        self.harga_beli_input.setPrefix("Rp ")
        self.harga_beli_input.setMaximum(999_999_999)
        self.harga_beli_input.setSingleStep(1000)
        self.harga_beli_input.setGroupSeparatorShown(True)
        self.harga_beli_input.setFixedHeight(38)
        self.harga_beli_input.setStyleSheet("""
            QDoubleSpinBox {
                background: #2D3250;
                border: 1px solid #3D4466;
                border-radius: 8px;
                padding: 0 10px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QDoubleSpinBox:focus { border-color: #6C63FF; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background: #3D4466;
                border: none;
                border-radius: 4px;
                width: 20px;
            }
        """)
        form_layout.addRow(make_label("Harga Beli"), self.harga_beli_input)

        # Harga Jual
        self.harga_jual_input = QDoubleSpinBox()
        self.harga_jual_input.setPrefix("Rp ")
        self.harga_jual_input.setMaximum(999_999_999)
        self.harga_jual_input.setSingleStep(1000)
        self.harga_jual_input.setGroupSeparatorShown(True)
        self.harga_jual_input.setFixedHeight(38)
        self.harga_jual_input.setStyleSheet(self.harga_beli_input.styleSheet())
        form_layout.addRow(make_label("Harga Jual *"), self.harga_jual_input)

        # Stok
        stok_row = QHBoxLayout()
        self.stok_input = QSpinBox()
        self.stok_input.setMaximum(999_999)
        self.stok_input.setFixedHeight(38)
        self.stok_input.setStyleSheet("""
            QSpinBox {
                background: #2D3250;
                border: 1px solid #3D4466;
                border-radius: 8px;
                padding: 0 10px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QSpinBox:focus { border-color: #6C63FF; }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #3D4466; border: none; border-radius: 4px; width: 20px;
            }
        """)
        stok_row.addWidget(self.stok_input)

        stok_min_lbl = QLabel("Min:")
        stok_min_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        stok_row.addWidget(stok_min_lbl)

        self.stok_min_input = QSpinBox()
        self.stok_min_input.setMaximum(9999)
        self.stok_min_input.setValue(config.DEFAULT_MIN_STOCK)
        self.stok_min_input.setFixedHeight(38)
        self.stok_min_input.setFixedWidth(80)
        self.stok_min_input.setStyleSheet(self.stok_input.styleSheet())
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
        btn_cancel.setFixedHeight(44)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #21263A;
                color: #94A3B8;
                border: 1px solid #2D3250;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background: #2A2F45; color: #F1F5F9; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Simpan Barang")
        btn_save.setFixedHeight(44)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C63FF, stop:1 #8B84FF);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: #8B84FF; }
            QPushButton:pressed { background: #4A44CC; }
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _populate_fields(self):
        """Isi form dengan data barang yang diedit"""
        b = self.barang
        self.kode_input.setText(b.kode or "")
        self.barcode_input.setText(b.barcode or "")
        self.nama_input.setText(b.nama or "")

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
            else:
                # Tambah baru
                b = Barang(
                    kode=kode, barcode=barcode, nama=nama,
                    kategori=kategori, satuan=satuan,
                    harga_beli=harga_beli, harga_jual=harga_jual,
                    stok=stok, stok_min=stok_min
                )
                session.add(b)

            session.commit()

        self.saved.emit()
        self.accept()

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()
