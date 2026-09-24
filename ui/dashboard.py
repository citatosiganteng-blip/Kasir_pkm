"""
KasirKu Dashboard Page
Halaman utama dengan statistik ringkasan
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QScrollArea, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QCursor
from datetime import datetime, date, timedelta

from database.db import db
from database.models import Transaksi, Barang, Pengeluaran
from utils.helpers import format_rupiah, format_rupiah_short, format_datetime, get_today_range, get_month_range


class StatCard(QFrame):
    """Kartu statistik untuk dashboard yang adaptif terhadap mode terang / gelap"""
    def __init__(self, title: str, value: str, icon: str,
                 subtitle: str = "", color: str = "#6C63FF", parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")
        self.setFrameStyle(QFrame.NoFrame)
        self.color = color
        self.title_str = title
        self.subtitle_str = subtitle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Icon
        self.icon_frame = QFrame()
        self.icon_frame.setObjectName("stat_card_icon")
        self.icon_frame.setFixedSize(52, 52)
        icon_layout = QVBoxLayout(self.icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        icon_layout.addWidget(icon_lbl)
        layout.addWidget(self.icon_frame)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        text_layout.addWidget(self.title_lbl)

        self.value_lbl = QLabel(value)
        text_layout.addWidget(self.value_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            text_layout.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

        layout.addLayout(text_layout)
        layout.addStretch()

        current_theme = db.get_setting("app_theme", "light")
        self.apply_theme(current_theme)

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet(f"""
                QFrame#stat_card {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1A1D27, stop:1 #1E2235);
                    border: 1px solid #2D3250;
                    border-radius: 14px;
                    min-height: 105px;
                }}
                QFrame#stat_card:hover {{
                    border-color: {self.color};
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1E2235, stop:1 #21263A);
                }}
                QFrame#stat_card_icon {{
                    background-color: {self.color}22;
                    border-radius: 12px;
                    border: 1px solid {self.color}44;
                }}
            """)
            self.title_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600; background: transparent;")
            self.value_lbl.setStyleSheet("color: #F1F5F9; font-size: 20px; font-weight: 800; background: transparent;")
            if self.sub_lbl:
                self.sub_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        else:
            self.setStyleSheet(f"""
                QFrame#stat_card {{
                    background-color: #FFFFFF;
                    border: 1.5px solid #E2E8F0;
                    border-radius: 14px;
                    min-height: 105px;
                }}
                QFrame#stat_card:hover {{
                    border-color: {self.color};
                    background-color: #F8FAFC;
                }}
                QFrame#stat_card_icon {{
                    background-color: {self.color}15;
                    border-radius: 12px;
                    border: 1px solid {self.color}30;
                }}
            """)
            self.title_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600; background: transparent;")
            self.value_lbl.setStyleSheet("color: #1E293B; font-size: 20px; font-weight: 800; background: transparent;")
            if self.sub_lbl:
                self.sub_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class DashboardPage(QWidget):
    """Halaman dashboard utama"""

    def __init__(self, on_navigate=None, parent=None):
        super().__init__(parent)
        self.on_navigate = on_navigate
        self._current_theme = db.get_setting("app_theme", "light")
        self._setup_ui()
        self._load_data()

        # Auto refresh setiap 30 detik
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._load_data)
        self.refresh_timer.start(30000)

    def on_theme_changed(self, theme: str):
        """Hook yang dipanggil saat user mengubah tema"""
        self._current_theme = theme
        for card in [
            self.card_pemasukan, self.card_transaksi,
            self.card_pengeluaran, self.card_stok_rendah,
            self.card_bulanan, self.card_laba,
            self.card_total_barang, self.card_transaksi_batal
        ]:
            if hasattr(card, "apply_theme"):
                card.apply_theme(theme)
        if hasattr(self, "_divider"):
            self._divider.setStyleSheet(
                f"background: {'#2D3250' if theme == 'dark' else '#E2E8F0'}; max-height: 1px; border: none;"
            )
        self._load_data()

    def _setup_ui(self):
        # Scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()

        now = datetime.now()
        greeting = "Selamat Pagi" if now.hour < 12 else ("Selamat Siang" if now.hour < 15 else "Selamat Sore")
        from auth.auth_manager import auth
        user_name = auth.current_user.nama_lengkap or auth.current_user.username if auth.current_user else "User"

        title_lbl = QLabel(f"{greeting}, {user_name}! 👋")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent;")
        title_layout.addWidget(title_lbl)

        date_lbl = QLabel(now.strftime("%A, %d %B %Y"))
        date_lbl.setStyleSheet("font-size: 13px; color: #64748B; background: transparent;")
        title_layout.addWidget(date_lbl)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.setFixedHeight(38)
        btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        btn_refresh.clicked.connect(self._load_data)
        header_layout.addWidget(btn_refresh)

        main_layout.addLayout(header_layout)

        # Divider
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.HLine)
        self._divider.setStyleSheet(
            f"background: {'#2D3250' if self._current_theme == 'dark' else '#E2E8F0'}; max-height: 1px; border: none;"
        )
        main_layout.addWidget(self._divider)

        # Stat Cards
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.card_pemasukan = StatCard(
            "Pemasukan Hari Ini", "Rp 0", "💰",
            "Total transaksi penjualan", "#10B981"
        )
        self.card_transaksi = StatCard(
            "Transaksi Hari Ini", "0", "🧾",
            "Jumlah transaksi berhasil", "#2563EB"
        )
        self.card_pengeluaran = StatCard(
            "Pengeluaran Hari Ini", "Rp 0", "💸",
            "Total biaya keluar", "#EF4444"
        )
        self.card_stok_rendah = StatCard(
            "Stok Rendah", "0 item", "⚠️",
            "Perlu segera restok", "#F59E0B"
        )

        stats_grid.addWidget(self.card_pemasukan, 0, 0)
        stats_grid.addWidget(self.card_transaksi, 0, 1)
        stats_grid.addWidget(self.card_pengeluaran, 0, 2)
        stats_grid.addWidget(self.card_stok_rendah, 0, 3)

        # Bulan ini
        self.card_bulanan = StatCard(
            "Pemasukan Bulan Ini", "Rp 0", "📈",
            "Akumulasi penjualan", "#2563EB"
        )
        self.card_laba = StatCard(
            "Estimasi Laba Bersih", "Rp 0", "📊",
            "Pemasukan - Pengeluaran", "#10B981"
        )
        self.card_total_barang = StatCard(
            "Total Barang", "0", "📦",
            "Jenis barang aktif", "#8B5CF6"
        )
        self.card_transaksi_batal = StatCard(
            "Transaksi Void", "0", "❌",
            "Transaksi dibatalkan bulan ini", "#EF4444"
        )

        stats_grid.addWidget(self.card_bulanan, 1, 0)
        stats_grid.addWidget(self.card_laba, 1, 1)
        stats_grid.addWidget(self.card_total_barang, 1, 2)
        stats_grid.addWidget(self.card_transaksi_batal, 1, 3)

        main_layout.addLayout(stats_grid)

        # Bottom section: Recent transactions + Low stock
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        # Recent transactions
        recent_frame = QFrame()
        recent_frame.setObjectName("card")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(18, 18, 18, 18)
        recent_layout.setSpacing(12)

        recent_header = QHBoxLayout()
        recent_title = QLabel("Transaksi Terbaru")
        recent_title.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        recent_layout.addLayout(recent_header)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["Invoice", "Kasir", "Total", "Waktu"])
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setMaximumHeight(220)
        recent_layout.addWidget(self.recent_table)
        bottom_layout.addWidget(recent_frame, 3)

        # Low stock items
        low_stock_frame = QFrame()
        low_stock_frame.setObjectName("card")
        low_layout = QVBoxLayout(low_stock_frame)
        low_layout.setContentsMargins(18, 18, 18, 18)
        low_layout.setSpacing(12)

        low_title = QLabel("⚠️ Stok Hampir Habis")
        low_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F59E0B; background: transparent;")
        low_layout.addWidget(low_title)

        self.low_stock_container = QVBoxLayout()
        self.low_stock_container.setSpacing(8)
        low_layout.addLayout(self.low_stock_container)
        low_layout.addStretch()

        bottom_layout.addWidget(low_stock_frame, 2)

        main_layout.addLayout(bottom_layout)

        # Set scroll as main
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _load_data(self):
        """Load semua data dashboard"""
        today_start, today_end = get_today_range()
        month_start, month_end = get_month_range()

        with db.get_session() as session:
            # Pemasukan hari ini
            from sqlalchemy import func
            today_income = session.query(
                func.coalesce(func.sum(Transaksi.total), 0)
            ).filter(
                Transaksi.tanggal >= today_start,
                Transaksi.tanggal <= today_end,
                Transaksi.status == "selesai"
            ).scalar() or 0

            # Jumlah transaksi hari ini
            today_count = session.query(Transaksi).filter(
                Transaksi.tanggal >= today_start,
                Transaksi.tanggal <= today_end,
                Transaksi.status == "selesai"
            ).count()

            # Pengeluaran hari ini
            today_expense = session.query(
                func.coalesce(func.sum(Pengeluaran.nominal), 0)
            ).filter(
                Pengeluaran.tanggal >= today_start,
                Pengeluaran.tanggal <= today_end,
            ).scalar() or 0

            # Stok rendah
            low_stock_items = session.query(Barang).filter(
                Barang.stok <= Barang.stok_min,
                Barang.aktif == True
            ).all()

            # Pemasukan bulan ini
            month_income = session.query(
                func.coalesce(func.sum(Transaksi.total), 0)
            ).filter(
                Transaksi.tanggal >= month_start,
                Transaksi.tanggal <= month_end,
                Transaksi.status == "selesai"
            ).scalar() or 0

            # Pengeluaran bulan ini
            month_expense = session.query(
                func.coalesce(func.sum(Pengeluaran.nominal), 0)
            ).filter(
                Pengeluaran.tanggal >= month_start,
                Pengeluaran.tanggal <= month_end,
            ).scalar() or 0

            # Total barang aktif
            total_barang = session.query(Barang).filter(Barang.aktif == True).count()

            # Transaksi void bulan ini
            void_count = session.query(Transaksi).filter(
                Transaksi.tanggal >= month_start,
                Transaksi.tanggal <= month_end,
                Transaksi.status == "void"
            ).count()

            # Transaksi terbaru
            recent = session.query(Transaksi).filter(
                Transaksi.status == "selesai"
            ).order_by(Transaksi.tanggal.desc()).limit(8).all()

            recent_data = []
            for t in recent:
                kasir_name = t.kasir.username if t.kasir else "-"
                recent_data.append((t.no_invoice, kasir_name, t.total, t.tanggal))

            # Detach low stock
            low_stock_data = [(b.kode, b.nama, b.stok, b.stok_min, b.satuan) for b in low_stock_items]

        # Update cards
        self.card_pemasukan.set_value(format_rupiah_short(today_income))
        self.card_transaksi.set_value(str(today_count))
        self.card_pengeluaran.set_value(format_rupiah_short(today_expense))
        self.card_stok_rendah.set_value(f"{len(low_stock_data)} item")

        self.card_bulanan.set_value(format_rupiah_short(month_income))
        self.card_laba.set_value(format_rupiah_short(month_income - month_expense))
        self.card_total_barang.set_value(str(total_barang))
        self.card_transaksi_batal.set_value(str(void_count))

        # Update recent transactions table
        self.recent_table.setRowCount(len(recent_data))
        for i, (invoice, kasir, total, tanggal) in enumerate(recent_data):
            self.recent_table.setItem(i, 0, QTableWidgetItem(invoice))
            self.recent_table.setItem(i, 1, QTableWidgetItem(kasir))

            total_item = QTableWidgetItem(format_rupiah(total))
            total_item.setForeground(QColor("#10B981"))
            self.recent_table.setItem(i, 2, total_item)

            self.recent_table.setItem(i, 3, QTableWidgetItem(
                format_datetime(tanggal) if tanggal else ""
            ))

        # Update low stock
        # Clear old widgets
        while self.low_stock_container.count():
            child = self.low_stock_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not low_stock_data:
            no_alert = QLabel("✅ Semua stok dalam kondisi aman")
            no_alert.setStyleSheet("color: #10B981; font-size: 12px; background: transparent;")
            self.low_stock_container.addWidget(no_alert)
        else:
            for kode, nama, stok, stok_min, satuan in low_stock_data[:8]:
                item_frame = QFrame()
                item_frame.setStyleSheet("""
                    QFrame {
                        background: rgba(245, 158, 11, 0.08);
                        border: 1px solid rgba(245, 158, 11, 0.2);
                        border-radius: 8px;
                    }
                """)
                item_layout = QHBoxLayout(item_frame)
                item_layout.setContentsMargins(12, 8, 12, 8)
                item_layout.setSpacing(8)

                name_lbl = QLabel(nama)
                name_lbl.setStyleSheet("font-size: 12px; font-weight: 500; background: transparent;")
                name_lbl.setMaximumWidth(140)
                name_lbl.setWordWrap(False)
                item_layout.addWidget(name_lbl)
                item_layout.addStretch()

                stock_lbl = QLabel(f"{stok}/{stok_min} {satuan}")
                stock_lbl.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 600; background: transparent;")
                item_layout.addWidget(stock_lbl)

                self.low_stock_container.addWidget(item_frame)
