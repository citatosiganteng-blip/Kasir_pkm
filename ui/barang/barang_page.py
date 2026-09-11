"""
KasirKu Barang Page
Halaman manajemen barang/produk
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from database.db import db
from database.models import Barang
from utils.helpers import format_rupiah
from auth.auth_manager import auth
from .barang_form import BarangFormDialog
import csv
import os
from datetime import datetime


class BarangPage(QWidget):
    """Halaman manajemen barang"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._barang_data = []
        self._setup_ui()
        self._load_data()

        # Search delay timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._filter_table)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel("📦 Manajemen Barang")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #F1F5F9;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        if auth.is_admin:
            btn_add = QPushButton("+ Tambah Barang")
            btn_add.setFixedHeight(40)
            btn_add.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6C63FF, stop:1 #8B84FF);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0 20px;
                    font-size: 13px;
                    font-weight: 700;
                }
                QPushButton:hover { background: #8B84FF; }
            """)
            btn_add.clicked.connect(self._open_add_form)
            header_layout.addWidget(btn_add)

            btn_export = QPushButton("📤 Export CSV")
            btn_export.setFixedHeight(40)
            btn_export.setStyleSheet("""
                QPushButton {
                    background: #21263A;
                    color: #94A3B8;
                    border: 1px solid #2D3250;
                    border-radius: 8px;
                    padding: 0 16px;
                    font-size: 13px;
                }
                QPushButton:hover { background: #2A2F45; color: #F1F5F9; }
            """)
            btn_export.clicked.connect(self._export_csv)
            header_layout.addWidget(btn_export)

        layout.addLayout(header_layout)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background: #1A1D27;
                border: 1px solid #2D3250;
                border-radius: 10px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Cari nama, kode, atau barcode...")
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #21263A;
                border: 1px solid #2D3250;
                border-radius: 8px;
                padding: 0 12px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #6C63FF; }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_input, 3)

        # Kategori filter
        self.kategori_filter = QComboBox()
        self.kategori_filter.addItem("Semua Kategori")
        self.kategori_filter.setFixedHeight(38)
        self.kategori_filter.setFixedWidth(180)
        self.kategori_filter.setStyleSheet("""
            QComboBox {
                background: #21263A;
                border: 1px solid #2D3250;
                border-radius: 8px;
                padding: 0 12px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QComboBox:focus { border-color: #6C63FF; }
            QComboBox QAbstractItemView {
                background: #21263A;
                border: 1px solid #2D3250;
                selection-background-color: #6C63FF;
            }
        """)
        self.kategori_filter.currentTextChanged.connect(self._filter_table)
        filter_layout.addWidget(self.kategori_filter)

        # Stok filter
        self.stok_filter = QComboBox()
        self.stok_filter.addItems(["Semua Stok", "Stok Rendah", "Habis"])
        self.stok_filter.setFixedHeight(38)
        self.stok_filter.setFixedWidth(140)
        self.stok_filter.setStyleSheet(self.kategori_filter.styleSheet())
        self.stok_filter.currentTextChanged.connect(self._filter_table)
        filter_layout.addWidget(self.stok_filter)

        layout.addWidget(filter_frame)

        # Stats row
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(self.stats_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Kode", "Barcode", "Nama Barang", "Kategori",
            "Harga Beli", "Harga Jual", "Stok", "Satuan", "Aksi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1A1D27;
                border: 1px solid #2D3250;
                border-radius: 10px;
                gridline-color: #2D3250;
                alternate-background-color: #1E2235;
            }
            QTableWidget::item {
                padding: 10px 12px;
                color: #F1F5F9;
            }
            QTableWidget::item:selected {
                background: #2A2F45;
            }
            QHeaderView::section {
                background: #21263A;
                color: #94A3B8;
                padding: 10px 12px;
                font-size: 11px;
                font-weight: 600;
                border: none;
                border-bottom: 2px solid #2D3250;
            }
        """)
        layout.addWidget(self.table)

    def _load_data(self):
        """Load semua barang dari database"""
        with db.get_session() as session:
            barang_list = session.query(Barang).filter(
                Barang.aktif == True
            ).order_by(Barang.nama).all()

            self._barang_data = [
                {
                    "id": b.id,
                    "kode": b.kode,
                    "barcode": b.barcode or "",
                    "nama": b.nama,
                    "kategori": b.kategori or "",
                    "harga_beli": b.harga_beli,
                    "harga_jual": b.harga_jual,
                    "stok": b.stok,
                    "stok_min": b.stok_min,
                    "satuan": b.satuan,
                    "is_low_stock": b.stok <= b.stok_min,
                }
                for b in barang_list
            ]

            # Update kategori filter
            kategori_set = set(b["kategori"] for b in self._barang_data if b["kategori"])
            current_kat = self.kategori_filter.currentText()
            self.kategori_filter.blockSignals(True)
            self.kategori_filter.clear()
            self.kategori_filter.addItem("Semua Kategori")
            for kat in sorted(kategori_set):
                self.kategori_filter.addItem(kat)
            idx = self.kategori_filter.findText(current_kat)
            if idx >= 0:
                self.kategori_filter.setCurrentIndex(idx)
            self.kategori_filter.blockSignals(False)

        self._filter_table()

    def _on_search_changed(self):
        self._search_timer.start(300)

    def _filter_table(self):
        """Filter tabel berdasarkan search dan filter"""
        query = self.search_input.text().strip().lower()
        kat_filter = self.kategori_filter.currentText()
        stok_filter = self.stok_filter.currentText()

        filtered = self._barang_data
        if query:
            filtered = [b for b in filtered if (
                query in b["nama"].lower() or
                query in b["kode"].lower() or
                query in b["barcode"].lower()
            )]
        if kat_filter != "Semua Kategori":
            filtered = [b for b in filtered if b["kategori"] == kat_filter]
        if stok_filter == "Stok Rendah":
            filtered = [b for b in filtered if b["is_low_stock"] and b["stok"] > 0]
        elif stok_filter == "Habis":
            filtered = [b for b in filtered if b["stok"] == 0]

        self._render_table(filtered)
        total = len(self._barang_data)
        self.stats_lbl.setText(f"Menampilkan {len(filtered)} dari {total} barang")

    def _render_table(self, data: list):
        """Render data ke tabel"""
        self.table.setRowCount(len(data))
        self.table.setColumnWidth(8, 120)

        for row, b in enumerate(data):
            self.table.setRowHeight(row, 46)

            items = [
                (b["kode"], "#94A3B8"),
                (b["barcode"], "#64748B"),
                (b["nama"], "#F1F5F9"),
                (b["kategori"], "#94A3B8"),
                (format_rupiah(b["harga_beli"]), "#94A3B8"),
                (format_rupiah(b["harga_jual"]), "#10B981"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                item.setData(Qt.UserRole, b["id"])
                self.table.setItem(row, col, item)

            # Stok dengan badge
            stok_text = str(b["stok"])
            stok_item = QTableWidgetItem(stok_text)
            if b["stok"] == 0:
                stok_item.setForeground(QColor("#EF4444"))
                stok_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            elif b["is_low_stock"]:
                stok_item.setForeground(QColor("#F59E0B"))
                stok_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            else:
                stok_item.setForeground(QColor("#10B981"))
            stok_item.setData(Qt.UserRole, b["id"])
            self.table.setItem(row, 6, stok_item)

            # Satuan
            satuan_item = QTableWidgetItem(b["satuan"])
            satuan_item.setForeground(QColor("#64748B"))
            satuan_item.setData(Qt.UserRole, b["id"])
            self.table.setItem(row, 7, satuan_item)

            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(4)

            if auth.is_admin:
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(30, 30)
                btn_edit.setToolTip("Edit")
                btn_edit.setStyleSheet("""
                    QPushButton {
                        background: #21263A;
                        border: 1px solid #2D3250;
                        border-radius: 6px;
                        font-size: 13px;
                    }
                    QPushButton:hover { background: #6C63FF; border-color: #6C63FF; }
                """)
                btn_edit.clicked.connect(lambda _, bid=b["id"]: self._open_edit_form(bid))
                action_layout.addWidget(btn_edit)

                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(30, 30)
                btn_del.setToolTip("Hapus")
                btn_del.setStyleSheet("""
                    QPushButton {
                        background: #21263A;
                        border: 1px solid #2D3250;
                        border-radius: 6px;
                        font-size: 13px;
                    }
                    QPushButton:hover { background: #EF4444; border-color: #EF4444; }
                """)
                btn_del.clicked.connect(lambda _, bid=b["id"]: self._delete_barang(bid))
                action_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 8, action_widget)

    def _open_add_form(self):
        dialog = BarangFormDialog(parent=self)
        dialog.saved.connect(self._load_data)
        dialog.exec_()

    def _open_edit_form(self, barang_id: int):
        with db.get_session() as session:
            b = session.query(Barang).filter_by(id=barang_id).first()
            if not b:
                return
            session.expunge(b)
        dialog = BarangFormDialog(barang=b, parent=self)
        dialog.saved.connect(self._load_data)
        dialog.exec_()

    def _delete_barang(self, barang_id: int):
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            "Yakin ingin menghapus barang ini?\nBarang akan dinonaktifkan dari sistem.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with db.get_session() as session:
                b = session.query(Barang).filter_by(id=barang_id).first()
                if b:
                    b.aktif = False
                    session.commit()
            self._load_data()

    def _export_csv(self):
        """Export barang ke CSV"""
        try:
            filename = f"barang_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(os.path.expanduser("~"), "Downloads", filename)
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Kode", "Barcode", "Nama", "Kategori",
                                  "Harga Beli", "Harga Jual", "Stok", "Satuan"])
                for b in self._barang_data:
                    writer.writerow([
                        b["kode"], b["barcode"], b["nama"], b["kategori"],
                        b["harga_beli"], b["harga_jual"], b["stok"], b["satuan"]
                    ])
            QMessageBox.information(self, "Export Berhasil",
                                    f"Data barang berhasil diekspor ke:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal export: {str(e)}")

    def refresh(self):
        self._load_data()
