"""
KasirKu Riwayat Transaksi
Halaman transaksi modern dengan stat cards, filter tabs, dan customer avatar
Matching reference design
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QDialog, QDateEdit,
    QTextEdit, QAbstractItemView, QSizePolicy, QSplitter, QScrollArea,
    QFileDialog
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont, QCursor

from database.db import db
from database.models import Transaksi, TransaksiDetail
from auth.auth_manager import auth
from utils.helpers import format_rupiah, format_datetime, format_tanggal
from services.printer_service import PrinterService
from services.invoice_pdf_service import InvoicePdfService
from ui.transaksi.retur_penjualan_dialog import ReturPenjualanDialog
from datetime import datetime, date, timedelta


AVATAR_COLORS = [
    "#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B",
    "#10B981", "#EF4444", "#14B8A6", "#F97316",
]


def get_avatar_color(name: str) -> str:
    idx = sum(ord(c) for c in (name or "A")) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


def get_initials(name: str) -> str:
    parts = (name or "?").strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (parts[0][:2]).upper() if parts else "?"


class RiwayatTransaksiPage(QWidget):
    """Halaman riwayat transaksi — redesigned"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transactions = []
        self._current_period = "hari_ini"
        self._selected_id = None
        self._selected_invoice = None
        self._selected_status = None
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── STAT CARDS ────────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_penjualan = self._make_stat_card("TOTAL PENJUALAN", "Rp 0", "-", "📊", "#1E3A5F")
        self.card_transaksi = self._make_stat_card("JUMLAH TRANSAKSI", "0", "Order", "📋", "#14532D")
        self.card_top_bayar = self._make_stat_card("PEMBAYARAN TOP", "-", "0 transaksi", "💳", "#7C3D12")
        self.card_perhatian = self._make_stat_card("PERLU PERHATIAN", "0", "Transaksi void", "⚠️", "#7F1D1D")

        for card in [self.card_penjualan, self.card_transaksi, self.card_top_bayar, self.card_perhatian]:
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # ── PERIOD FILTER TABS ────────────────────────────────────────────────
        period_row = QHBoxLayout()
        period_row.setSpacing(6)

        self._period_buttons = {}
        periods = [
            ("hari_ini", "Hari Ini"),
            ("kemarin", "Kemarin"),
            ("rentang", "Rentang Tanggal"),
        ]
        for key, label in periods:
            btn = QPushButton(label)
            btn.setObjectName("period_tab_active" if key == "hari_ini" else "period_tab")
            btn.setFixedHeight(36)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, k=key: self._set_period(k))
            period_row.addWidget(btn)
            self._period_buttons[key] = btn

        period_row.addStretch()

        # Date range (hidden by default)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setFixedHeight(36)
        self.date_from.hide()
        period_row.addWidget(self.date_from)

        lbl_sd = QLabel("s/d")
        lbl_sd.setStyleSheet("color: #64748B; background: transparent;")
        self.lbl_sd = lbl_sd
        lbl_sd.hide()
        period_row.addWidget(lbl_sd)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedHeight(36)
        self.date_to.hide()
        period_row.addWidget(self.date_to)

        btn_apply = QPushButton("Tampilkan")
        btn_apply.setFixedHeight(36)
        btn_apply.setCursor(QCursor(Qt.PointingHandCursor))
        btn_apply.hide()
        btn_apply.clicked.connect(self._load_data)
        self.btn_apply_date = btn_apply
        period_row.addWidget(btn_apply)

        layout.addLayout(period_row)

        # ── SEARCH + FILTER ROW ───────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        # Date display label
        self.date_display_lbl = QLabel()
        self.date_display_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        search_row.addWidget(self.date_display_lbl)
        search_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Cari No. Order atau Pelanggan...")
        self.search_input.setFixedHeight(38)
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._filter_data)
        search_row.addWidget(self.search_input)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Semua Status", "Selesai", "Void"])
        self.status_filter.setFixedHeight(38)
        self.status_filter.setFixedWidth(140)
        self.status_filter.currentTextChanged.connect(self._filter_data)
        search_row.addWidget(self.status_filter)

        layout.addLayout(search_row)

        # ── TABLE ─────────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ORDER ID", "PELANGGAN", "METODE PEMBAYARAN", "STATUS",
            "TOTAL NOMINAL", "WAKTU", "AKSI"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 90)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        # Detail panel
        detail_frame = QFrame()
        detail_frame.setObjectName("card")
        detail_frame.setMinimumWidth(260)
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        detail_title = QLabel("📄 Detail Transaksi")
        detail_title.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        detail_layout.addWidget(detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }
        """)
        self.detail_text.setPlaceholderText("Pilih transaksi untuk melihat detail")
        detail_layout.addWidget(self.detail_text)

        self.btn_reprint = QPushButton("🖨 Cetak Struk POS")
        self.btn_reprint.setObjectName("btn_secondary")
        self.btn_reprint.setFixedHeight(40)
        self.btn_reprint.setEnabled(False)
        self.btn_reprint.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_reprint.clicked.connect(self._reprint)
        detail_layout.addWidget(self.btn_reprint)

        self.btn_faktur_pdf = QPushButton("📄 Cetak Faktur (A4 / PDF)")
        self.btn_faktur_pdf.setObjectName("btn_primary")
        self.btn_faktur_pdf.setFixedHeight(40)
        self.btn_faktur_pdf.setEnabled(False)
        self.btn_faktur_pdf.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_faktur_pdf.clicked.connect(self._export_faktur_pdf)
        detail_layout.addWidget(self.btn_faktur_pdf)

        self.btn_retur = QPushButton("↩️ Retur Barang")
        self.btn_retur.setObjectName("btn_warning")
        self.btn_retur.setFixedHeight(40)
        self.btn_retur.setEnabled(False)
        self.btn_retur.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_retur.clicked.connect(self._open_retur_dialog)
        detail_layout.addWidget(self.btn_retur)

        if auth.is_admin:
            self.btn_void = QPushButton("❌ Void / Batalkan")
            self.btn_void.setObjectName("btn_danger")
            self.btn_void.setFixedHeight(40)
            self.btn_void.setEnabled(False)
            self.btn_void.setCursor(QCursor(Qt.PointingHandCursor))
            self.btn_void.clicked.connect(self._void_transaction)
            detail_layout.addWidget(self.btn_void)

        splitter.addWidget(detail_frame)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        # ── BOTTOM INFO ───────────────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        self.info_lbl = QLabel("")
        self.info_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        bottom_row.addWidget(self.info_lbl)
        layout.addLayout(bottom_row)

    def _make_stat_card(self, title, value, subtitle, icon, icon_bg):
        frame = QFrame()
        frame.setObjectName("stat_card_tx")
        frame.setMinimumHeight(95)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setObjectName(f"sc_title_{title}")
        title_lbl.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 0.5px; background: transparent; color: #94A3B8;")
        layout.addWidget(title_lbl)

        row = QHBoxLayout()
        row.setSpacing(8)

        val_lbl = QLabel(value)
        val_lbl.setObjectName(f"sc_val_{title}")
        val_lbl.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent; color: #F1F5F9;")
        row.addWidget(val_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName(f"sc_sub_{title}")
        sub_lbl.setStyleSheet("font-size: 11px; background: transparent; color: #22C55E;")
        row.addWidget(sub_lbl)
        row.addStretch()

        icon_frame = QFrame()
        icon_frame.setFixedSize(42, 42)
        icon_frame.setStyleSheet(f"background-color: {icon_bg}; border-radius: 10px;")
        icon_layout = QHBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        icon_layout.addWidget(icon_lbl)
        row.addWidget(icon_frame)

        layout.addLayout(row)

        frame._title_lbl = title_lbl
        frame._val_lbl = val_lbl
        frame._sub_lbl = sub_lbl

        self._apply_stat_card_theme(frame)
        return frame

    def _apply_stat_card_theme(self, frame):
        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")
        if is_dark:
            frame.setStyleSheet("""
                QFrame#stat_card_tx {
                    background-color: #1A1D27;
                    border: 1px solid #2D3250;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 0.5px; background: transparent; color: #94A3B8;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent; color: #F1F5F9;")
            if hasattr(frame, "_sub_lbl"):
                frame._sub_lbl.setStyleSheet("font-size: 11px; background: transparent; color: #22C55E;")
        else:
            frame.setStyleSheet("""
                QFrame#stat_card_tx {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
            if hasattr(frame, "_title_lbl"):
                frame._title_lbl.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 0.5px; background: transparent; color: #64748B;")
            if hasattr(frame, "_val_lbl"):
                frame._val_lbl.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent; color: #0F172A;")
            if hasattr(frame, "_sub_lbl"):
                frame._sub_lbl.setStyleSheet("font-size: 11px; background: transparent; color: #16A34A;")

    def _set_period(self, key: str):
        self._current_period = key
        for k, btn in self._period_buttons.items():
            btn.setObjectName("period_tab_active" if k == key else "period_tab")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        show_date_range = (key == "rentang")
        self.date_from.setVisible(show_date_range)
        self.date_to.setVisible(show_date_range)
        self.lbl_sd.setVisible(show_date_range)
        self.btn_apply_date.setVisible(show_date_range)

        if key != "rentang":
            self._load_data()

    def _load_data(self):
        today = date.today()
        if self._current_period == "hari_ini":
            dt_from = datetime.combine(today, datetime.min.time())
            dt_to = datetime.combine(today, datetime.max.time())
            self.date_display_lbl.setText(f"📅 {today.strftime('%d %b %Y')}")
        elif self._current_period == "kemarin":
            yesterday = today - timedelta(days=1)
            dt_from = datetime.combine(yesterday, datetime.min.time())
            dt_to = datetime.combine(yesterday, datetime.max.time())
            self.date_display_lbl.setText(f"📅 {yesterday.strftime('%d %b %Y')}")
        else:
            d_from = self.date_from.date().toPyDate()
            d_to = self.date_to.date().toPyDate()
            dt_from = datetime.combine(d_from, datetime.min.time())
            dt_to = datetime.combine(d_to, datetime.max.time())
            self.date_display_lbl.setText(
                f"📅 {d_from.strftime('%d %b %Y')} - {d_to.strftime('%d %b %Y')}"
            )

        with db.get_session() as session:
            trans = session.query(Transaksi).filter(
                Transaksi.tanggal >= dt_from,
                Transaksi.tanggal <= dt_to
            ).order_by(Transaksi.tanggal.desc()).all()

            self._transactions = [
                {
                    "id": t.id,
                    "no_invoice": t.no_invoice,
                    "tanggal": t.tanggal,
                    "kasir": t.kasir.nama_lengkap or t.kasir.username if t.kasir else "Kasir",
                    "kasir_username": t.kasir.username if t.kasir else "-",
                    "metode": t.metode_bayar,
                    "total": t.total,
                    "bayar": t.bayar,
                    "kembalian": t.kembalian,
                    "status": t.status,
                    "diskon": t.diskon_total,
                    "jumlah_item": len(t.detail),
                }
                for t in trans
            ]

        # Update stat cards
        selesai = [t for t in self._transactions if t["status"] == "selesai"]
        void = [t for t in self._transactions if t["status"] == "void"]
        total_revenue = sum(t["total"] for t in selesai)

        # Find top payment method
        metode_count = {}
        for t in selesai:
            m = t["metode"].upper()
            metode_count[m] = metode_count.get(m, 0) + 1
        top_metode = max(metode_count, key=metode_count.get) if metode_count else "-"
        top_metode_pct = f"{int(metode_count.get(top_metode, 0) * 100 / max(len(selesai), 1))}%"

        self.card_penjualan._val_lbl.setText(format_rupiah(total_revenue))
        self.card_penjualan._sub_lbl.setText(f"Dibandingkan kemarin")
        self.card_transaksi._val_lbl.setText(str(len(selesai)))
        avg = total_revenue // max(len(selesai), 1)
        self.card_transaksi._sub_lbl.setText(f"Rata-rata {format_rupiah(avg)}/order")
        self.card_top_bayar._val_lbl.setText(f"{top_metode} {top_metode_pct}")
        self.card_top_bayar._sub_lbl.setText(f"{metode_count.get(top_metode, 0)} total transaksi")
        self.card_perhatian._val_lbl.setText(str(len(void)))
        self.card_perhatian._sub_lbl.setText(f"{len(void)} Transaksi dibatalkan")

        self._filter_data()

    def _filter_data(self):
        q = self.search_input.text().lower().strip()
        status_f = self.status_filter.currentText()

        filtered = list(self._transactions)
        if q:
            filtered = [t for t in filtered if (
                q in t["no_invoice"].lower() or
                q in t["kasir"].lower() or
                q in t["kasir_username"].lower()
            )]
        if status_f == "Selesai":
            filtered = [t for t in filtered if t["status"] == "selesai"]
        elif status_f == "Void":
            filtered = [t for t in filtered if t["status"] == "void"]

        self._render_table(filtered)

        total_amount = sum(t["total"] for t in filtered if t["status"] == "selesai")
        self.info_lbl.setText(
            f"Menampilkan 1-{len(filtered)} dari {len(filtered)} transaksi"
        )

    def on_theme_changed(self, theme: str):
        """Hook saat tema berubah"""
        for card in [self.card_penjualan, self.card_transaksi, self.card_top_bayar, self.card_perhatian]:
            self._apply_stat_card_theme(card)
        self._filter_data()

    def _render_table(self, data: list):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setRowCount(len(data))
        is_dark = (db.get_setting("app_theme", "light") == "dark")
        text_primary = "#F1F5F9" if is_dark else "#1E293B"
        text_muted = "#94A3B8" if is_dark else "#64748B"

        for row, t in enumerate(data):
            self.table.setRowHeight(row, 60)

            # ── Col 0: Order ID (bold blue) ──
            order_id_item = QTableWidgetItem(f"#{t['no_invoice'][-6:] if len(t['no_invoice']) > 6 else t['no_invoice']}")
            order_id_item.setForeground(QColor("#3B82F6"))
            order_id_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            order_id_item.setData(Qt.UserRole, t["id"])
            self.table.setItem(row, 0, order_id_item)

            # ── Col 1: Pelanggan (avatar + kasir name + item count) ──
            customer_widget = QWidget()
            customer_widget.setStyleSheet("background: transparent;")
            cust_layout = QHBoxLayout(customer_widget)
            cust_layout.setContentsMargins(8, 4, 8, 4)
            cust_layout.setSpacing(10)

            initials = get_initials(t["kasir"])
            avatar_color = get_avatar_color(t["kasir"])
            avatar_lbl = QLabel(initials)
            avatar_lbl.setFixedSize(34, 34)
            avatar_lbl.setAlignment(Qt.AlignCenter)
            avatar_lbl.setStyleSheet(f"""
                background-color: {avatar_color};
                color: #FFFFFF;
                border-radius: 17px;
                font-weight: 700;
                font-size: 11px;
            """)
            cust_layout.addWidget(avatar_lbl)

            cust_text = QVBoxLayout()
            cust_text.setSpacing(1)
            name_lbl = QLabel(t["kasir"])
            name_lbl.setStyleSheet(f"color: {text_primary}; font-weight: 600; font-size: 13px; background: transparent;")
            cust_text.addWidget(name_lbl)
            items_lbl = QLabel(f"{t['jumlah_item']} item")
            items_lbl.setStyleSheet(f"color: {text_muted}; font-size: 11px; background: transparent;")
            cust_text.addWidget(items_lbl)
            cust_layout.addLayout(cust_text)

            self.table.setCellWidget(row, 1, customer_widget)

            # ── Col 2: Metode Pembayaran ──
            metode_icons = {
                "qris": "⊞", "tunai": "💵", "cash": "💵",
                "debit": "💳", "kredit": "💳", "transfer": "🏦"
            }
            metode_key = t["metode"].lower()
            metode_icon = next((v for k, v in metode_icons.items() if k in metode_key), "💰")
            metode_item = QTableWidgetItem(f"{metode_icon} {t['metode'].title()}")
            metode_item.setForeground(QColor(text_primary))
            metode_item.setData(Qt.UserRole, t["id"])
            self.table.setItem(row, 2, metode_item)

            # ── Col 3: Status badge ──
            status_widget = QWidget()
            status_widget.setStyleSheet("background: transparent;")
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(4, 2, 4, 2)
            status_layout.setAlignment(Qt.AlignCenter)

            status_lbl = QLabel(t["status"].capitalize())
            status_lbl.setWordWrap(False)
            status_lbl.setFixedHeight(24)
            status_lbl.setMinimumWidth(80)
            status_lbl.setAlignment(Qt.AlignCenter)
            if t["status"] == "selesai":
                bg_col = "#14532D" if is_dark else "#DCFCE7"
                fg_col = "#86EFAC" if is_dark else "#15803D"
                border_col = "#166534" if is_dark else "#BBF7D0"
            elif t["status"] == "void":
                bg_col = "#7F1D1D" if is_dark else "#FEE2E2"
                fg_col = "#FCA5A5" if is_dark else "#B91C1C"
                border_col = "#991B1B" if is_dark else "#FECACA"
            else:
                bg_col = "#78350F" if is_dark else "#FEF3C7"
                fg_col = "#FCD34D" if is_dark else "#B45309"
                border_col = "#92400E" if is_dark else "#FDE68A"

            status_lbl.setStyleSheet(f"background-color: {bg_col}; color: {fg_col}; border: 1px solid {border_col}; border-radius: 10px; padding: 2px 12px; font-size: 11px; font-weight: 700; white-space: nowrap;")
            status_layout.addWidget(status_lbl)
            self.table.setCellWidget(row, 3, status_widget)

            # ── Col 4: Total ──
            total_color = "#94A3B8" if t["status"] == "void" else ("#F1F5F9" if is_dark else "#1E293B")
            total_item = QTableWidgetItem(format_rupiah(t["total"]))
            total_item.setForeground(QColor(total_color))
            total_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            total_item.setData(Qt.UserRole, t["id"])
            self.table.setItem(row, 4, total_item)

            # ── Col 5: Waktu ──
            waktu_str = t["tanggal"].strftime("%H:%M\nWIB") if t["tanggal"] else "-"
            waktu_item = QTableWidgetItem(waktu_str)
            waktu_item.setForeground(QColor(text_muted))
            waktu_item.setData(Qt.UserRole, t["id"])
            self.table.setItem(row, 5, waktu_item)

            # ── Col 6: Actions ──
            action_w = QWidget()
            action_w.setStyleSheet("background: transparent;")
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 4, 4, 4)
            action_l.setSpacing(4)
            action_l.setAlignment(Qt.AlignCenter)

            btn_print = QPushButton("🖨")
            btn_print.setFixedSize(30, 30)
            btn_print.setToolTip("Cetak Ulang")
            is_dark = (db.get_setting("app_theme", "dark") == "dark")
            if is_dark:
                btn_print.setStyleSheet("QPushButton { background-color: #1A1D27; border: 1px solid #2D3250; border-radius: 6px; color: #F1F5F9; } QPushButton:hover { background-color: #21263A; }")
            else:
                btn_print.setStyleSheet("QPushButton { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; color: #1E293B; } QPushButton:hover { background-color: #F1F5F9; }")
            btn_print.setCursor(QCursor(Qt.PointingHandCursor))
            btn_print.clicked.connect(lambda _, inv=t["no_invoice"]: self._reprint_invoice(inv))
            action_l.addWidget(btn_print)

            btn_detail = QPushButton("👁")
            btn_detail.setFixedSize(30, 30)
            btn_detail.setToolTip("Lihat Detail")
            btn_detail.setStyleSheet("QPushButton { background-color: #1E3A5F; border: none; border-radius: 6px; } QPushButton:hover { background-color: #1E40AF; }")
            btn_detail.setCursor(QCursor(Qt.PointingHandCursor))
            btn_detail.clicked.connect(lambda _, tid=t["id"]: self._show_detail(tid))
            action_l.addWidget(btn_detail)

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

            cust_name = t.nama_pelanggan or (t.pelanggan.nama if t.pelanggan else "-")
            cust_npwp = t.npwp_pelanggan or (t.pelanggan.npwp if t.pelanggan else "-")
            dpp_val = t.dpp if (t.dpp and t.dpp > 0) else t.total

            lines += [
                f"{'─'*35}",
                f"Pelanggan: {cust_name}",
                f"NPWP     : {cust_npwp}",
                f"Status   : {(t.status_bayar or 'lunas').upper()}",
                f"{'─'*35}",
                f"Subtotal (DPP): {format_rupiah(dpp_val)}",
            ]
            if t.diskon_total > 0:
                lines.append(f"Diskon   : - {format_rupiah(t.diskon_total)}")
            if (t.ppn_nominal or 0) > 0:
                lines.append(f"PPN ({t.ppn_persen:.0f}%) : + {format_rupiah(t.ppn_nominal)}")
            if (t.pph_nominal or 0) > 0:
                lines.append(f"PPh ({t.pph_persen:.1f}%): - {format_rupiah(t.pph_nominal)}")

            lines += [
                f"TOTAL    : {format_rupiah(t.total)}",
                f"Bayar    : {format_rupiah(t.bayar)}",
                f"Kembali  : {format_rupiah(t.kembalian)}",
                f"{'='*35}",
            ]

            if t.retur:
                lines += [
                    f"RIWAYAT RETUR ({len(t.retur)}x):"
                ]
                for r in t.retur:
                    lines.append(f" • {r.no_retur}: {format_rupiah(r.total_retur)} ({r.metode_kembali})")
                lines.append(f"{'='*35}")

            self.detail_text.setPlainText("\n".join(lines))
            self._selected_invoice = t.no_invoice
            self._selected_id = transaksi_id
            self._selected_status = t.status
            self.btn_reprint.setEnabled(True)
            self.btn_faktur_pdf.setEnabled(True)
            self.btn_retur.setEnabled(t.status == "selesai")
            if auth.is_admin and hasattr(self, "btn_void"):
                self.btn_void.setEnabled(t.status == "selesai")

    def _export_faktur_pdf(self):
        if not self._selected_invoice:
            return
        with db.get_session() as session:
            t = session.query(Transaksi).filter_by(no_invoice=self._selected_invoice).first()
            if not t:
                QMessageBox.warning(self, "Error", "Transaksi tidak ditemukan.")
                return

            html = InvoicePdfService.generate_sales_invoice_html(t)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan Faktur Penjualan (PDF)",
                f"Faktur_Penjualan_{t.no_invoice}.pdf",
                "PDF Files (*.pdf)"
            )
            if file_path:
                ok = InvoicePdfService.save_html_to_pdf(html, file_path)
                if ok:
                    QMessageBox.information(self, "Sukses", f"Faktur A4 PDF berhasil disimpan ke:\n{file_path}")
                else:
                    QMessageBox.critical(self, "Gagal", "Gagal menyimpan file PDF.")

    def _open_retur_dialog(self):
        if not self._selected_id:
            return
        dlg = ReturPenjualanDialog(self._selected_id, self)
        dlg.retur_processed.connect(self._load_data)
        dlg.exec_()

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
        if not self._selected_id:
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

    def on_theme_changed(self, theme: str):
        """Update stat cards, detail panel, and table on theme switch"""
        is_dark = (theme == "dark")
        for card in [self.card_penjualan, self.card_transaksi, self.card_top_bayar, self.card_perhatian]:
            self._apply_stat_card_theme(card)
        if hasattr(self, "detail_text"):
            bg = "#1A1D27" if is_dark else "#F8FAFC"
            color = "#F1F5F9" if is_dark else "#1E293B"
            border = "#2D3250" if is_dark else "#E2E8F0"
            self.detail_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg};
                    color: {color};
                    border: 1px solid {border};
                    border-radius: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    padding: 10px;
                }}
            """)
        self._load_data()
