"""
KasirKu Laporan Page
Halaman laporan dan analitik
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QMessageBox, QDateEdit, QSizePolicy,
    QScrollArea
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

from sqlalchemy import func
from database.db import db
from database.models import Transaksi, TransaksiDetail, Pengeluaran, Barang
from utils.helpers import (
    format_rupiah, format_tanggal, format_datetime,
    get_today_range, get_month_range
)
from datetime import datetime, date
import os
import csv


class LaporanPage(QWidget):
    """Halaman laporan"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("📊 Laporan & Analitik")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #F1F5F9;")
        header.addWidget(title)
        header.addStretch()

        # Period filter
        period_lbl = QLabel("Periode:")
        period_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        header.addWidget(period_lbl)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["Hari Ini", "7 Hari Terakhir", "30 Hari Terakhir",
                                    "Bulan Ini", "Bulan Lalu", "Custom"])
        self.period_combo.setFixedHeight(38)
        self.period_combo.setFixedWidth(160)
        self.period_combo.setStyleSheet("""
            QComboBox {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 10px; color: #F1F5F9; font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background: #21263A; selection-background-color: #6C63FF;
            }
        """)
        self.period_combo.currentTextChanged.connect(self._on_period_changed)
        header.addWidget(self.period_combo)

        date_style = """
            QDateEdit {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 10px; color: #F1F5F9; font-size: 13px;
            }
        """
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setFixedHeight(38)
        self.date_from.setStyleSheet(date_style)
        self.date_from.hide()
        header.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedHeight(38)
        self.date_to.setStyleSheet(date_style)
        self.date_to.hide()
        header.addWidget(self.date_to)

        btn_load = QPushButton("📊 Tampilkan")
        btn_load.setFixedHeight(38)
        btn_load.setStyleSheet("""
            QPushButton {
                background: #6C63FF; color: white;
                border: none; border-radius: 8px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover { background: #8B84FF; }
        """)
        btn_load.clicked.connect(self._load_all)
        header.addWidget(btn_load)

        btn_export = QPushButton("📤 Export")
        btn_export.setFixedHeight(38)
        btn_export.setStyleSheet("""
            QPushButton {
                background: #21263A; color: #94A3B8;
                border: 1px solid #2D3250; border-radius: 8px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover { background: #2A2F45; color: #F1F5F9; }
        """)
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)
        layout.addLayout(header)

        # Summary cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        def stat_card(title, color="#6C63FF"):
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #1A1D27; border: 1px solid #2D3250;
                    border-radius: 10px; border-left: 3px solid {color};
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(16, 12, 16, 12)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
            fl.addWidget(t_lbl)
            v_lbl = QLabel("Rp 0")
            v_lbl.setStyleSheet(f"color: #F1F5F9; font-size: 18px; font-weight: 800; background: transparent;")
            fl.addWidget(v_lbl)
            return frame, v_lbl

        c1, self.total_penjualan_lbl = stat_card("Total Penjualan", "#10B981")
        c2, self.total_pengeluaran_lbl = stat_card("Total Pengeluaran", "#EF4444")
        c3, self.laba_bersih_lbl = stat_card("Laba Bersih", "#6C63FF")
        c4, self.jumlah_transaksi_lbl = stat_card("Jumlah Transaksi", "#F59E0B")
        c4.findChildren(QLabel)[1].setText("0")  # Initial value

        for card in [c1, c2, c3, c4]:
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background: #1A1D27; border: 1px solid #2D3250;
                border-radius: 10px; margin-top: -1px;
            }
            QTabBar::tab {
                background: #21263A; color: #94A3B8;
                padding: 10px 20px; border: 1px solid #2D3250;
                border-bottom: none; border-radius: 8px 8px 0 0; margin-right: 2px;
            }
            QTabBar::tab:selected { background: #6C63FF; color: white; border-color: #6C63FF; }
            QTabBar::tab:hover:!selected { background: #2A2F45; color: #F1F5F9; }
        """)

        # Tab 1: Rekap harian
        tab_harian = self._create_daily_tab()
        self.tabs.addTab(tab_harian, "📅 Rekap Harian")

        # Tab 2: Top produk
        tab_produk = self._create_product_tab()
        self.tabs.addTab(tab_produk, "🏆 Top Produk")

        # Tab 3: Rekap pengeluaran
        tab_expense = self._create_expense_tab()
        self.tabs.addTab(tab_expense, "💸 Rekap Pengeluaran")

        layout.addWidget(self.tabs)

    def _create_daily_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(5)
        self.daily_table.setHorizontalHeaderLabels(
            ["Tanggal", "Transaksi", "Pemasukan", "Pengeluaran", "Laba"]
        )
        self.daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.daily_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.daily_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.daily_table.verticalHeader().setVisible(False)
        self.daily_table.setAlternatingRowColors(True)
        self.daily_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; gridline-color: #2D3250; alternate-background-color: #1E2235; }
            QTableWidget::item { padding: 10px; color: #F1F5F9; }
            QTableWidget::item:selected { background: #2A2F45; }
            QHeaderView::section {
                background: #21263A; color: #94A3B8;
                padding: 10px; font-size: 11px; font-weight: 600;
                border: none; border-bottom: 2px solid #2D3250;
            }
        """)
        layout.addWidget(self.daily_table)
        return w

    def _create_product_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(4)
        self.product_table.setHorizontalHeaderLabels(
            ["Nama Barang", "Total Terjual", "Total Qty", "Revenue"]
        )
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setStyleSheet(self.daily_table.styleSheet() if hasattr(self, "daily_table") else "")
        layout.addWidget(self.product_table)
        return w

    def _create_expense_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        self.expense_table = QTableWidget()
        self.expense_table.setColumnCount(3)
        self.expense_table.setHorizontalHeaderLabels(
            ["Kategori Pengeluaran", "Jumlah Transaksi", "Total Nominal"]
        )
        self.expense_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.expense_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.expense_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.expense_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.expense_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.expense_table.verticalHeader().setVisible(False)
        self.expense_table.setAlternatingRowColors(True)
        self.expense_table.setStyleSheet("""
            QTableWidget { background: transparent; border: none; gridline-color: #2D3250; alternate-background-color: #1E2235; }
            QTableWidget::item { padding: 10px; color: #F1F5F9; }
            QTableWidget::item:selected { background: #2A2F45; }
            QHeaderView::section {
                background: #21263A; color: #94A3B8;
                padding: 10px; font-size: 11px; font-weight: 600;
                border: none; border-bottom: 2px solid #2D3250;
            }
        """)
        layout.addWidget(self.expense_table)
        return w

    def _on_period_changed(self, period: str):
        if period == "Custom":
            self.date_from.show()
            self.date_to.show()
        else:
            self.date_from.hide()
            self.date_to.hide()

    def _get_date_range(self):
        period = self.period_combo.currentText()
        today = date.today()

        if period == "Hari Ini":
            return datetime.combine(today, datetime.min.time()), datetime.combine(today, datetime.max.time())
        elif period == "7 Hari Terakhir":
            from datetime import timedelta
            start = today - timedelta(days=6)
            return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
        elif period == "30 Hari Terakhir":
            from datetime import timedelta
            start = today - timedelta(days=29)
            return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
        elif period == "Bulan Ini":
            return get_month_range()
        elif period == "Bulan Lalu":
            if today.month == 1:
                return get_month_range(today.year - 1, 12)
            return get_month_range(today.year, today.month - 1)
        else:  # Custom
            d_from = self.date_from.date().toPyDate()
            d_to = self.date_to.date().toPyDate()
            return datetime.combine(d_from, datetime.min.time()), datetime.combine(d_to, datetime.max.time())

    def _load_all(self):
        dt_from, dt_to = self._get_date_range()
        self._dt_from = dt_from
        self._dt_to = dt_to
        self._load_summary(dt_from, dt_to)
        self._load_daily(dt_from, dt_to)
        self._load_top_products(dt_from, dt_to)
        self._load_expense_recap(dt_from, dt_to)

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

            total_pengeluaran = session.query(
                func.coalesce(func.sum(Pengeluaran.nominal), 0)
            ).filter(
                Pengeluaran.tanggal >= dt_from,
                Pengeluaran.tanggal <= dt_to
            ).scalar() or 0

        laba = total_penjualan - total_pengeluaran
        self.total_penjualan_lbl.setText(format_rupiah(total_penjualan))
        self.total_pengeluaran_lbl.setText(format_rupiah(total_pengeluaran))
        self.laba_bersih_lbl.setText(format_rupiah(laba))
        self.laba_bersih_lbl.setStyleSheet(
            f"color: {'#10B981' if laba >= 0 else '#EF4444'}; font-size: 18px; font-weight: 800; background: transparent;"
        )
        self.jumlah_transaksi_lbl.setText(str(jumlah_transaksi))

    def _load_daily(self, dt_from, dt_to):
        from datetime import timedelta
        from collections import defaultdict

        with db.get_session() as session:
            trans = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).all()

            penjualan_by_date = defaultdict(lambda: {"count": 0, "total": 0})
            for t in trans:
                d = t.tanggal.date()
                penjualan_by_date[d]["count"] += 1
                penjualan_by_date[d]["total"] += t.total

            expenses = session.query(Pengeluaran).filter(
                Pengeluaran.tanggal >= dt_from,
                Pengeluaran.tanggal <= dt_to
            ).all()
            expense_by_date = defaultdict(float)
            for e in expenses:
                expense_by_date[e.tanggal.date()] += e.nominal

        all_dates = sorted(set(list(penjualan_by_date.keys()) + list(expense_by_date.keys())), reverse=True)

        self.daily_table.setRowCount(len(all_dates))
        for row, d in enumerate(all_dates):
            self.daily_table.setRowHeight(row, 44)
            penjualan = penjualan_by_date[d]["total"]
            count = penjualan_by_date[d]["count"]
            pengeluaran = expense_by_date[d]
            laba = penjualan - pengeluaran

            items = [
                (d.strftime("%d/%m/%Y (%A)"), "#94A3B8"),
                (str(count), "#6C63FF"),
                (format_rupiah(penjualan), "#10B981"),
                (format_rupiah(pengeluaran), "#EF4444"),
                (format_rupiah(laba), "#10B981" if laba >= 0 else "#EF4444"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                self.daily_table.setItem(row, col, item)

    def _load_top_products(self, dt_from, dt_to):
        with db.get_session() as session:
            results = session.query(
                TransaksiDetail.nama_barang,
                func.sum(TransaksiDetail.qty).label("total_qty"),
                func.sum(TransaksiDetail.subtotal).label("total_revenue"),
                func.count(TransaksiDetail.id).label("count")
            ).join(
                Transaksi, TransaksiDetail.transaksi_id == Transaksi.id
            ).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to,
                Transaksi.status == "selesai"
            ).group_by(TransaksiDetail.nama_barang).order_by(
                func.sum(TransaksiDetail.subtotal).desc()
            ).limit(20).all()

        self.product_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.product_table.setRowHeight(row, 44)
            rank = f"#{row+1} {r.nama_barang}"
            items = [
                (rank, "#F1F5F9"),
                (str(r.count), "#6C63FF"),
                (f"{int(r.total_qty)} unit", "#94A3B8"),
                (format_rupiah(r.total_revenue), "#10B981"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                self.product_table.setItem(row, col, item)

    def _load_expense_recap(self, dt_from, dt_to):
        with db.get_session() as session:
            results = session.query(
                Pengeluaran.kategori,
                func.count(Pengeluaran.id).label("count"),
                func.sum(Pengeluaran.nominal).label("total")
            ).filter(
                Pengeluaran.tanggal >= dt_from,
                Pengeluaran.tanggal <= dt_to
            ).group_by(Pengeluaran.kategori).order_by(
                func.sum(Pengeluaran.nominal).desc()
            ).all()

        self.expense_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.expense_table.setRowHeight(row, 44)
            items = [
                (r.kategori or "-", "#F1F5F9"),
                (str(r.count), "#6C63FF"),
                (format_rupiah(r.total), "#EF4444"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                self.expense_table.setItem(row, col, item)

    def _export_csv(self):
        try:
            filename = f"laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(os.path.expanduser("~"), "Downloads", filename)
            dt_from, dt_to = self._get_date_range()

            with db.get_session() as session:
                trans = session.query(Transaksi).filter(
                    Transaksi.tanggal >= dt_from,
                    Transaksi.tanggal <= dt_to,
                    Transaksi.status == "selesai"
                ).order_by(Transaksi.tanggal.desc()).all()

                with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Invoice", "Tanggal", "Kasir", "Metode", "Total", "Status"])
                    for t in trans:
                        writer.writerow([
                            t.no_invoice,
                            format_datetime(t.tanggal),
                            t.kasir.username if t.kasir else "-",
                            t.metode_bayar,
                            t.total,
                            t.status
                        ])

            QMessageBox.information(self, "Export Berhasil",
                                    f"Laporan berhasil diekspor ke:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error Export", str(e))

    def refresh(self):
        self._load_all()
