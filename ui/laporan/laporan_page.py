"""
KasirKu Laporan Page
Halaman laporan dan analitik — redesigned matching reference:
- Period filter tabs (Hari ini / Minggu ini / Bulan ini / Kustom)
- 4 stat cards (Pendapatan, Transaksi, Rata-rata, Barang Terjual)
- Bar chart (Grafik Pendapatan per jam)
- Metode Pembayaran breakdown
- Produk Terlaris table
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QMessageBox, QDateEdit, QSizePolicy,
    QScrollArea, QMenu, QAction, QToolTip, QFileDialog
)
from PyQt5.QtCore import Qt, QDate, QSize, QPoint, QRectF
from PyQt5.QtGui import (
    QColor, QFont, QCursor, QPainter, QPen, QBrush, QLinearGradient,
    QPainterPath
)

from sqlalchemy import func
from database.db import db
from database.models import Transaksi, TransaksiDetail, Pengeluaran, Barang
from utils.helpers import (
    format_rupiah, format_rupiah_short, format_tanggal, format_datetime,
    get_today_range, get_month_range
)
from datetime import datetime, date, timedelta
import os
import csv
import math


class BarChartWidget(QWidget):
    """
    Modern Bar Chart Widget:
    - Tinggi proporsional (min 280px)
    - Garis grid horizontal halus & skala sumbu Y (nominal Rupiah)
    - Batang bergradien dengan sudut membulat atas (rounded top corners)
    - Highlight otomatis pada batang dengan penjualan tertinggi (peak sales)
    - Mouse tracking & tooltip interaktif saat hover
    - Adaptif terhadap Dark Mode dan Light Mode
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list of (label_str, numeric_value)
        self._hover_idx = -1
        self._bar_rects = []  # list of (QRectF, label, val)
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_data(self, data: list):
        """data: list of (label_str, numeric_value)"""
        self._data = data
        self._hover_idx = -1
        self._bar_rects = []
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        hovered = -1
        for i, (rect, label, val) in enumerate(self._bar_rects):
            # Allow hover over the whole vertical column of the bar
            if rect.left() - 4 <= pos.x() <= rect.right() + 4 and 15 <= pos.y() <= self.height() - 25:
                hovered = i
                break

        if hovered != self._hover_idx:
            self._hover_idx = hovered
            self.update()
            if 0 <= hovered < len(self._data):
                label, val = self._data[hovered]
                tip_text = f"<b>{label}</b><br>Total Penjualan: <b>{format_rupiah(val)}</b>"
                QToolTip.showText(event.globalPos(), tip_text, self)
            else:
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_idx = -1
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")

        # Color palettes matching reference dashboard
        grid_color = QColor("#22283A" if is_dark else "#E2E8F0")
        axis_text_color = QColor("#94A3B8" if is_dark else "#64748B")

        # Regular bar colors (slate blue gradient)
        bar_top_normal = QColor("#465F87" if is_dark else "#60A5FA")
        bar_bot_normal = QColor("#2B3D5B" if is_dark else "#2563EB")

        # Peak bar highlight colors (Soft light blue/indigo like reference mockup)
        bar_top_peak = QColor("#C7D2FE" if is_dark else "#1E40AF")
        bar_bot_peak = QColor("#93C5FD" if is_dark else "#3B82F6")

        hover_outline = QColor("#FFFFFF" if is_dark else "#1E293B")

        w = self.width()
        h = self.height()

        margin_l = 68   # Room for Y labels (e.g. "Rp 1.5jt")
        margin_r = 24
        margin_top = 28
        margin_bot = 38  # Room for X labels (e.g. "08:00")

        chart_w = max(10, w - margin_l - margin_r)
        chart_h = max(10, h - margin_top - margin_bot)

        # Determine scale max
        raw_max = max((v for _, v in self._data), default=0) if self._data else 0
        scale_max = self._calc_scale_max(raw_max)

        # ── 1. DRAW HORIZONTAL GRID LINES & Y-AXIS LABELS ──
        painter.setFont(QFont("Segoe UI", 8))
        grid_steps = 4
        for step in range(grid_steps + 1):
            ratio = step / float(grid_steps)
            y_pos = int(margin_top + chart_h - (ratio * chart_h))
            val_at_line = ratio * scale_max

            # Grid line
            painter.setPen(QPen(grid_color, 1, Qt.DashLine if step > 0 else Qt.SolidLine))
            painter.drawLine(margin_l, y_pos, w - margin_r, y_pos)

            # Label on the left
            painter.setPen(QPen(axis_text_color))
            label_y = format_rupiah_short(val_at_line)
            painter.drawText(0, y_pos - 8, margin_l - 10, 16, Qt.AlignRight | Qt.AlignVCenter, label_y)

        # ── 2. DRAW BARS & X-AXIS LABELS ──
        self._bar_rects = []
        if not self._data:
            painter.end()
            return

        n = len(self._data)
        # Find peak index (highest value > 0)
        peak_idx = -1
        if raw_max > 0:
            for idx, (_, v) in enumerate(self._data):
                if v == raw_max:
                    peak_idx = idx
                    break

        # Calculate optimal bar width and gap (proportional, max 50px)
        slot_w = chart_w / float(n)
        bar_w = min(48.0, max(14.0, slot_w * 0.56))

        for i, (label, val) in enumerate(self._data):
            center_x = margin_l + (i + 0.5) * slot_w
            x = center_x - (bar_w / 2.0)

            is_peak = (i == peak_idx and val > 0)
            is_hover = (i == self._hover_idx)

            if val > 0:
                bar_h = max(6.0, (val / float(scale_max)) * chart_h)
            else:
                bar_h = 4.0  # subtle pill at baseline for zero

            y = margin_top + chart_h - bar_h
            bar_rect = QRectF(x, y, bar_w, bar_h)
            self._bar_rects.append((bar_rect, label, val))

            # Choose colors
            if is_peak:
                c_top = bar_top_peak
                c_bot = bar_bot_peak
            else:
                c_top = bar_top_normal
                c_bot = bar_bot_normal

            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, c_top)
            grad.setColorAt(1, c_bot)

            painter.setBrush(QBrush(grad))

            if is_hover:
                painter.setPen(QPen(hover_outline, 1.5))
            else:
                painter.setPen(Qt.NoPen)

            # Draw rounded top bar
            corner_r = min(6.0, bar_w / 3.0)
            path = QPainterPath()
            path.moveTo(x, y + bar_h)
            path.lineTo(x, y + corner_r)
            path.quadTo(x, y, x + corner_r, y)
            path.lineTo(x + bar_w - corner_r, y)
            path.quadTo(x + bar_w, y, x + bar_w, y + corner_r)
            path.lineTo(x + bar_w, y + bar_h)
            path.closeSubpath()
            painter.drawPath(path)

            # Draw value tag on top of peak bar or hovered bar
            if is_peak or is_hover:
                painter.setPen(QPen(c_top if not is_hover else hover_outline))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                val_short = format_rupiah_short(val)
                painter.drawText(int(center_x - 40), int(y - 18), 80, 16, Qt.AlignCenter, val_short)

            # X label
            painter.setPen(QPen(axis_text_color))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold if is_peak else QFont.Normal))
            painter.drawText(int(center_x - 35), int(margin_top + chart_h + 10), 70, 18, Qt.AlignCenter, label)

        painter.end()

    @staticmethod
    def _calc_scale_max(val: float) -> float:
        if val <= 0:
            return 500000.0
        exp = math.floor(math.log10(val))
        base = val / (10 ** exp)
        if base <= 1.0:
            nice = 1.0
        elif base <= 1.5:
            nice = 1.5
        elif base <= 2.0:
            nice = 2.0
        elif base <= 3.0:
            nice = 3.0
        elif base <= 5.0:
            nice = 5.0
        elif base <= 7.5:
            nice = 7.5
        else:
            nice = 10.0
        return float(nice * (10 ** exp))


