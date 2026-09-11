"""
KasirKu Riwayat Transaksi
Halaman riwayat dan detail transaksi
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QDialog, QDateEdit,
    QSplitter, QTextEdit, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont

from database.db import db
from database.models import Transaksi, TransaksiDetail
from auth.auth_manager import auth
from utils.helpers import format_rupiah, format_datetime, format_tanggal
from services.printer_service import PrinterService
from datetime import datetime, date, timedelta


class RiwayatTransaksiPage(QWidget):
    """Halaman riwayat transaksi"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transactions = []
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("📋 Riwayat Transaksi")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #F1F5F9;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Filters
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background: #1A1D27; border: 1px solid #2D3250; border-radius: 10px; }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari invoice / kasir...")
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 12px;
                color: #F1F5F9; font-size: 13px;
            }
            QLineEdit:focus { border-color: #6C63FF; }
        """)
        self.search_input.textChanged.connect(self._filter_data)
        filter_layout.addWidget(self.search_input, 2)

        # Date filters
        date_lbl = QLabel("Dari:")
        date_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        filter_layout.addWidget(date_lbl)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setFixedHeight(38)
        self.date_from.setStyleSheet("""
            QDateEdit {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 10px; color: #F1F5F9; font-size: 13px;
            }
        """)
        filter_layout.addWidget(self.date_from)

        date_lbl2 = QLabel("s/d:")
        date_lbl2.setStyleSheet("color: #94A3B8; font-size: 12px;")
        filter_layout.addWidget(date_lbl2)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedHeight(38)
        self.date_to.setStyleSheet(self.date_from.styleSheet())
        filter_layout.addWidget(self.date_to)

        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Semua Status", "Selesai", "Void"])
        self.status_filter.setFixedHeight(38)
        self.status_filter.setStyleSheet("""
            QComboBox {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 10px; color: #F1F5F9; font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background: #21263A; border: 1px solid #2D3250;
                selection-background-color: #6C63FF;
            }
        """)
        filter_layout.addWidget(self.status_filter)

        btn_filter = QPushButton("🔍 Filter")
        btn_filter.setFixedHeight(38)
        btn_filter.setStyleSheet("""
            QPushButton {
                background: #6C63FF; color: white;
                border: none; border-radius: 8px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover { background: #8B84FF; }
        """)
        btn_filter.clicked.connect(self._load_data)
        filter_layout.addWidget(btn_filter)

        layout.addWidget(filter_frame)

        # Stats
        self.stats_lbl = QLabel("")
        self.stats_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(self.stats_lbl)

        # Splitter: table + detail
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #2D3250; width: 1px; }")

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Invoice", "Tanggal", "Kasir", "Metode", "Total", "Status", "Aksi"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 120)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.currentItemChanged.connect(self._on_selection_changed)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1A1D27; border: 1px solid #2D3250;
                border-radius: 10px; gridline-color: #2D3250;
                alternate-background-color: #1E2235;
            }
            QTableWidget::item { padding: 10px; color: #F1F5F9; }
            QTableWidget::item:selected { background: #2A2F45; }
            QHeaderView::section {
                background: #21263A; color: #94A3B8;
                padding: 10px; font-size: 11px; font-weight: 600;
                border: none; border-bottom: 2px solid #2D3250;
            }
        """)
        splitter.addWidget(self.table)

        # Detail panel
        detail_frame = QFrame()
        detail_frame.setMinimumWidth(280)
        detail_frame.setStyleSheet("""
            QFrame { background: #1A1D27; border: 1px solid #2D3250; border-radius: 10px; }
        """)
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        detail_title = QLabel("📄 Detail Transaksi")
        detail_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F1F5F9;")
        detail_layout.addWidget(detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }
        """)
        self.detail_text.setPlaceholderText("Pilih transaksi untuk melihat detail")
        detail_layout.addWidget(self.detail_text)

        self.btn_reprint = QPushButton("🖨️ Cetak Ulang")
        self.btn_reprint.setFixedHeight(40)
        self.btn_reprint.setEnabled(False)
        self.btn_reprint.setStyleSheet("""
            QPushButton {
                background: #21263A; color: #94A3B8;
                border: 1px solid #2D3250; border-radius: 8px; font-size: 13px;
            }
            QPushButton:hover { background: #6C63FF; color: white; border-color: #6C63FF; }
            QPushButton:disabled { background: #1A1D27; color: #3D4466; }
        """)
        self.btn_reprint.clicked.connect(self._reprint)
        detail_layout.addWidget(self.btn_reprint)

        if auth.is_admin:
            self.btn_void = QPushButton("❌ Void / Batalkan")
            self.btn_void.setFixedHeight(40)
            self.btn_void.setEnabled(False)
            self.btn_void.setStyleSheet("""
                QPushButton {
                    background: #21263A; color: #EF4444;
                    border: 1px solid #EF4444; border-radius: 8px; font-size: 13px;
                }
                QPushButton:hover { background: #EF4444; color: white; }
                QPushButton:disabled { background: #1A1D27; color: #3D4466; border-color: #2D3250; }
            """)
            self.btn_void.clicked.connect(self._void_transaction)
            detail_layout.addWidget(self.btn_void)

        splitter.addWidget(detail_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._selected_invoice = None

    def _load_data(self):
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        from datetime import datetime
        dt_from = datetime.combine(date_from, datetime.min.time())
        dt_to = datetime.combine(date_to, datetime.max.time())

        with db.get_session() as session:
            query = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to
            ).order_by(Transaksi.tanggal.desc())

            trans = query.all()
            self._transactions = [
                {
                    "id": t.id,
                    "no_invoice": t.no_invoice,
                    "tanggal": t.tanggal,
                    "kasir": t.kasir.username if t.kasir else "-",
                    "metode": t.metode_bayar,
                    "total": t.total,
                    "bayar": t.bayar,
                    "kembalian": t.kembalian,
                    "status": t.status,
                    "diskon": t.diskon_total,
                }
                for t in trans
            ]

        self._filter_data()

    def _filter_data(self):
        q = self.search_input.text().lower().strip()
        status_f = self.status_filter.currentText()

        filtered = self._transactions
        if q:
            filtered = [t for t in filtered if (
                q in t["no_invoice"].lower() or q in t["kasir"].lower()
            )]
        if status_f == "Selesai":
            filtered = [t for t in filtered if t["status"] == "selesai"]
        elif status_f == "Void":
            filtered = [t for t in filtered if t["status"] == "void"]

        self._render_table(filtered)

        total_amount = sum(t["total"] for t in filtered if t["status"] == "selesai")
        self.stats_lbl.setText(
            f"{len(filtered)} transaksi · Total: {format_rupiah(total_amount)}"
        )

    def _render_table(self, data: list):
        self.table.setRowCount(len(data))
        for row, t in enumerate(data):
            self.table.setRowHeight(row, 44)

            items = [
                (t["no_invoice"], "#94A3B8"),
                (format_datetime(t["tanggal"]), "#64748B"),
                (t["kasir"], "#F1F5F9"),
                (t["metode"].upper(), "#6C63FF"),
                (format_rupiah(t["total"]), "#10B981"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                item.setData(Qt.UserRole, t["id"])
                self.table.setItem(row, col, item)

            # Status badge
            status_item = QTableWidgetItem(t["status"].upper())
            if t["status"] == "selesai":
                status_item.setForeground(QColor("#10B981"))
            else:
                status_item.setForeground(QColor("#EF4444"))
            self.table.setItem(row, 5, status_item)

            # Actions
            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 4, 4, 4)
            action_l.setSpacing(4)

            btn_detail = QPushButton("📄")
            btn_detail.setFixedSize(30, 30)
            btn_detail.setToolTip("Lihat Detail")
            btn_detail.setStyleSheet("""
                QPushButton {
                    background: #21263A; border: 1px solid #2D3250;
                    border-radius: 6px; font-size: 13px;
                }
                QPushButton:hover { background: #6C63FF; border-color: #6C63FF; }
            """)
            btn_detail.clicked.connect(lambda _, tid=t["id"]: self._show_detail(tid))
            action_l.addWidget(btn_detail)

            btn_print = QPushButton("🖨️")
            btn_print.setFixedSize(30, 30)
            btn_print.setToolTip("Cetak Ulang")
            btn_print.setStyleSheet(btn_detail.styleSheet())
            btn_print.clicked.connect(lambda _, inv=t["no_invoice"]: self._reprint_invoice(inv))
            action_l.addWidget(btn_print)

            self.table.setCellWidget(row, 6, action_w)

    def _on_selection_changed(self, current, previous):
        if current:
            tid = current.data(Qt.UserRole)
            if tid:
                self._show_detail(tid)

    def _show_detail(self, transaksi_id: int):
        with db.get_session() as session:
            t = session.query(Transaksi).filter_by(id=transaksi_id).first()
            if not t:
                return

            lines = [
                f"{'='*35}",
                f"  DETAIL TRANSAKSI",
                f"{'='*35}",
                f"Invoice  : {t.no_invoice}",
                f"Tanggal  : {format_datetime(t.tanggal)}",
                f"Kasir    : {t.kasir.username if t.kasir else '-'}",
                f"Metode   : {t.metode_bayar.upper()}",
                f"Status   : {t.status.upper()}",
                f"{'─'*35}",
                f"ITEM:",
            ]

            for d in t.detail:
                diskon_str = f" (-{d.diskon:.0f}%)" if d.diskon > 0 else ""
                lines.append(f"  {d.nama_barang}")
                lines.append(f"  {d.qty} x {format_rupiah(d.harga)}{diskon_str}")
                lines.append(f"  = {format_rupiah(d.subtotal)}")
                lines.append("")

            lines += [
                f"{'─'*35}",
                f"Subtotal : {format_rupiah(t.total + t.diskon_total)}",
                f"Diskon   : - {format_rupiah(t.diskon_total)}",
                f"TOTAL    : {format_rupiah(t.total)}",
                f"Bayar    : {format_rupiah(t.bayar)}",
                f"Kembali  : {format_rupiah(t.kembalian)}",
                f"{'='*35}",
            ]

            self.detail_text.setPlainText("\n".join(lines))
            self._selected_invoice = t.no_invoice
            self._selected_id = transaksi_id
            self._selected_status = t.status
            self.btn_reprint.setEnabled(True)
            if auth.is_admin and hasattr(self, "btn_void"):
                self.btn_void.setEnabled(t.status == "selesai")

    def _reprint(self):
        if self._selected_invoice:
            self._reprint_invoice(self._selected_invoice)

    def _reprint_invoice(self, no_invoice: str):
        try:
            with db.get_session() as session:
                t = session.query(Transaksi).filter_by(no_invoice=no_invoice).first()
                if t:
                    PrinterService().print_receipt(t)
                    QMessageBox.information(self, "Cetak Struk", "Struk berhasil dicetak!")
        except Exception as e:
            QMessageBox.warning(self, "Printer Error", f"Gagal cetak: {str(e)}")

    def _void_transaction(self):
        if not hasattr(self, "_selected_id") or not self._selected_id:
            return

        reply = QMessageBox.question(
            self, "Konfirmasi Void",
            "Yakin ingin membatalkan transaksi ini?\nStok barang tidak akan dikembalikan secara otomatis.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with db.get_session() as session:
                t = session.query(Transaksi).filter_by(id=self._selected_id).first()
                if t:
                    t.status = "void"
                    session.commit()
            self._load_data()

    def refresh(self):
        self._load_data()
