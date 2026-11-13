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
    QScrollArea, QMenu, QAction, QToolTip, QFileDialog, QStyle,
    QStyleOptionHeader
)
from PyQt5.QtCore import Qt, QDate, QSize, QPoint, QRectF
from PyQt5.QtGui import (
    QColor, QFont, QCursor, QPainter, QPen, QBrush, QLinearGradient,
    QPainterPath
)

from sqlalchemy import func
from database.db import db
from database.models import Transaksi, TransaksiDetail, Pengeluaran, Barang, Pembelian
from ui.dashboard import _rgba
from utils.helpers import (
    format_rupiah, format_rupiah_short, format_tanggal, format_datetime,
    get_today_range, get_month_range, get_pembelian_status_display
)
from datetime import datetime, date, timedelta
import os
import csv
import math


def aggregate_intraday_revenue(transactions):
    """Jumlahkan pendapatan per menit transaksi dan urutkan menurut waktu."""
    from collections import defaultdict

    minute_totals = defaultdict(float)
    for transaction in transactions:
        minute = transaction.tanggal.strftime("%H:%M")
        minute_totals[minute] += float(transaction.total or 0)
    return sorted(minute_totals.items())


class ProductTableHeader(QHeaderView):
    """Tempatkan judul nama produk sejajar dengan area thumbnail dan nama."""

    def paintSection(self, painter, rect, logical_index):
        if logical_index != 1:
            super().paintSection(painter, rect, logical_index)
            return

        option = QStyleOptionHeader()
        option.initFrom(self)
        option.rect = rect
        option.section = logical_index
        option.orientation = self.orientation()
        option.text = str(
            self.model().headerData(logical_index, self.orientation(), Qt.DisplayRole)
        )
        option.textAlignment = Qt.AlignLeft | Qt.AlignVCenter
        option.position = QStyleOptionHeader.Middle

        self.style().drawControl(QStyle.CE_HeaderSection, option, painter, self)
        option.rect = rect.adjusted(52, 0, 0, 0)
        self.style().drawControl(QStyle.CE_HeaderLabel, option, painter, self)


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
        self._time_axis = False
        self._hover_idx = -1
        self._bar_rects = []  # list of (QRectF, label, val)
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_data(self, data: list, time_axis: bool = False):
        """data: list of (label_str, numeric_value), optionally on a clock-time axis."""
        self._data = data
        self._time_axis = time_axis
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
        grid_color = QColor("#22283A" if is_dark else "#E5E7EB")
        axis_text_color = QColor("#94A3B8" if is_dark else "#64748B")

        # Regular bar colors (slate blue gradient)
        bar_top_normal = QColor("#465F87" if is_dark else "#6B93C2")
        bar_bot_normal = QColor("#2B3D5B" if is_dark else "#3F72AF")

        # Peak bar highlight colors (Soft light blue/indigo like reference mockup)
        bar_top_peak = QColor("#C7D2FE" if is_dark else "#1E40AF")
        bar_bot_peak = QColor("#93C5FD" if is_dark else "#3F72AF")

        hover_outline = QColor("#FFFFFF" if is_dark else "#112D4E")

        w = self.width()
        h = self.height()

        margin_l = 68   # Room for Y labels (e.g. "Rp 1.5jt")
        margin_r = 24
        margin_top = 28
        margin_bot = 58 if self._time_axis else 38

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
        time_minutes = [
            int(label[:2]) * 60 + int(label[3:5])
            for label, _ in self._data
        ] if self._time_axis else []
        if self._time_axis:
            min_data_time = min(time_minutes, default=8 * 60)
            max_data_time = max(time_minutes, default=20 * 60)
            time_start = min(8 * 60, (min_data_time // 60) * 60)
            time_end = max(20 * 60, min(24 * 60, (max_data_time // 60 + 1) * 60))
            time_span = max(1, time_end - time_start)
            hours_in_chart = time_span / 60
            tick_step = 1 if chart_w / hours_in_chart >= 55 else 2

            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QPen(axis_text_color))
            baseline_y = margin_top + chart_h
            for minute in range(time_start, time_end + 1, tick_step * 60):
                x = margin_l + (minute - time_start) / time_span * chart_w
                painter.drawLine(int(x), baseline_y, int(x), baseline_y + 4)
                hour_label = f"{(minute // 60) % 24:02d}:00"
                painter.drawText(
                    int(x - 28), baseline_y + 5, 56, 16,
                    Qt.AlignCenter, hour_label
                )

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

        if self._time_axis:
            bar_w = min(18.0, max(4.0, chart_w / time_span * 0.75))
        else:
            slot_w = chart_w / float(n)
            bar_w = min(48.0, max(14.0, slot_w * 0.56))

        for i, (label, val) in enumerate(self._data):
            if self._time_axis:
                center_x = margin_l + (
                    (time_minutes[i] - time_start) / time_span * chart_w
                )
                center_x = max(
                    margin_l + bar_w / 2,
                    min(margin_l + chart_w - bar_w / 2, center_x),
                )
            else:
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

            if not self._time_axis:
                painter.setPen(QPen(axis_text_color))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold if is_peak else QFont.Normal))
                painter.drawText(
                    int(center_x - 35), int(margin_top + chart_h + 10),
                    70, 18, Qt.AlignCenter, label
                )

        if self._time_axis:
            painter.setPen(QPen(axis_text_color))
            painter.setFont(QFont("Segoe UI", 8))
            last_label_x = float("-inf")
            for (label, _), minute in zip(self._data, time_minutes):
                center_x = margin_l + (
                    (minute - time_start) / time_span * chart_w
                )
                center_x = max(
                    margin_l + bar_w / 2,
                    min(margin_l + chart_w - bar_w / 2, center_x),
                )
                if center_x - last_label_x >= 52:
                    painter.drawText(
                        int(center_x - 28), margin_top + chart_h + 29,
                        56, 16, Qt.AlignCenter, label
                    )
                    last_label_x = center_x

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

        btn_export_tax = QPushButton("🏛️ Rekap Pajak (Excel)")
        btn_export_tax.setObjectName("btn_secondary")
        btn_export_tax.setFixedHeight(36)
        btn_export_tax.setCursor(QCursor(Qt.PointingHandCursor))
        btn_export_tax.clicked.connect(self._export_tax_excel)
        header_row.addWidget(btn_export_tax)

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

        self.card_pendapatan = self._make_stat_card("Total Penjualan", "Rp 0", "+0% dari kemarin", "📈", "#3F72AF")
        self.card_pendapatan.setToolTip(
            "Jumlah transaksi selesai, termasuk PPN. Transaksi void tidak dihitung."
        )
        self.card_transaksi = self._make_stat_card("Total Transaksi", "0 Transaksi", "+0% dari kemarin", "📋", "#10B981")
        self.card_rata = self._make_stat_card("Rata-rata Peranjang", "Rp 0", "+0% dari kemarin", "🛍", "#F59E0B")
        self.card_terjual = self._make_stat_card("Barang Terjual", "0 Unit", "+0% dari kemarin", "📦", "#8B5CF6")

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
        legend_dot.setStyleSheet("color: #3F72AF; font-size: 14px; background: transparent;")
        chart_title_row.addWidget(legend_dot)
        legend_lbl = QLabel("Pendapatan (Rp)")
        legend_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        chart_title_row.addWidget(legend_lbl)
        chart_layout.addLayout(chart_title_row)

        self.chart_sub = QLabel("Tren penjualan sesuai waktu transaksi hari ini")
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
        sep2.setStyleSheet("background: #274568;")
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
        self.produk_search.setStyleSheet("color: #64748B; font-size: 12px; background: #17324F; border-radius: 6px; padding: 6px 12px;")
        produk_header.addWidget(self.produk_search)
        produk_layout.addLayout(produk_header)

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6)
        self.product_table.setHorizontalHeader(
            ProductTableHeader(Qt.Horizontal, self.product_table)
        )
        self.product_table.setHorizontalHeaderLabels([
            "No", "Nama Produk", "Kategori", "Terjual", "Harga Satuan", "Subtotal Produk"
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

    def _make_stat_card(self, title, value, subtitle, icon, icon_color):
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
        frame._icon_frame = icon_frame
        frame._icon_color = icon_color
        self._apply_stat_card_style(frame)
        return frame

    def _apply_stat_card_style(self, frame):
        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")
        if hasattr(frame, "_icon_frame"):
            icon_alpha = 0.13 if is_dark else 0.08
            border_alpha = 0.27 if is_dark else 0.19
            frame._icon_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {_rgba(frame._icon_color, icon_alpha)};
                    border: 1px solid {_rgba(frame._icon_color, border_alpha)};
                    border-radius: 9px;
                }}
            """)
        if is_dark:
            frame.setStyleSheet("""
                QFrame#laporan_stat_card {
                    background-color: #112D4E;
                    border: 1px solid #274568;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; background: transparent;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("color: #F9FAFB; font-size: 20px; font-weight: 800; background: transparent;")
            if hasattr(frame, "_sub_lbl"):
                frame._sub_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: transparent;")
        else:
            frame.setStyleSheet("""
                QFrame#laporan_stat_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("color: #112D4E; font-size: 20px; font-weight: 800; background: transparent;")
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
            data = aggregate_intraday_revenue(trans)
            if hasattr(self, "chart_sub"):
                self.chart_sub.setText("Tren penjualan sesuai waktu transaksi hari ini")

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

        self.bar_chart.set_data(data, time_axis=period == "hari_ini")

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
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        METHOD_COLORS = {
            "Qris": "#3F72AF",
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
            bar_bg_color = "#274568" if is_dark else "#E5E7EB"
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
        text_primary = "#F9FAFB" if is_dark else "#112D4E"
        text_muted = "#94A3B8" if is_dark else "#64748B"

        TERJUAL_COLORS_DARK = ["#14532D", "#1E3A5F", "#4C1D95", "#7C3D12", "#7F1D1D"]
        TERJUAL_TEXT_DARK = ["#86EFAC", "#93C5FD", "#C4B5FD", "#FDE047", "#FCA5A5"]
        TERJUAL_COLORS_LIGHT = ["#DCFCE7", "#DBE2EF", "#F3E8FF", "#FEF3C7", "#FEE2E2"]
        TERJUAL_TEXT_LIGHT = ["#15803D", "#2F5A8C", "#6D28D9", "#B45309", "#B91C1C"]
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
            icon_bg = "#17324F" if is_dark else "#F9FAFB"
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

            # Subtotal produk sebelum pajak transaksi
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
            period_range = f"{self._dt_from.strftime('%d/%m/%Y')} s/d {self._dt_to.strftime('%d/%m/%Y')}"
            period_str = f"Periode: {period_range}"
            ws.cell(2, 1, period_str).font = Font(size=11, italic=True, color="64748B")
            ws.cell(3, 1, f"Dicetak pada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}").font = Font(size=9, color="94A3B8")

            # Border styles
            thin_border = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            headers = [
                "No", "Nama Produk", "Kategori", "Terjual (Qty)",
                "Harga Rata-rata", "Subtotal Produk"
            ]
            with db.get_session() as session:
                sales_rows = session.query(
                    func.date(Transaksi.tanggal).label("sale_date"),
                    TransaksiDetail.nama_barang,
                    TransaksiDetail.barang_id,
                    func.sum(TransaksiDetail.qty).label("total_qty"),
                    func.avg(TransaksiDetail.harga).label("avg_harga"),
                    func.sum(TransaksiDetail.subtotal).label("revenue"),
                ).join(
                    Transaksi, TransaksiDetail.transaksi_id == Transaksi.id
                ).filter(
                    Transaksi.tanggal >= self._dt_from,
                    Transaksi.tanggal <= self._dt_to,
                    Transaksi.status == "selesai"
                ).group_by(
                    func.date(Transaksi.tanggal),
                    TransaksiDetail.nama_barang,
                    TransaksiDetail.barang_id
                ).order_by(
                    func.date(Transaksi.tanggal),
                    func.sum(TransaksiDetail.subtotal).desc()
                ).all()

                daily_financials = session.query(
                    func.date(Transaksi.tanggal).label("sale_date"),
                    func.sum(Transaksi.ppn_nominal).label("ppn"),
                    func.sum(Transaksi.pph_nominal).label("pph"),
                    func.sum(Transaksi.total).label("total_sales"),
                ).filter(
                    Transaksi.tanggal >= self._dt_from,
                    Transaksi.tanggal <= self._dt_to,
                    Transaksi.status == "selesai"
                ).group_by(func.date(Transaksi.tanggal)).all()

                barang_ids = {row.barang_id for row in sales_rows if row.barang_id}
                kategori_map = {}
                if barang_ids:
                    kategori_map = {
                        barang.id: barang.kategori
                        for barang in session.query(Barang).filter(Barang.id.in_(barang_ids)).all()
                    }

            def to_date(value):
                if isinstance(value, datetime):
                    return value.date()
                if isinstance(value, date):
                    return value
                return datetime.strptime(str(value), "%Y-%m-%d").date()

            sales_by_date = {}
            for sale in sales_rows:
                sales_by_date.setdefault(to_date(sale.sale_date), []).append(sale)

            financials_by_date = {}
            for daily in daily_financials:
                sale_date = to_date(daily.sale_date)
                financials_by_date[sale_date] = daily
                sales_by_date.setdefault(sale_date, [])

            total_qty_sum = 0
            total_product_subtotal_sum = 0
            total_ppn_sum = 0
            total_pph_sum = 0
            total_sales_sum = 0
            current_row = 5
            period_title_rows = set()

            for sale_date, products in sorted(sales_by_date.items()):
                financials = financials_by_date[sale_date]
                period_title = f"Periode Penjualan: {format_tanggal(datetime.combine(sale_date, datetime.min.time()))}"
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
                period_cell = ws.cell(current_row, 1, period_title)
                period_cell.font = Font(bold=True, color="1E3A8A", size=11)
                period_cell.alignment = Alignment(vertical="center")
                period_cell.fill = PatternFill("solid", fgColor="DBEAFE")
                period_title_rows.add(current_row)
                ws.row_dimensions[current_row].height = 22
                current_row += 1

                header_row = current_row
                for col_idx, heading in enumerate(headers, 1):
                    cell = ws.cell(header_row, col_idx, heading)
                    cell.font = Font(bold=True, color="FFFFFF", size=10)
                    cell.fill = PatternFill("solid", fgColor="2563EB")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = thin_border
                ws.row_dimensions[header_row].height = 24
                current_row += 1

                daily_qty = 0
                daily_product_subtotal = 0
                for rank, product in enumerate(products, start=1):
                    ws.cell(current_row, 1, rank).alignment = Alignment(horizontal="center")
                    ws.cell(current_row, 2, product.nama_barang or "-")
                    category = kategori_map.get(product.barang_id, "-") or "-"
                    ws.cell(current_row, 3, category).alignment = Alignment(horizontal="center")

                    qty = int(product.total_qty or 0)
                    quantity_cell = ws.cell(current_row, 4, qty)
                    quantity_cell.alignment = Alignment(horizontal="right")
                    quantity_cell.number_format = "#,##0"
                    daily_qty += qty

                    average_cell = ws.cell(current_row, 5, product.avg_harga or 0)
                    average_cell.alignment = Alignment(horizontal="right")
                    average_cell.number_format = "#,##0"

                    revenue = product.revenue or 0
                    revenue_cell = ws.cell(current_row, 6, revenue)
                    revenue_cell.alignment = Alignment(horizontal="right")
                    revenue_cell.number_format = "#,##0"
                    daily_product_subtotal += revenue

                    for col in range(1, 7):
                        ws.cell(current_row, col).border = thin_border
                    current_row += 1

                total_qty_sum += daily_qty
                total_product_subtotal_sum += daily_product_subtotal
                total_ppn_sum += financials.ppn or 0
                total_pph_sum += financials.pph or 0
                total_sales_sum += financials.total_sales or 0

                total_row = current_row
                for col in range(1, 7):
                    ws.cell(total_row, col).border = thin_border
                    ws.cell(total_row, col).fill = PatternFill("solid", fgColor="F1F5F9")
                total_label = ws.cell(total_row, 2, "TOTAL HARIAN (SUBTOTAL PRODUK)")
                total_label.font = Font(bold=True)
                total_label.alignment = Alignment(horizontal="right")
                daily_qty_cell = ws.cell(total_row, 4, daily_qty)
                daily_qty_cell.font = Font(bold=True)
                daily_qty_cell.alignment = Alignment(horizontal="right")
                daily_qty_cell.number_format = "#,##0"
                subtotal_cell = ws.cell(total_row, 6, daily_product_subtotal)
                subtotal_cell.font = Font(bold=True)
                subtotal_cell.alignment = Alignment(horizontal="right")
                subtotal_cell.number_format = "#,##0"
                current_row += 1

                for label, amount, is_total in [
                    ("PPN", financials.ppn or 0, False),
                    ("PPh", financials.pph or 0, False),
                    ("TOTAL PENJUALAN", financials.total_sales or 0, True),
                ]:
                    summary_row = current_row
                    fill_color = "DBEAFE" if is_total else "F8FAFC"
                    for col in range(1, 7):
                        cell = ws.cell(summary_row, col)
                        cell.border = thin_border
                        cell.fill = PatternFill("solid", fgColor=fill_color)
                    label_cell = ws.cell(summary_row, 2, label)
                    label_cell.font = Font(bold=is_total)
                    label_cell.alignment = Alignment(horizontal="right")
                    amount_cell = ws.cell(summary_row, 6, amount)
                    amount_cell.font = Font(bold=is_total)
                    amount_cell.alignment = Alignment(horizontal="right")
                    amount_cell.number_format = "#,##0"
                    current_row += 1
                current_row += 1

            if not sales_by_date:
                ws.cell(current_row, 1, "Tidak ada transaksi penjualan pada periode ini.")
                current_row += 1

            overall_title = ws.cell(current_row, 1, f"Rekap Keseluruhan: {period_range}")
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
            overall_title.font = Font(bold=True, color="334155", size=11)
            overall_title.fill = PatternFill("solid", fgColor="E2E8F0")
            period_title_rows.add(current_row)
            current_row += 1

            summary_rows = [
                ("TOTAL SUBTOTAL PRODUK", total_product_subtotal_sum, total_qty_sum),
                ("PPN", total_ppn_sum, None),
                ("PPh", total_pph_sum, None),
                ("TOTAL PENJUALAN", total_sales_sum, None),
            ]
            for label, amount, quantity in summary_rows:
                summary_row = current_row
                is_total = label == "TOTAL PENJUALAN"
                fill_color = "CBD5E1" if is_total else "E2E8F0"
                for col in range(1, 7):
                    cell = ws.cell(summary_row, col)
                    cell.border = thin_border
                    cell.fill = PatternFill("solid", fgColor=fill_color)
                label_cell = ws.cell(summary_row, 2, label)
                label_cell.font = Font(bold=True)
                label_cell.alignment = Alignment(horizontal="right")
                if quantity is not None:
                    quantity_cell = ws.cell(summary_row, 4, quantity)
                    quantity_cell.font = Font(bold=True)
                    quantity_cell.alignment = Alignment(horizontal="right")
                    quantity_cell.number_format = "#,##0"
                amount_cell = ws.cell(summary_row, 6, amount)
                amount_cell.font = Font(bold=True)
                amount_cell.alignment = Alignment(horizontal="right")
                amount_cell.number_format = "#,##0"
                current_row += 1

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row in period_title_rows:
                        continue
                    if cell.value:
                        val_str = str(cell.value)
                        max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            # Rekap PO dan barang yang direstock pada periode laporan.
            ws_buy = wb.create_sheet("Pembelian & Restock")
            ws_buy.cell(1, 1, store_name).font = Font(bold=True, size=16, color="1E293B")
            ws_buy.cell(2, 1, period_str).font = Font(size=11, italic=True, color="64748B")
            buy_headers = ["No PO", "No Faktur Vendor", "Tanggal", "Supplier", "Nama Barang", "Qty Restock", "Harga Beli", "Subtotal Item", "Total Faktur", "Sudah Dibayar", "Sisa Hutang", "Status", "Jatuh Tempo", "Keterangan Retur"]
            for col_idx, heading in enumerate(buy_headers, 1):
                cell = ws_buy.cell(4, col_idx, heading)
                cell.font = Font(bold=True, color="FFFFFF", size=10)
                cell.fill = PatternFill("solid", fgColor="0F766E")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
            with db.get_session() as session:
                purchases = session.query(Pembelian).filter(
                    Pembelian.tanggal >= self._dt_from,
                    Pembelian.tanggal <= self._dt_to
                ).order_by(Pembelian.tanggal.asc()).all()
                buy_row = 5
                for purchase in purchases:
                    status_text, retur_note = get_pembelian_status_display(purchase)
                    details = purchase.detail or []
                    if not details:
                        details = [None]
                    for detail in details:
                        values = [
                            purchase.no_po, purchase.no_faktur, purchase.tanggal,
                            purchase.supplier.nama if purchase.supplier else "Umum",
                            detail.nama_barang if detail else "-",
                            detail.qty if detail else 0,
                            detail.harga_beli if detail else 0,
                            detail.subtotal if detail else 0,
                            purchase.total or 0, purchase.sudah_dibayar or 0,
                            max(0, (purchase.total or 0) - (purchase.sudah_dibayar or 0)),
                            status_text, purchase.jatuh_tempo, retur_note or "-"
                        ]
                        for col_idx, value in enumerate(values, 1):
                            cell = ws_buy.cell(buy_row, col_idx, value)
                            cell.border = thin_border
                            if col_idx in (3, 13) and value:
                                cell.number_format = "dd/mm/yyyy"
                            elif col_idx in (6,):
                                cell.number_format = "#,##0.##"
                            elif col_idx in (7, 8, 9, 10, 11):
                                cell.number_format = '"Rp" #,##0.00'
                            if col_idx in (6, 7, 8, 9, 10, 11):
                                cell.alignment = Alignment(horizontal="right")
                        status_cell = ws_buy.cell(buy_row, 12)
                        if purchase.retur:
                            status_cell.font = Font(color="B45309", bold=True)
                            status_cell.fill = PatternFill("solid", fgColor="FEF3C7")
                            ws_buy.cell(buy_row, 14).font = Font(color="B45309")
                            ws_buy.cell(buy_row, 14).fill = PatternFill("solid", fgColor="FEF3C7")
                        elif purchase.status_bayar in ("tempo", "cicil"):
                            status_cell.font = Font(color="DC2626", bold=True)
                            status_cell.fill = PatternFill("solid", fgColor="FEE2E2")
                        elif purchase.status_bayar == "lunas":
                            status_cell.font = Font(color="059669", bold=True)
                        buy_row += 1
            for col_idx, width in enumerate([18, 22, 18, 24, 28, 14, 18, 20, 20, 20, 20, 34, 18, 55], 1):
                ws_buy.column_dimensions[get_column_letter(col_idx)].width = width
            ws_buy.freeze_panes = "A5"
            ws_buy.auto_filter.ref = f"A4:N{max(4, buy_row - 1)}"

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
                writer.writerow([
                    "No", "Nama Produk", "Kategori", "Terjual",
                    "Harga Satuan", "Subtotal Produk"
                ])
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

    def _export_tax_excel(self):
        """Ekspor Rekapitulasi Pajak PPN Masukan, Keluaran, dan Selisih ke Excel"""
        if self._dt_from is None:
            self._load_all()

        parent_w = self.window() if hasattr(self, "window") else None
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(default_dir, exist_ok=True)
        default_filename = f"rekap_pajak_ppn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(default_dir, default_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            parent_w,
            "Simpan Rekapitulasi Pajak PPN & PPh (Excel)",
            default_path,
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if not filepath:
            return

        try:
            from services.invoice_pdf_service import InvoicePdfService
            ok = InvoicePdfService.export_tax_report_to_excel(self._dt_from, self._dt_to, filepath)
            if ok:
                reply = QMessageBox.information(
                    parent_w,
                    "Export Pajak Berhasil",
                    f"Rekapitulasi SPT Pajak (PPN & PPh) berhasil diekspor ke:\n{filepath}\n\nApakah Anda ingin membuka filenya?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    try:
                        os.startfile(filepath)
                    except Exception:
                        pass
            else:
                QMessageBox.critical(parent_w, "Error Export Pajak", "Gagal mengekspor laporan pajak ke Excel.")
        except Exception as e:
            QMessageBox.critical(parent_w, "Error Export Pajak", f"Terjadi kesalahan saat ekspor pajak:\n{e}")

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
            bg = "#17324F" if is_dark else "#F9FAFB"
            color = "#94A3B8" if is_dark else "#64748B"
            border = "1px solid #274568" if is_dark else "1px solid #E5E7EB"
            self.produk_search.setStyleSheet(f"color: {color}; font-size: 12px; background: {bg}; border: {border}; border-radius: 6px; padding: 6px 12px;")
        self._load_all()