class LaporanPage(QWidget):
    """Halaman laporan — redesigned"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dt_from = None
        self._dt_to = None
        self._current_period = "hari_ini"
        self._setup_ui()
        self._load_all()

    def _setup_ui(self):
        # Outer scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setObjectName("laporan_content")
        content.setStyleSheet("#laporan_content { background: transparent; }")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ── HEADER ────────────────────────────────────────────────────────────
        header_top = QLabel("ANALYTICS & LAPORAN")
        header_top.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 1px; background: transparent;")
        layout.addWidget(header_top)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_lbl = QLabel("Laporan Penjualan")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        # Export buttons
        btn_export_excel = QPushButton("⬇ Export Excel")
        btn_export_excel.setObjectName("btn_secondary")
        btn_export_excel.setFixedHeight(36)
        btn_export_excel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_export_excel.clicked.connect(self._export_excel)
        header_row.addWidget(btn_export_excel)

        btn_export_csv = QPushButton("📄 Export CSV")
        btn_export_csv.setFixedHeight(36)
        btn_export_csv.setCursor(QCursor(Qt.PointingHandCursor))
        btn_export_csv.clicked.connect(self._export_csv)
        header_row.addWidget(btn_export_csv)

        layout.addLayout(header_row)

        # ── PERIOD FILTER TABS ────────────────────────────────────────────────
        period_row = QHBoxLayout()
        period_row.setSpacing(6)

        self._period_buttons = {}
        periods = [
            ("hari_ini", "Hari ini"),
            ("minggu_ini", "Minggu ini"),
            ("bulan_ini", "Bulan ini"),
            ("kustom", "Kustom"),
        ]
        for key, label in periods:
            btn = QPushButton(label)
            btn.setObjectName("period_tab_active" if key == "hari_ini" else "period_tab")
            btn.setFixedHeight(34)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, k=key: self._set_period(k))
            period_row.addWidget(btn)
            self._period_buttons[key] = btn

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setFixedHeight(34)
        self.date_from.hide()
        period_row.addWidget(self.date_from)

        self.lbl_sd = QLabel("s/d")
        self.lbl_sd.setStyleSheet("color: #64748B; background: transparent;")
        self.lbl_sd.hide()
        period_row.addWidget(self.lbl_sd)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedHeight(34)
        self.date_to.hide()
        period_row.addWidget(self.date_to)

        self.btn_apply = QPushButton("Tampilkan")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_apply.hide()
        self.btn_apply.clicked.connect(self._load_all)
        period_row.addWidget(self.btn_apply)
        period_row.addStretch()

        layout.addLayout(period_row)

        # ── 4 STAT CARDS ──────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_pendapatan = self._make_stat_card("Total Pendapatan", "Rp 0", "+0% dari kemarin", "📈", "#1E3A5F")
        self.card_transaksi = self._make_stat_card("Total Transaksi", "0 Transaksi", "+0% dari kemarin", "📋", "#14532D")
        self.card_rata = self._make_stat_card("Rata-rata Peranjang", "Rp 0", "+0% dari kemarin", "🛍", "#7C3D12")
        self.card_terjual = self._make_stat_card("Barang Terjual", "0 Unit", "+0% dari kemarin", "📦", "#4C1D95")

        for c in [self.card_pendapatan, self.card_transaksi, self.card_rata, self.card_terjual]:
            cards_row.addWidget(c)
        layout.addLayout(cards_row)

        # ── CHART + PAYMENT METHOD ROW ────────────────────────────────────────
        chart_row = QHBoxLayout()
        chart_row.setSpacing(14)

        # Bar chart frame
        chart_frame = QFrame()
        chart_frame.setObjectName("card")
        chart_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        chart_frame.setMinimumHeight(350)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 14, 16, 14)
        chart_layout.setSpacing(8)

        chart_title_row = QHBoxLayout()
        chart_title_lbl = QLabel("Grafik Pendapatan")
        chart_title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        chart_title_row.addWidget(chart_title_lbl)
        chart_title_row.addStretch()
        legend_dot = QLabel("●")
        legend_dot.setStyleSheet("color: #3B82F6; font-size: 14px; background: transparent;")
        chart_title_row.addWidget(legend_dot)
        legend_lbl = QLabel("Pendapatan (Rp)")
        legend_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        chart_title_row.addWidget(legend_lbl)
        chart_layout.addLayout(chart_title_row)

        self.chart_sub = QLabel("Tren penjualan per jam hari ini")
        self.chart_sub.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        chart_layout.addWidget(self.chart_sub)

        self.bar_chart = BarChartWidget()
        chart_layout.addWidget(self.bar_chart)

        chart_row.addWidget(chart_frame, 3)

        # Payment method panel
        payment_frame = QFrame()
        payment_frame.setObjectName("card")
        payment_frame.setFixedWidth(280)
        payment_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        payment_frame.setMinimumHeight(350)
        payment_layout = QVBoxLayout(payment_frame)
        payment_layout.setContentsMargins(16, 14, 16, 14)
        payment_layout.setSpacing(10)

        payment_title = QLabel("Metode Pembayaran")
        payment_title.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        payment_layout.addWidget(payment_title)

        payment_sub = QLabel("Distribusi transaksi berdasarkan metode bayar")
        payment_sub.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        payment_layout.addWidget(payment_sub)

        self._payment_rows_widget = QWidget()
        self._payment_rows_widget.setStyleSheet("background: transparent;")
        self._payment_rows_layout = QVBoxLayout(self._payment_rows_widget)
        self._payment_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._payment_rows_layout.setSpacing(10)
        payment_layout.addWidget(self._payment_rows_widget)

        payment_layout.addStretch()

        # Total metode
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #2D3250;")
        payment_layout.addWidget(sep2)

        self.total_metode_lbl = QLabel("Total Metode    100% Terverifikasi")
        self.total_metode_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        payment_layout.addWidget(self.total_metode_lbl)

        chart_row.addWidget(payment_frame)
        layout.addLayout(chart_row)

        # ── PRODUK TERLARIS ───────────────────────────────────────────────────
        produk_frame = QFrame()
        produk_frame.setObjectName("card")
        produk_layout = QVBoxLayout(produk_frame)
        produk_layout.setContentsMargins(16, 14, 16, 14)
        produk_layout.setSpacing(12)

        produk_header = QHBoxLayout()
        produk_title_layout = QVBoxLayout()
        produk_title = QLabel("Produk Terlaris")
        produk_title.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        produk_title_layout.addWidget(produk_title)
        produk_sub = QLabel("Daftar barang dengan volume penjualan tertinggi")
        produk_sub.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        produk_title_layout.addWidget(produk_sub)
        produk_header.addLayout(produk_title_layout)
        produk_header.addStretch()

        self.produk_search = QLabel("🔍 Cari produk terlaris...")
        self.produk_search.setStyleSheet("color: #64748B; font-size: 12px; background: #21263A; border-radius: 6px; padding: 6px 12px;")
        produk_header.addWidget(self.produk_search)
        produk_layout.addLayout(produk_header)

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6)
        self.product_table.setHorizontalHeaderLabels([
            "No", "Nama Produk", "Kategori", "Terjual", "Harga Satuan", "Total Pendapatan"
        ])
        hh = self.product_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self.product_table.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.product_table.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setShowGrid(False)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setMaximumHeight(360)
        produk_layout.addWidget(self.product_table)

        # Pagination row
        pagination_row = QHBoxLayout()
        self.produk_info_lbl = QLabel("")
        self.produk_info_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        pagination_row.addWidget(self.produk_info_lbl)
        pagination_row.addStretch()

        btn_prev = QPushButton("‹")
        btn_prev.setObjectName("page_btn")
        btn_prev.setFixedSize(30, 30)
        btn_prev.setCursor(QCursor(Qt.PointingHandCursor))
        pagination_row.addWidget(btn_prev)

        for i in range(1, 4):
            btn = QPushButton(str(i))
            btn.setObjectName("page_btn_active" if i == 1 else "page_btn")
            btn.setFixedSize(30, 30)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            pagination_row.addWidget(btn)

        btn_next = QPushButton("›")
        btn_next.setObjectName("page_btn")
        btn_next.setFixedSize(30, 30)
        btn_next.setCursor(QCursor(Qt.PointingHandCursor))
        pagination_row.addWidget(btn_next)

        produk_layout.addLayout(pagination_row)
        layout.addWidget(produk_frame)

        self._product_data = []
        self._daily_data = []
        self._expense_data = []

    def _make_stat_card(self, title, value, subtitle, icon, icon_bg):
        frame = QFrame()
        frame.setObjectName("laporan_stat_card")
        frame.setMinimumHeight(110)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        vl = QVBoxLayout(frame)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(10)

        icon_frame = QFrame()
        icon_frame.setFixedSize(38, 38)
        icon_frame.setStyleSheet(f"background-color: {icon_bg}; border-radius: 9px;")
        icon_l = QHBoxLayout(icon_frame)
        icon_l.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 17px; background: transparent;")
        icon_l.addWidget(icon_lbl)
        row1.addWidget(icon_frame)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; background: transparent;")
        row1.addWidget(title_lbl)
        row1.addStretch()
        vl.addLayout(row1)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        vl.addWidget(val_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: transparent;")
        vl.addWidget(sub_lbl)

        frame._title_lbl = title_lbl
        frame._val_lbl = val_lbl
        frame._sub_lbl = sub_lbl
        self._apply_stat_card_style(frame)
        return frame

    def _apply_stat_card_style(self, frame):
        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")
        if is_dark:
            frame.setStyleSheet("""
                QFrame#laporan_stat_card {
                    background-color: #1A1D27;
                    border: 1px solid #2D3250;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; background: transparent;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 800; background: transparent;")
            if hasattr(frame, "_sub_lbl"):
                frame._sub_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: transparent;")
        else:
            frame.setStyleSheet("""
                QFrame#laporan_stat_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("color: #0F172A; font-size: 20px; font-weight: 800; background: transparent;")
            if hasattr(frame, "_sub_lbl"):
                frame._sub_lbl.setStyleSheet("color: #16A34A; font-size: 11px; background: transparent;")

    def _set_period(self, key: str):
        self._current_period = key
        for k, btn in self._period_buttons.items():
            btn.setObjectName("period_tab_active" if k == key else "period_tab")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        show_custom = (key == "kustom")
        self.date_from.setVisible(show_custom)
        self.date_to.setVisible(show_custom)
        self.lbl_sd.setVisible(show_custom)
        self.btn_apply.setVisible(show_custom)

        if key != "kustom":
            self._load_all()

    def _get_date_range(self):
        today = date.today()
        if self._current_period == "hari_ini":
            return (datetime.combine(today, datetime.min.time()),
                    datetime.combine(today, datetime.max.time()))
        elif self._current_period == "minggu_ini":
            start = today - timedelta(days=today.weekday())
            return (datetime.combine(start, datetime.min.time()),
                    datetime.combine(today, datetime.max.time()))
        elif self._current_period == "bulan_ini":
            return get_month_range()
        else:  # kustom
            d_from = self.date_from.date().toPyDate()
            d_to = self.date_to.date().toPyDate()
            return (datetime.combine(d_from, datetime.min.time()),
                    datetime.combine(d_to, datetime.max.time()))

    def _load_all(self):
        dt_from, dt_to = self._get_date_range()
        self._dt_from = dt_from
        self._dt_to = dt_to
        self._load_summary(dt_from, dt_to)
        self._load_chart(dt_from, dt_to)
        self._load_payment_methods(dt_from, dt_to)
        self._load_top_products(dt_from, dt_to)

    def _load_summary(self, dt_from, dt_to):
        with db.get_session() as session:
            total_penjualan = session.query(
                func.coalesce(func.sum(Transaksi.total), 0)
            ).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).scalar() or 0

            jumlah_transaksi = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).count()

            total_qty = session.query(
                func.coalesce(func.sum(TransaksiDetail.qty), 0)
            ).join(
                Transaksi, TransaksiDetail.transaksi_id == Transaksi.id
            ).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).scalar() or 0

        rata = total_penjualan // max(jumlah_transaksi, 1)

        self.card_pendapatan._val_lbl.setText(format_rupiah(total_penjualan))
        self.card_transaksi._val_lbl.setText(f"{jumlah_transaksi} Transaksi")
        self.card_rata._val_lbl.setText(format_rupiah(rata))
        self.card_terjual._val_lbl.setText(f"{int(total_qty):,} Unit")

    def _load_chart(self, dt_from, dt_to):
        """Load revenue data for bar chart with smart binning based on selected period"""
        from collections import defaultdict

        with db.get_session() as session:
            trans = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).all()

        period = self._current_period

        if period == "hari_ini":
            # 7 time slots like reference mockup (08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00)
            slots = [8, 10, 12, 14, 16, 18, 20]
            slot_data = {s: 0.0 for s in slots}

            for t in trans:
                h = t.tanggal.hour
                # Map to 2-hour bracket
                if h < 9:
                    bracket = 8
                elif h < 11:
                    bracket = 10
                elif h < 13:
                    bracket = 12
                elif h < 15:
                    bracket = 14
                elif h < 17:
                    bracket = 16
                elif h < 19:
                    bracket = 18
                else:
                    bracket = 20
                slot_data[bracket] += float(t.total)

            data = [(f"{s:02d}:00", slot_data[s]) for s in slots]
            if hasattr(self, "chart_sub"):
                self.chart_sub.setText("Tren penjualan per jam hari ini")

        elif period == "minggu_ini":
            # 7 days: Senin - Minggu
            days_label = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            day_data = {i: 0.0 for i in range(7)}

            for t in trans:
                weekday = t.tanggal.weekday()  # 0=Monday, 6=Sunday
                day_data[weekday] += float(t.total)

            data = [(days_label[i], day_data[i]) for i in range(7)]
            if hasattr(self, "chart_sub"):
                self.chart_sub.setText("Tren penjualan harian minggu ini")

        elif period == "bulan_ini":
            # 5 date brackets for the month
            brackets = [
                ("1-6", 1, 6),
                ("7-12", 7, 12),
                ("13-18", 13, 18),
                ("19-24", 19, 24),
                ("25-31", 25, 31)
            ]
            bracket_data = {b[0]: 0.0 for b in brackets}
            for t in trans:
                d = t.tanggal.day
                for label, start, end in brackets:
                    if start <= d <= end:
                        bracket_data[label] += float(t.total)
                        break

            data = [(b[0], bracket_data[b[0]]) for b in brackets]
            if hasattr(self, "chart_sub"):
                self.chart_sub.setText("Tren penjualan periode tanggal bulan ini")

        else:  # kustom
            days_diff = (dt_to.date() - dt_from.date()).days
            if days_diff <= 1:
                slots = [8, 10, 12, 14, 16, 18, 20]
                slot_data = {s: 0.0 for s in slots}
                for t in trans:
                    h = t.tanggal.hour
                    bracket = min(20, max(8, (h // 2) * 2))
                    slot_data[bracket] += float(t.total)
                data = [(f"{s:02d}:00", slot_data[s]) for s in slots]
            elif days_diff <= 14:
                # Group by day
                curr = dt_from.date()
                day_data = defaultdict(float)
                for t in trans:
                    day_data[t.tanggal.strftime("%d/%m")] += float(t.total)
                data = []
                while curr <= dt_to.date():
                    key = curr.strftime("%d/%m")
                    data.append((key, day_data[key]))
                    curr += timedelta(days=1)
            else:
                # Weekly summary
                curr = dt_from.date()
                week_idx = 1
                data = []
                while curr <= dt_to.date():
                    next_w = curr + timedelta(days=6)
                    w_total = sum(float(t.total) for t in trans if curr <= t.tanggal.date() <= next_w)
                    data.append((f"Mgg {week_idx}", w_total))
                    curr += timedelta(days=7)
                    week_idx += 1

            if hasattr(self, "chart_sub"):
                self.chart_sub.setText("Tren penjualan periode kustom")

        self.bar_chart.set_data(data)

    def _load_payment_methods(self, dt_from, dt_to):
        from collections import defaultdict

        with db.get_session() as session:
            trans = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).all()

            metode_count = defaultdict(int)
            metode_total = defaultdict(float)
            for t in trans:
                m = t.metode_bayar.title()
                metode_count[m] += 1
                metode_total[m] += float(t.total)

        total_trans = sum(metode_count.values()) or 1

        # Clear old rows
        while self._payment_rows_layout.count():
            item = self._payment_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        METHOD_COLORS = {
            "Qris": "#3B82F6",
            "Tunai": "#10B981",
            "Cash": "#10B981",
            "Debit": "#F59E0B",
            "Kartu Debit": "#F59E0B",
            "Kredit": "#EF4444",
        }

        for metode, count in sorted(metode_count.items(), key=lambda x: -x[1]):
            pct = int(count * 100 / total_trans)
            color = METHOD_COLORS.get(metode, "#8B5CF6")
            total_val = metode_total[metode]

            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_l = QVBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(4)

            top_row = QHBoxLayout()
            name_lbl = QLabel(f"● {metode}")
            name_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600; background: transparent;")
            top_row.addWidget(name_lbl)
            top_row.addStretch()
            pct_lbl = QLabel(f"{pct}% ({format_rupiah_short(total_val)})")
            pct_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
            top_row.addWidget(pct_lbl)
            row_l.addLayout(top_row)

            # Progress bar
            is_dark = (db.get_setting("app_theme", "dark") == "dark")
            bar_bg_color = "#2D3250" if is_dark else "#E2E8F0"
            text_muted = "#94A3B8" if is_dark else "#64748B"
            pct_lbl.setStyleSheet(f"color: {text_muted}; font-size: 11px; background: transparent;")

            bar_bg = QFrame()
            bar_bg.setFixedHeight(6)
            bar_bg.setStyleSheet(f"background-color: {bar_bg_color}; border-radius: 3px;")
            bar_fill = QFrame(bar_bg)
            bar_fill.setFixedHeight(6)
            bar_fill.setFixedWidth(max(4, int(pct * 2.2)))
            bar_fill.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            row_l.addWidget(bar_bg)

            self._payment_rows_layout.addWidget(row_w)

        is_dark = (db.get_setting("app_theme", "dark") == "dark")
        text_muted = "#94A3B8" if is_dark else "#64748B"
        total_label = f"Total Metode: {len(metode_count)}    {int(sum(metode_count.values()))} Transaksi"
        self.total_metode_lbl.setText(total_label)
        self.total_metode_lbl.setStyleSheet(f"color: {text_muted}; font-size: 11px; background: transparent;")

    def _load_top_products(self, dt_from, dt_to):
        with db.get_session() as session:
            results = session.query(
                TransaksiDetail.nama_barang,
                TransaksiDetail.barang_id,
                func.sum(TransaksiDetail.qty).label("total_qty"),
                func.sum(TransaksiDetail.subtotal).label("total_revenue"),
                func.count(TransaksiDetail.id).label("count"),
                func.avg(TransaksiDetail.harga).label("avg_harga"),
            ).join(
                Transaksi, TransaksiDetail.transaksi_id == Transaksi.id
            ).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).group_by(TransaksiDetail.nama_barang, TransaksiDetail.barang_id
            ).order_by(func.sum(TransaksiDetail.subtotal).desc()
            ).limit(20).all()

            # Get kategori
            barang_ids = [r.barang_id for r in results if r.barang_id]
            kategori_map = {}
            if barang_ids:
                barangs = session.query(Barang).filter(Barang.id.in_(barang_ids)).all()
                kategori_map = {b.id: b.kategori for b in barangs}

        self._product_data = []
        self.product_table.clearContents()
        self.product_table.setRowCount(0)
        self.product_table.setRowCount(len(results))
        is_dark = (db.get_setting("app_theme", "dark") == "dark")
        text_primary = "#F1F5F9" if is_dark else "#1E293B"
        text_muted = "#94A3B8" if is_dark else "#64748B"

        TERJUAL_COLORS_DARK = ["#14532D", "#1E3A5F", "#4C1D95", "#7C3D12", "#7F1D1D"]
        TERJUAL_TEXT_DARK = ["#86EFAC", "#93C5FD", "#C4B5FD", "#FDE047", "#FCA5A5"]
        TERJUAL_COLORS_LIGHT = ["#DCFCE7", "#EFF6FF", "#F3E8FF", "#FEF3C7", "#FEE2E2"]
        TERJUAL_TEXT_LIGHT = ["#15803D", "#1D4ED8", "#6D28D9", "#B45309", "#B91C1C"]
        TERJUAL_BORDER_LIGHT = ["#BBF7D0", "#BFDBFE", "#DDD6FE", "#FDE68A", "#FECACA"]

        for row, r in enumerate(results):
            self.product_table.setRowHeight(row, 52)

            kat = kategori_map.get(r.barang_id, "-") or "-"
            self._product_data.append({
                "rank": row + 1,
                "nama": r.nama_barang,
                "kategori": kat,
                "total_qty": int(r.total_qty),
                "count": r.count,
                "avg_harga": r.avg_harga or 0,
                "revenue": r.total_revenue,
            })

            # No
            no_item = QTableWidgetItem(str(row + 1))
            no_item.setForeground(QColor(text_muted))
            no_item.setTextAlignment(Qt.AlignCenter)
            self.product_table.setItem(row, 0, no_item)

            # Nama Produk (with thumbnail)
            prod_widget = QWidget()
            prod_widget.setStyleSheet("background: transparent;")
            prod_l = QHBoxLayout(prod_widget)
            prod_l.setContentsMargins(8, 4, 8, 4)
            prod_l.setSpacing(10)

            thumb = QLabel(self._get_emoji(r.nama_barang, kat))
            thumb.setFixedSize(34, 34)
            thumb.setAlignment(Qt.AlignCenter)
            icon_bg = "#21263A" if is_dark else "#F1F5F9"
            thumb.setStyleSheet(f"background-color: {icon_bg}; border-radius: 8px; font-size: 16px;")
            prod_l.addWidget(thumb)

            name_lbl = QLabel(r.nama_barang)
            name_lbl.setStyleSheet(f"color: {text_primary}; font-weight: 600; font-size: 13px; background: transparent;")
            prod_l.addWidget(name_lbl)
            prod_l.addStretch()
            self.product_table.setCellWidget(row, 1, prod_widget)

            # Kategori
            kat_item = QTableWidgetItem(kat)
            kat_item.setForeground(QColor(text_muted))
            self.product_table.setItem(row, 2, kat_item)

            # Terjual (badge)
            terjual_widget = QWidget()
            terjual_widget.setStyleSheet("background: transparent;")
            tj_l = QHBoxLayout(terjual_widget)
            tj_l.setContentsMargins(4, 2, 4, 2)
            tj_l.setAlignment(Qt.AlignCenter)
            if is_dark:
                badge_bg = TERJUAL_COLORS_DARK[row % len(TERJUAL_COLORS_DARK)]
                badge_fg = TERJUAL_TEXT_DARK[row % len(TERJUAL_TEXT_DARK)]
                badge_border = badge_bg
            else:
                badge_bg = TERJUAL_COLORS_LIGHT[row % len(TERJUAL_COLORS_LIGHT)]
                badge_fg = TERJUAL_TEXT_LIGHT[row % len(TERJUAL_TEXT_LIGHT)]
                badge_border = TERJUAL_BORDER_LIGHT[row % len(TERJUAL_BORDER_LIGHT)]
            terjual_lbl = QLabel(f"● {int(r.total_qty)} Unit")
            terjual_lbl.setWordWrap(False)
            terjual_lbl.setFixedHeight(24)
            terjual_lbl.setMinimumWidth(80)
            terjual_lbl.setAlignment(Qt.AlignCenter)
            terjual_lbl.setStyleSheet(f"background-color: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_border}; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 700; white-space: nowrap;")
            tj_l.addWidget(terjual_lbl)
            self.product_table.setCellWidget(row, 3, terjual_widget)

            # Harga Satuan
            harga_item = QTableWidgetItem(format_rupiah(r.avg_harga or 0))
            harga_item.setForeground(QColor(text_primary))
            self.product_table.setItem(row, 4, harga_item)

            # Total Pendapatan
            rev_item = QTableWidgetItem(format_rupiah(r.total_revenue))
            rev_item.setForeground(QColor("#10B981"))
            rev_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.product_table.setItem(row, 5, rev_item)

        total = len(results)
        self.produk_info_lbl.setText(f"Menampilkan 1-{min(total, 5)} dari {total} produk")

    def _get_emoji(self, nama: str, kat: str) -> str:
        n = (nama or "").lower()
        k = (kat or "").lower()
        if "kopi" in n: return "☕"
        if "croissant" in n or "roti" in n: return "🥐"
        if "teh" in n or "matcha" in n: return "🍵"
        if "coklat" in n or "chocolate" in n: return "🍫"
        if "lemon" in n: return "🍋"
        if "air" in n or "mineral" in n: return "💧"
        if "minuman" in k: return "🧋"
        if "makanan" in k: return "🍱"
        if "jajanan" in k: return "🍟"
        return "📦"

    # =========================================================================
    # Export Excel
    # =========================================================================
    # =========================================================================
    # Export Excel & CSV
    # =========================================================================
    def _export_excel(self):
        if self._dt_from is None:
            self._load_all()

        parent_w = self.window() if hasattr(self, "window") else None

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(parent_w, "Error",
                "Library openpyxl tidak ditemukan.\nJalankan: pip install openpyxl")
            return

        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(default_dir, exist_ok=True)
        default_filename = f"laporan_penjualan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(default_dir, default_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            parent_w,
            "Simpan Laporan Excel",
            default_path,
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if not filepath:
            return

        try:
            store_name = db.get_setting("store_name", "KasirKu")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Laporan Penjualan"

            # Title & Subtitle
            ws.cell(1, 1, store_name).font = Font(bold=True, size=16, color="1E293B")
            period_str = f"Periode: {self._dt_from.strftime('%d/%m/%Y')} s/d {self._dt_to.strftime('%d/%m/%Y')}"
            ws.cell(2, 1, period_str).font = Font(size=11, italic=True, color="64748B")
            ws.cell(3, 1, f"Dicetak pada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}").font = Font(size=9, color="94A3B8")

            # Border styles
            thin_border = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            # Table Headers
            headers = ["No", "Nama Produk", "Kategori", "Terjual (Qty)", "Harga Rata-rata", "Total Pendapatan"]
            header_row = 5
            for col_idx, h in enumerate(headers, 1):
                c = ws.cell(header_row, col_idx, h)
                c.font = Font(bold=True, color="FFFFFF", size=10)
                c.fill = PatternFill("solid", fgColor="2563EB")
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.border = thin_border
            ws.row_dimensions[header_row].height = 24

            total_qty_sum = 0
            total_rev_sum = 0

            # Data rows
            for idx, p in enumerate(self._product_data, start=header_row + 1):
                c1 = ws.cell(idx, 1, p.get("rank", idx - header_row))
                c1.alignment = Alignment(horizontal="center")

                c2 = ws.cell(idx, 2, p.get("nama", "-"))

                c3 = ws.cell(idx, 3, p.get("kategori", "-"))
                c3.alignment = Alignment(horizontal="center")

                qty = p.get("total_qty", 0)
                c4 = ws.cell(idx, 4, qty)
                c4.alignment = Alignment(horizontal="right")
                c4.number_format = "#,##0"
                total_qty_sum += qty

                avg = p.get("avg_harga", 0)
                c5 = ws.cell(idx, 5, avg)
                c5.alignment = Alignment(horizontal="right")
                c5.number_format = "#,##0"

                rev = p.get("revenue", 0)
                c6 = ws.cell(idx, 6, rev)
                c6.alignment = Alignment(horizontal="right")
                c6.number_format = "#,##0"
                total_rev_sum += rev

                for col in range(1, 7):
                    ws.cell(idx, col).border = thin_border

            # Summary row
            sum_row = header_row + len(self._product_data) + 1
            ws.cell(sum_row, 1, "").border = thin_border
            ws.cell(sum_row, 2, "TOTAL").font = Font(bold=True)
            ws.cell(sum_row, 2).alignment = Alignment(horizontal="right")
            ws.cell(sum_row, 2).border = thin_border
            ws.cell(sum_row, 3, "").border = thin_border

            c_tot_qty = ws.cell(sum_row, 4, total_qty_sum)
            c_tot_qty.font = Font(bold=True)
            c_tot_qty.alignment = Alignment(horizontal="right")
            c_tot_qty.number_format = "#,##0"
            c_tot_qty.border = thin_border

            ws.cell(sum_row, 5, "").border = thin_border

            c_tot_rev = ws.cell(sum_row, 6, total_rev_sum)
            c_tot_rev.font = Font(bold=True)
            c_tot_rev.alignment = Alignment(horizontal="right")
            c_tot_rev.number_format = "#,##0"
            c_tot_rev.border = thin_border

            for col in range(1, 7):
                ws.cell(sum_row, col).fill = PatternFill("solid", fgColor="F1F5F9")

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row < header_row:
                        continue
                    if cell.value:
                        val_str = str(cell.value)
                        max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(filepath)

            reply = QMessageBox.information(
                parent_w,
                "Export Berhasil",
                f"Laporan Excel berhasil disimpan ke:\n{filepath}\n\nApakah Anda ingin membuka folder penyimpanan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                try:
                    os.startfile(os.path.dirname(filepath))
                except Exception:
                    pass

        except PermissionError:
            QMessageBox.critical(
                parent_w,
                "File Sedang Digunakan",
                f"Tidak dapat menyimpan file karena file sedang dibuka oleh program lain (seperti Excel).\n"
                f"Silakan tutup file '{os.path.basename(filepath)}' lalu coba lagi."
            )
        except Exception as e:
            QMessageBox.critical(parent_w, "Error Export", f"Gagal mengekspor laporan:\n{e}")

    def _export_csv(self):
        if self._dt_from is None:
            self._load_all()

        parent_w = self.window() if hasattr(self, "window") else None

        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(default_dir, exist_ok=True)
        default_filename = f"laporan_penjualan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        default_path = os.path.join(default_dir, default_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            parent_w,
            "Simpan Laporan CSV",
            default_path,
            "CSV Files (*.csv);;All Files (*)"
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["No", "Nama Produk", "Kategori", "Terjual", "Harga Satuan", "Total Pendapatan"])
                for p in self._product_data:
                    writer.writerow([
                        p.get("rank", ""),
                        p.get("nama", ""),
                        p.get("kategori", ""),
                        p.get("total_qty", 0),
                        p.get("avg_harga", 0),
                        p.get("revenue", 0)
                    ])

            reply = QMessageBox.information(
                parent_w,
                "Export Berhasil",
                f"Laporan CSV berhasil disimpan ke:\n{filepath}\n\nApakah Anda ingin membuka folder penyimpanan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                try:
                    os.startfile(os.path.dirname(filepath))
                except Exception:
                    pass

        except PermissionError:
            QMessageBox.critical(
                parent_w,
                "File Sedang Digunakan",
                f"Tidak dapat menyimpan file karena file sedang dibuka oleh program lain.\n"
                f"Silakan tutup file '{os.path.basename(filepath)}' lalu coba lagi."
            )
        except Exception as e:
            QMessageBox.critical(parent_w, "Error Export CSV", f"Gagal mengekspor CSV:\n{e}")

    def refresh(self):
        self._load_all()

    def on_theme_changed(self, theme: str):
        """Update chart, buttons, and table colors on theme change"""
        is_dark = (theme == "dark")
        for card in [self.card_pendapatan, self.card_transaksi, self.card_rata, self.card_terjual]:
            self._apply_stat_card_style(card)
        for k, btn in self._period_buttons.items():
            btn.setObjectName("period_tab_active" if k == self._current_period else "period_tab")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if hasattr(self, "bar_chart"):
            self.bar_chart.update()
        if hasattr(self, "produk_search"):
            bg = "#21263A" if is_dark else "#F1F5F9"
            color = "#94A3B8" if is_dark else "#64748B"
            border = "1px solid #2D3250" if is_dark else "1px solid #E2E8F0"
            self.produk_search.setStyleSheet(f"color: {color}; font-size: 12px; background: {bg}; border: {border}; border-radius: 6px; padding: 6px 12px;")
        self._load_all()
