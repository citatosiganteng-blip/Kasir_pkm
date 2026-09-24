"""
KasirKu Barang Page
Halaman manajemen barang/produk — redesigned with stat cards, modern table, pagination
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QAbstractItemView, QSizePolicy,
    QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QCursor

from database.db import db
from database.models import Barang
from utils.helpers import format_rupiah
from auth.auth_manager import auth
from .barang_form import BarangFormDialog
import csv
import os
from datetime import datetime

ITEMS_PER_PAGE = 10


class StatCardBarang(QFrame):
    """Kartu statistik untuk halaman barang"""

    def __init__(self, title, value, subtitle, icon, icon_bg, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Text area
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; letter-spacing: 0.5px; background: transparent;")
        text_layout.addWidget(self.title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet("font-size: 28px; font-weight: 800; background: transparent;")
        text_layout.addWidget(self.value_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("font-size: 11px; background: transparent;")
            text_layout.addWidget(self.sub_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Icon box
        icon_frame = QFrame()
        icon_frame.setFixedSize(52, 52)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {icon_bg};
                border-radius: 12px;
            }}
        """)
        icon_layout = QHBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        icon_layout.addWidget(icon_lbl)
        layout.addWidget(icon_frame)

        self._apply_theme()

    def _apply_theme(self):
        theme = db.get_setting("app_theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                QFrame#stat_card {
                    background-color: #1A1D27;
                    border: 1px solid #2D3250;
                    border-radius: 12px;
                }
            """)
            self.title_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; background: transparent;")
            self.value_lbl.setStyleSheet("color: #F1F5F9; font-size: 28px; font-weight: 800; background: transparent;")
            if hasattr(self, 'sub_lbl'):
                self.sub_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        else:
            self.setStyleSheet("""
                QFrame#stat_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
            self.title_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; background: transparent;")
            self.value_lbl.setStyleSheet("color: #1E293B; font-size: 28px; font-weight: 800; background: transparent;")
            if hasattr(self, 'sub_lbl'):
                self.sub_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")

    def update_value(self, value, subtitle=""):
        self.value_lbl.setText(str(value))
        if hasattr(self, 'sub_lbl') and subtitle:
            self.sub_lbl.setText(subtitle)

    def on_theme_changed(self, theme):
        self._apply_theme()


class BarangPage(QWidget):
    """Halaman manajemen barang"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._barang_data = []
        self._filtered_data = []
        self._current_page = 1
        self._setup_ui()
        self._load_data()

        # Search delay timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._filter_table)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── STAT CARDS ROW ────────────────────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.card_total = StatCardBarang(
            "Total Produk", "0", "⬆ Memuat data...",
            "📦", "#1E3A5F"
        )
        self.card_menipis = StatCardBarang(
            "Stok Menipis", "0", "⚠ Perlu restock segera",
            "🛒", "#7C3D12"
        )
        self.card_habis = StatCardBarang(
            "Stok Habis", "0", "⊘ Tidak tersedia di etalase",
            "🚫", "#7F1D1D"
        )

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_menipis)
        cards_layout.addWidget(self.card_habis)
        layout.addLayout(cards_layout)

        # ── TOOLBAR ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Cari nama produk atau SKU...")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input, 2)

        # Kategori filter
        self.kategori_filter = QComboBox()
        self.kategori_filter.addItem("Semua Kategori")
        self.kategori_filter.setFixedHeight(40)
        self.kategori_filter.setMinimumWidth(150)
        self.kategori_filter.currentTextChanged.connect(self._filter_table)
        toolbar.addWidget(self.kategori_filter)

        # Sort filter
        self.sort_filter = QComboBox()
        self.sort_filter.addItems(["Urutkan: Terbaru", "Nama A-Z", "Stok Terendah", "Harga Tertinggi"])
        self.sort_filter.setFixedHeight(40)
        self.sort_filter.setMinimumWidth(170)
        self.sort_filter.currentTextChanged.connect(self._filter_table)
        toolbar.addWidget(self.sort_filter)

        toolbar.addStretch()

        if auth.is_admin:
            btn_export = QPushButton("⬇ Ekspor")
            btn_export.setObjectName("btn_secondary")
            btn_export.setFixedHeight(40)
            btn_export.setCursor(QCursor(Qt.PointingHandCursor))
            btn_export.clicked.connect(self._export_csv)
            toolbar.addWidget(btn_export)

            btn_add = QPushButton("+ Tambah Barang")
            btn_add.setObjectName("btn_primary")
            btn_add.setFixedHeight(40)
            btn_add.setCursor(QCursor(Qt.PointingHandCursor))
            btn_add.clicked.connect(self._open_add_form)
            toolbar.addWidget(btn_add)

        layout.addLayout(toolbar)

        # ── TABLE ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Produk", "SKU", "Kategori", "Stok", "Harga", "", "Aksi"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 0)  # hidden spacer
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 120)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # ── PAGINATION ────────────────────────────────────────────────────────
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.pagination_info_lbl = QLabel("")
        self.pagination_info_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        pagination_layout.addWidget(self.pagination_info_lbl)
        pagination_layout.addStretch()

        self.btn_prev = QPushButton("Sebelumnya")
        self.btn_prev.setObjectName("page_btn")
        self.btn_prev.setFixedHeight(34)
        self.btn_prev.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_prev.clicked.connect(self._prev_page)
        pagination_layout.addWidget(self.btn_prev)

        self._page_buttons_container = QHBoxLayout()
        self._page_buttons_container.setSpacing(4)
        pagination_layout.addLayout(self._page_buttons_container)

        self.btn_next = QPushButton("Selanjutnya")
        self.btn_next.setObjectName("page_btn")
        self.btn_next.setFixedHeight(34)
        self.btn_next.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_next.clicked.connect(self._next_page)
        pagination_layout.addWidget(self.btn_next)

        layout.addLayout(pagination_layout)

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
                    "deskripsi": getattr(b, 'deskripsi', '') or "",
                    "kategori": b.kategori or "",
                    "harga_beli": b.harga_beli,
                    "harga_jual": b.harga_jual,
                    "stok": b.stok,
                    "stok_min": b.stok_min,
                    "satuan": b.satuan,
                    "is_low_stock": b.stok <= b.stok_min and b.stok > 0,
                    "is_empty": b.stok == 0,
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

        # Update stat cards
        total = len(self._barang_data)
        menipis = sum(1 for b in self._barang_data if b["is_low_stock"])
        habis = sum(1 for b in self._barang_data if b["is_empty"])
        self.card_total.update_value(f"{total:,}", f"⬆ {total} produk aktif")
        self.card_menipis.update_value(str(menipis), "⚠ Perlu restock segera")
        self.card_habis.update_value(str(habis), "⊘ Tidak tersedia di etalase")

        self._current_page = 1
        self._filter_table()

    def _on_search_changed(self):
        self._search_timer.start(300)

    def _filter_table(self):
        """Filter tabel berdasarkan search dan filter"""
        query = self.search_input.text().strip().lower()
        kat_filter = self.kategori_filter.currentText()
        sort_text = self.sort_filter.currentText()

        filtered = list(self._barang_data)
        if query:
            filtered = [b for b in filtered if (
                query in b["nama"].lower() or
                query in b["kode"].lower() or
                query in b["barcode"].lower()
            )]
        if kat_filter != "Semua Kategori":
            filtered = [b for b in filtered if b["kategori"] == kat_filter]

        # Sort
        if "Nama A-Z" in sort_text:
            filtered.sort(key=lambda x: x["nama"])
        elif "Stok Terendah" in sort_text:
            filtered.sort(key=lambda x: x["stok"])
        elif "Harga Tertinggi" in sort_text:
            filtered.sort(key=lambda x: x["harga_jual"], reverse=True)

        self._filtered_data = filtered
        self._render_page()

    def _render_page(self):
        """Render halaman data saat ini"""
        total = len(self._filtered_data)
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self._current_page = max(1, min(self._current_page, total_pages))

        start = (self._current_page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_data = self._filtered_data[start:end]

        self._render_table(page_data)

        # Update pagination info
        end_actual = min(end, total)
        self.pagination_info_lbl.setText(
            f"Menampilkan {start + 1 if total > 0 else 0}-{end_actual} dari {total} produk"
        )

        # Update page buttons
        # Clear old page buttons
        while self._page_buttons_container.count():
            item = self._page_buttons_container.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()

        max_visible = 4
        for i in range(1, min(total_pages + 1, max_visible + 1)):
            btn = QPushButton(str(i))
            btn.setFixedSize(34, 34)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            if i == self._current_page:
                btn.setObjectName("page_btn_active")
            else:
                btn.setObjectName("page_btn")
                btn.clicked.connect(lambda _, p=i: self._go_to_page(p))
            self._page_buttons_container.addWidget(btn)

        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < total_pages)

    def _go_to_page(self, page):
        self._current_page = page
        self._render_page()

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._render_page()

    def _next_page(self):
        total = len(self._filtered_data)
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        if self._current_page < total_pages:
            self._current_page += 1
            self._render_page()

    def on_theme_changed(self, theme: str):
        """Hook saat tema berubah"""
        self.card_total.on_theme_changed(theme)
        self.card_menipis.on_theme_changed(theme)
        self.card_habis.on_theme_changed(theme)
        self._render_page()

    def _get_product_emoji(self, nama: str, kategori: str) -> str:
        name_lower = (nama or "").lower()
        cat_lower = (kategori or "").lower()
        if "kopi" in name_lower: return "☕"
        if "burger" in name_lower or "ayam" in name_lower: return "🍔"
        if "keripik" in name_lower or "singkong" in name_lower: return "🍟"
        if "air" in name_lower or "mineral" in name_lower: return "💧"
        if "mie" in name_lower: return "🍜"
        if "deterjan" in name_lower or "sabun" in name_lower: return "🧴"
        if "beras" in name_lower: return "🌾"
        if "teh" in name_lower: return "🍵"
        if "keyboard" in name_lower or "elektronik" in cat_lower: return "⌨️"
        if "minuman" in cat_lower: return "🧋"
        if "makanan" in cat_lower: return "🍱"
        if "kebersihan" in cat_lower: return "🧹"
        return "📦"

    def _render_table(self, data: list):
        """Render data ke tabel"""
        is_dark = (db.get_setting("app_theme", "light") == "dark")
        text_primary = "#F1F5F9" if is_dark else "#1E293B"
        text_muted = "#94A3B8" if is_dark else "#64748B"
        icon_bg = "#21263A" if is_dark else "#F1F5F9"

        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setRowCount(len(data))

        for row, b in enumerate(data):
            self.table.setRowHeight(row, 62)

            # ── Col 0: Produk (emoji thumbnail + nama + deskripsi) ──
            product_widget = QWidget()
            product_widget.setStyleSheet("background: transparent;")
            product_layout = QHBoxLayout(product_widget)
            product_layout.setContentsMargins(8, 4, 8, 4)
            product_layout.setSpacing(12)

            emoji = self._get_product_emoji(b["nama"], b["kategori"])
            thumb_lbl = QLabel(emoji)
            thumb_lbl.setFixedSize(38, 38)
            thumb_lbl.setAlignment(Qt.AlignCenter)
            thumb_lbl.setStyleSheet(f"""
                background-color: {icon_bg};
                border-radius: 8px;
                font-size: 18px;
            """)
            product_layout.addWidget(thumb_lbl)

            name_layout = QVBoxLayout()
            name_layout.setSpacing(1)
            name_lbl = QLabel(b["nama"])
            name_lbl.setStyleSheet(f"color: {text_primary}; font-weight: 600; font-size: 13px; background: transparent;")
            name_layout.addWidget(name_lbl)

            sku_lbl = QLabel(b.get("deskripsi", "") or b["kode"])
            sku_lbl.setStyleSheet(f"color: {text_muted}; font-size: 11px; background: transparent;")
            name_layout.addWidget(sku_lbl)
            product_layout.addLayout(name_layout)

            self.table.setCellWidget(row, 0, product_widget)

            # ── Col 1: SKU / Kode ──
            sku_item = QTableWidgetItem(b["kode"])
            sku_item.setForeground(QColor(text_muted))
            sku_item.setData(Qt.UserRole, b["id"])
            self.table.setItem(row, 1, sku_item)

            # ── Col 2: Kategori ──
            kat_item = QTableWidgetItem(b["kategori"] or "-")
            kat_item.setForeground(QColor(text_muted))
            kat_item.setData(Qt.UserRole, b["id"])
            self.table.setItem(row, 2, kat_item)

            # ── Col 3: Stok badge ──
            stok_widget = QWidget()
            stok_widget.setStyleSheet("background: transparent;")
            stok_layout = QHBoxLayout(stok_widget)
            stok_layout.setContentsMargins(4, 2, 4, 2)
            stok_layout.setAlignment(Qt.AlignCenter)

            stok_lbl = QLabel(f"● {b['stok']} Unit")
            stok_lbl.setWordWrap(False)
            stok_lbl.setFixedHeight(24)
            stok_lbl.setMinimumWidth(80)
            stok_lbl.setAlignment(Qt.AlignCenter)
            if b["is_empty"]:
                bg_col = "#7F1D1D" if is_dark else "#FEE2E2"
                fg_col = "#FCA5A5" if is_dark else "#B91C1C"
                border_col = "#991B1B" if is_dark else "#FECACA"
            elif b["is_low_stock"]:
                bg_col = "#78350F" if is_dark else "#FEF3C7"
                fg_col = "#FCD34D" if is_dark else "#B45309"
                border_col = "#92400E" if is_dark else "#FDE68A"
            else:
                bg_col = "#14532D" if is_dark else "#DCFCE7"
                fg_col = "#86EFAC" if is_dark else "#15803D"
                border_col = "#166534" if is_dark else "#BBF7D0"

            stok_lbl.setStyleSheet(f"background-color: {bg_col}; color: {fg_col}; border: 1px solid {border_col}; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 700; white-space: nowrap;")
            stok_layout.addWidget(stok_lbl)
            self.table.setCellWidget(row, 3, stok_widget)

            # ── Col 4: Harga ──
            harga_item = QTableWidgetItem(format_rupiah(b["harga_jual"]))
            harga_item.setForeground(QColor(text_primary))
            harga_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            harga_item.setData(Qt.UserRole, b["id"])
            self.table.setItem(row, 4, harga_item)

            # ── Col 5: empty ──
            self.table.setItem(row, 5, QTableWidgetItem(""))

            # ── Col 6: Action buttons ──
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(4)
            action_layout.setAlignment(Qt.AlignCenter)

            if auth.is_admin:
                btn_restock = QPushButton("＋")
                btn_restock.setFixedSize(28, 28)
                btn_restock.setToolTip("Restock / Tambah Stok")
                btn_restock.setStyleSheet("""
                    QPushButton { background-color: #14532D; color: #86EFAC; border-radius: 6px; font-weight: bold; border: none; }
                    QPushButton:hover { background-color: #166534; }
                """)
                btn_restock.setCursor(QCursor(Qt.PointingHandCursor))
                btn_restock.clicked.connect(lambda _, bid=b["id"]: self._open_edit_form(bid))
                action_layout.addWidget(btn_restock)

                btn_edit = QPushButton("✏")
                btn_edit.setFixedSize(28, 28)
                btn_edit.setToolTip("Edit")
                btn_edit.setStyleSheet("""
                    QPushButton { background-color: #1E3A5F; color: #93C5FD; border-radius: 6px; font-weight: bold; border: none; }
                    QPushButton:hover { background-color: #1E40AF; }
                """)
                btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
                btn_edit.clicked.connect(lambda _, bid=b["id"]: self._open_edit_form(bid))
                action_layout.addWidget(btn_edit)

                btn_del = QPushButton("🗑")
                btn_del.setFixedSize(28, 28)
                btn_del.setToolTip("Hapus")
                btn_del.setStyleSheet("""
                    QPushButton { background-color: #7F1D1D; color: #FCA5A5; border-radius: 6px; font-weight: bold; border: none; }
                    QPushButton:hover { background-color: #991B1B; }
                """)
                btn_del.setCursor(QCursor(Qt.PointingHandCursor))
                btn_del.clicked.connect(lambda _, bid=b["id"]: self._delete_barang(bid))
                action_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 6, action_widget)

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

    def on_theme_changed(self, theme: str):
        """Update stat cards and table styling on theme switch"""
        for card in [self.card_total, self.card_menipis, self.card_habis]:
            card._apply_theme()
        self._load_data()
