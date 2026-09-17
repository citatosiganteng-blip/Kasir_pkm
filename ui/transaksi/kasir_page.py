"""
KasirKu Kasir Page (POS)
Clean, modern, and professional POS interface matching reference design
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QMessageBox, QDialog, QApplication, QButtonGroup, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QCursor

from database.db import db
from database.models import Barang, Transaksi, TransaksiDetail
from auth.auth_manager import auth
from utils.helpers import (
    format_rupiah, generate_invoice_number, format_datetime,
    generate_tax_invoice_number
)
from services.printer_service import PrinterService
from services.drawer_service import DrawerService
from services.invoice_pdf_service import InvoicePdfService


class CartItem:
    def __init__(self, barang_id, kode, nama, harga, stok_available, kategori=""):
        self.barang_id = barang_id
        self.kode = kode
        self.nama = nama
        self.harga = harga
        self.qty = 1
        self.diskon = 0.0  # persen
        self.stok_available = stok_available
        self.kategori = kategori

    @property
    def subtotal(self):
        diskon_amount = self.harga * (self.diskon / 100)
        return (self.harga - diskon_amount) * self.qty

    @property
    def harga_after_discount(self):
        return self.harga * (1 - self.diskon / 100)


def get_product_icon_and_bg(nama: str, kategori: str):
    """Mendapatkan emoji/ikon dan warna latar belakang ilustrasi berdasarkan produk"""
    name_lower = (nama or "").lower()
    cat_lower = (kategori or "").lower()

    if "nasi goreng" in name_lower or "goreng" in name_lower:
        return "🍛", "#FEF3C7"  # Warm amber
    elif "ayam" in name_lower or "bakar" in name_lower:
        return "🍗", "#FFEDD5"  # Soft orange
    elif "teh" in name_lower or "es teh" in name_lower:
        return "🍹", "#ECFDF5"  # Soft mint/green
    elif "kopi" in name_lower:
        return "☕", "#FEF2F2"  # Soft warm red/brown
    elif "keripik" in name_lower or "snack" in name_lower or "singkong" in name_lower:
        return "🍟", "#FFFBEB"  # Soft yellow
    elif "aqua" in name_lower or "air" in name_lower:
        return "🥤", "#EFF6FF"  # Soft blue
    elif "mie" in name_lower or "indomie" in name_lower:
        return "🍜", "#FEF3C7"
    elif "sabun" in name_lower:
        return "🧼", "#F0FDF4"
    elif "gigi" in name_lower or "pepsodent" in name_lower:
        return "🪥", "#E0F2FE"
    elif "beras" in name_lower:
        return "🍚", "#F8FAFC"
    elif "minuman" in cat_lower:
        return "🧋", "#EFF6FF"
    elif "makanan" in cat_lower:
        return "🍱", "#FEF3C7"
    elif "jajanan" in cat_lower:
        return "🥨", "#FDF2F8"
    elif "kebersihan" in cat_lower:
        return "🧴", "#F0FDF4"
    elif "sembako" in cat_lower:
        return "🌾", "#FAF5FF"
    elif "elektronik" in cat_lower:
        return "🔌", "#E0F2FE"
    return "📦", "#F1F5F9"


class ProductCard(QFrame):
    """Kartu produk modern dengan ilustrasi, nama, harga, dan indikator stok"""
    clicked = pyqtSignal(object)

    def __init__(self, barang: Barang, parent=None):
        super().__init__(parent)
        self.barang = barang
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(185)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("product_card")
        self._setup_ui()

    def _setup_ui(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_dark:
            self.setStyleSheet("""
                QFrame#product_card {
                    background-color: #1A1D27;
                    border: 1.5px solid #2D3250;
                    border-radius: 14px;
                }
                QFrame#product_card:hover {
                    border-color: #3B82F6;
                    background-color: #21263A;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#product_card {
                    background-color: #FFFFFF;
                    border: 1.5px solid #E2E8F0;
                    border-radius: 14px;
                }
                QFrame#product_card:hover {
                    border-color: #2563EB;
                    background-color: #FAFAFA;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # Icon / Illustration badge
        icon_str, bg_color = get_product_icon_and_bg(self.barang.nama, self.barang.kategori or "")
        icon_container = QFrame()
        icon_container.setFixedSize(68, 68)
        if is_dark:
            icon_container.setStyleSheet("""
                QFrame {
                    background-color: #21263A;
                    border-radius: 34px;
                    border: 1px solid #2D3250;
                }
            """)
        else:
            icon_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border-radius: 34px;
                    border: 1px solid rgba(0, 0, 0, 0.05);
                }}
            """)
        ic_layout = QVBoxLayout(icon_container)
        ic_layout.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel(icon_str)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("font-size: 34px; background: transparent;")
        ic_layout.addWidget(ic_lbl)

        layout.addWidget(icon_container, 0, Qt.AlignCenter)
        layout.addSpacing(4)

        # Product Name
        name_lbl = QLabel(self.barang.nama)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setMaximumHeight(36)
        name_color = "#F1F5F9" if is_dark else "#1E293B"
        name_lbl.setStyleSheet(f"""
            color: {name_color};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(name_lbl)

        # Price
        price_lbl = QLabel(format_rupiah(self.barang.harga_jual))
        price_lbl.setAlignment(Qt.AlignCenter)
        price_color = "#60A5FA" if is_dark else "#2563EB"
        price_lbl.setStyleSheet(f"""
            color: {price_color};
            font-size: 12px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(price_lbl)

        # Stock indicator pill
        if self.barang.stok <= 0:
            stok_txt = "Habis"
            stok_color = "#EF4444" if is_dark else "#DC2626"
            stok_bg = "#2D1A1A" if is_dark else "#FEE2E2"
        elif self.barang.stok <= (self.barang.stok_min or 5):
            stok_txt = f"Sisa {self.barang.stok}"
            stok_color = "#F59E0B" if is_dark else "#D97706"
            stok_bg = "#2D261A" if is_dark else "#FEF3C7"
        else:
            stok_txt = f"Stok: {self.barang.stok}"
            stok_color = "#10B981" if is_dark else "#059669"
            stok_bg = "#1A2D23" if is_dark else "#ECFDF5"

        stok_lbl = QLabel(stok_txt)
        stok_lbl.setAlignment(Qt.AlignCenter)
        stok_lbl.setStyleSheet(f"""
            color: {stok_color};
            background-color: {stok_bg};
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 8px;
        """)
        layout.addWidget(stok_lbl, 0, Qt.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.barang)
        super().mousePressEvent(event)


class CartItemRow(QFrame):
    """Baris item keranjang interaktif persis seperti referensi visual"""
    qty_changed = pyqtSignal(int)
    remove_clicked = pyqtSignal()

    def __init__(self, item: CartItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setObjectName("cart_item_row")
        self._setup_ui()

    def _setup_ui(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_dark:
            self.setStyleSheet("""
                QFrame#cart_item_row {
                    background-color: #1A1D27;
                    border-bottom: 1px solid #21263A;
                    padding: 4px 0;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#cart_item_row {
                    background-color: #FFFFFF;
                    border-bottom: 1px solid #F1F5F9;
                    padding: 4px 0;
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Thumbnail
        icon_str, bg_color = get_product_icon_and_bg(self.item.nama, self.item.kategori)
        thumb = QFrame()
        thumb.setFixedSize(40, 40)
        if is_dark:
            thumb.setStyleSheet("""
                background-color: #21263A;
                border-radius: 20px;
                border: 1px solid #2D3250;
            """)
        else:
            thumb.setStyleSheet(f"""
                background-color: {bg_color};
                border-radius: 20px;
                border: 1px solid rgba(0,0,0,0.04);
            """)
        th_layout = QVBoxLayout(thumb)
        th_layout.setContentsMargins(0, 0, 0, 0)
        th_lbl = QLabel(icon_str)
        th_lbl.setAlignment(Qt.AlignCenter)
        th_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        th_layout.addWidget(th_lbl)
        layout.addWidget(thumb)

        # Name & unit price
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_lbl = QLabel(self.item.nama)
        name_color = "#F1F5F9" if is_dark else "#1E293B"
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {name_color}; background: transparent;")
        info_layout.addWidget(name_lbl)

        unit_lbl = QLabel(format_rupiah(self.item.harga))
        unit_color = "#94A3B8" if is_dark else "#64748B"
        unit_lbl.setStyleSheet(f"font-size: 11px; color: {unit_color}; background: transparent;")
        info_layout.addWidget(unit_lbl)
        layout.addLayout(info_layout, 1)

        # Qty multiplier indicator
        mult_lbl = QLabel(f"{self.item.qty}x")
        mult_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {unit_color}; background: transparent;")
        layout.addWidget(mult_lbl)

        # Subtotal
        sub_lbl = QLabel(format_rupiah(self.item.subtotal))
        sub_color = "#60A5FA" if is_dark else "#1E293B"
        sub_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {sub_color}; background: transparent;")
        layout.addWidget(sub_lbl)

        # Stepper: [-]
        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(26, 26)
        btn_minus.setCursor(QCursor(Qt.PointingHandCursor))
        if is_dark:
            btn_minus.setStyleSheet("""
                QPushButton {
                    background-color: #21263A;
                    color: #CBD5E1;
                    border: 1px solid #2D3250;
                    border-radius: 13px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #2D3250;
                    color: #F1F5F9;
                }
            """)
        else:
            btn_minus.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #E2E8F0;
                    border-radius: 13px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #1E293B;
                }
            """)
        btn_minus.clicked.connect(lambda: self.qty_changed.emit(self.item.qty - 1))
        layout.addWidget(btn_minus)

        # Stepper: [+]
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(26, 26)
        btn_plus.setCursor(QCursor(Qt.PointingHandCursor))
        if is_dark:
            btn_plus.setStyleSheet("""
                QPushButton {
                    background-color: #21263A;
                    color: #CBD5E1;
                    border: 1px solid #2D3250;
                    border-radius: 13px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #2D3250;
                    color: #F1F5F9;
                }
            """)
        else:
            btn_plus.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #E2E8F0;
                    border-radius: 13px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #1E293B;
                }
            """)
        btn_plus.clicked.connect(lambda: self.qty_changed.emit(self.item.qty + 1))
        layout.addWidget(btn_plus)

        # Trash icon
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(26, 26)
        btn_del.setCursor(QCursor(Qt.PointingHandCursor))
        if is_dark:
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #EF4444;
                    border: none;
                    font-size: 14px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #2D1A1A;
                    border-radius: 6px;
                }
            """)
        else:
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #EF4444;
                    border: none;
                    font-size: 14px;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                    border-radius: 6px;
                }
            """)
        btn_del.clicked.connect(self.remove_clicked.emit)
        layout.addWidget(btn_del)


class KasirPage(QWidget):
    """Halaman POS kasir dengan layout modern persis seperti referensi visual"""
    transaction_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart: list[CartItem] = []
        self._all_barang = []
        self._active_category = "Semua"
        self._selected_metode = "Tunai"
        self._nominal_bayar = 0.0

        self._setup_ui()
        self._load_barang()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # =====================================================================
        # LEFT PANEL: Search, Category Pills, Product Cards Grid (~65%)
        # =====================================================================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Top Bar: Search input
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari nama produk atau scan barcode (F2)...")
        self.search_input.setFixedHeight(42)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.returnPressed.connect(self._add_by_barcode)
        top_bar.addWidget(self.search_input)

        left_layout.addLayout(top_bar)

        # Category Pills Row
        self.category_scroll = QScrollArea()
        self.category_scroll.setFixedHeight(46)
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.category_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.category_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.pills_widget = QWidget()
        self.pills_widget.setStyleSheet("background: transparent;")
        self.pills_layout = QHBoxLayout(self.pills_widget)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(8)
        self.pills_layout.setAlignment(Qt.AlignLeft)

        self.category_scroll.setWidget(self.pills_widget)
        left_layout.addWidget(self.category_scroll)

        # Product Grid Area
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.grid_scroll.setWidget(self.grid_container)
        left_layout.addWidget(self.grid_scroll, 1)

        main_layout.addWidget(left_container, 65)

        # =====================================================================
        # RIGHT PANEL: Cart & Checkout (~35%)
        # =====================================================================
        right_panel = QFrame()
        right_panel.setObjectName("right_checkout_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)

        # Cart Header
        cart_header = QHBoxLayout()
        self.cart_title = QLabel("🛒 Keranjang")
        cart_header.addWidget(self.cart_title)

        self.item_count_badge = QLabel("0 item")
        self.item_count_badge.setStyleSheet("""
            background-color: #EFF6FF;
            color: #2563EB;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 10px;
        """)
        cart_header.addWidget(self.item_count_badge)
        cart_header.addStretch()

        self.btn_clear = QPushButton("Hapus")
        self.btn_clear.setFixedHeight(28)
        self.btn_clear.clicked.connect(self._clear_cart)
        cart_header.addWidget(self.btn_clear)
        right_layout.addLayout(cart_header)

        # Cart items scroll area
        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cart_list_container = QWidget()
        self.cart_list_container.setStyleSheet("background: transparent;")
        self.cart_list_layout = QVBoxLayout(self.cart_list_container)
        self.cart_list_layout.setContentsMargins(0, 0, 0, 0)
        self.cart_list_layout.setSpacing(4)
        self.cart_list_layout.setAlignment(Qt.AlignTop)

        self.cart_scroll.setWidget(self.cart_list_container)
        right_layout.addWidget(self.cart_scroll, 1)

        # Summary box
        self.summary_box = QFrame()
        sum_layout = QVBoxLayout(self.summary_box)
        sum_layout.setContentsMargins(14, 12, 14, 12)
        sum_layout.setSpacing(6)

        # Subtotal row
        sub_row = QHBoxLayout()
        self.sub_lbl = QLabel("Subtotal")
        sub_row.addWidget(self.sub_lbl)
        sub_row.addStretch()
        self.subtotal_val_lbl = QLabel("Rp 0")
        sub_row.addWidget(self.subtotal_val_lbl)
        sum_layout.addLayout(sub_row)

        # Pajak row (10%)
        tax_row = QHBoxLayout()
        self.tax_lbl = QLabel("Pajak (10%)")
        tax_row.addWidget(self.tax_lbl)
        tax_row.addStretch()
        self.tax_val_lbl = QLabel("Rp 0")
        tax_row.addWidget(self.tax_val_lbl)
        sum_layout.addLayout(tax_row)

        # Divider
        self.divider = QFrame()
        self.divider.setFixedHeight(1)
        sum_layout.addWidget(self.divider)

        # Total row
        tot_row = QHBoxLayout()
        self.tot_lbl = QLabel("Total")
        tot_row.addWidget(self.tot_lbl)
        tot_row.addStretch()
        self.total_val_lbl = QLabel("Rp 0")
        tot_row.addWidget(self.total_val_lbl)
        sum_layout.addLayout(tot_row)

        right_layout.addWidget(self.summary_box)

        # Payment Method Tabs (exact 4 tabs from screenshot)
        pay_tabs_layout = QHBoxLayout()
        pay_tabs_layout.setSpacing(6)

        self.pay_btn_group = QButtonGroup(self)
        self.pay_btn_group.setExclusive(True)

        metodes = ["Tunai", "Debit/Kredit", "QRIS/E-Wallet", "Metode Lain"]
        self.pay_buttons = {}

        for m in metodes:
            btn = QPushButton(m)
            btn.setFixedHeight(34)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            if m == "Tunai":
                btn.setChecked(True)
            btn.toggled.connect(lambda chk, b=btn, name=m: self._on_payment_tab_toggled(b, name, chk))
            self.pay_btn_group.addButton(btn)
            self.pay_buttons[m] = btn
            pay_tabs_layout.addWidget(btn)

        right_layout.addLayout(pay_tabs_layout)

        # Quick Cash Nominal Buttons (for Tunai)
        self.quick_cash_frame = QFrame()
        self.quick_cash_frame.setStyleSheet("background: transparent;")
        qc_layout = QHBoxLayout(self.quick_cash_frame)
        qc_layout.setContentsMargins(0, 0, 0, 0)
        qc_layout.setSpacing(6)

        self.btn_pas = QPushButton("Uang Pas")
        self.btn_50k = QPushButton("Rp 50rb")
        self.btn_100k = QPushButton("Rp 100rb")
        self.btn_200k = QPushButton("Rp 200rb")

        for b, val in [
            (self.btn_pas, "pas"),
            (self.btn_50k, 50000),
            (self.btn_100k, 100000),
            (self.btn_200k, 200000)
        ]:
            b.setFixedHeight(34)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.clicked.connect(lambda _, v=val: self._on_quick_cash_clicked(v))
            qc_layout.addWidget(b)

        right_layout.addWidget(self.quick_cash_frame)

        # Big Action Button: BAYAR SEKARANG
        self.btn_checkout = QPushButton("BAYAR SEKARANG")
        self.btn_checkout.setFixedHeight(50)
        self.btn_checkout.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_checkout.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #94A3B8;
            }
        """)
        self.btn_checkout.clicked.connect(self._do_checkout)
        right_layout.addWidget(self.btn_checkout)

        main_layout.addWidget(right_panel, 35)

        self._apply_theme_to_ui()
        self._update_cart_display()

    # =========================================================================
    # Styling Helpers
    # =========================================================================

    def _apply_theme_to_ui(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"

        # Cart title & clear button
        self.cart_title.setStyleSheet(
            f"font-size: 16px; font-weight: 800; color: {'#F1F5F9' if is_dark else '#1E293B'}; background: transparent;"
        )
        if is_dark:
            self.btn_clear.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #EF4444;
                    border: 1px solid #7F1D1D;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #2D1A1A; }
            """)
            self.summary_box.setStyleSheet("""
                QFrame {
                    background-color: #1E2235;
                    border: 1px solid #2D3250;
                    border-radius: 12px;
                    padding: 6px;
                }
            """)
            self.divider.setStyleSheet("background-color: #2D3250;")
            lbl_muted = "#94A3B8"
            lbl_text = "#F1F5F9"
            lbl_total = "#60A5FA"
        else:
            self.btn_clear.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #EF4444;
                    border: 1px solid #FCA5A5;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #FEE2E2; }
            """)
            self.summary_box.setStyleSheet("""
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                    padding: 6px;
                }
            """)
            self.divider.setStyleSheet("background-color: #E2E8F0;")
            lbl_muted = "#64748B"
            lbl_text = "#1E293B"
            lbl_total = "#0F172A"

        self.sub_lbl.setStyleSheet(f"color: {lbl_muted}; font-size: 13px; background: transparent;")
        self.tax_lbl.setStyleSheet(f"color: {lbl_muted}; font-size: 13px; background: transparent;")
        self.subtotal_val_lbl.setStyleSheet(f"color: {lbl_text}; font-size: 13px; font-weight: 600; background: transparent;")
        self.tax_val_lbl.setStyleSheet(f"color: {lbl_text}; font-size: 13px; font-weight: 600; background: transparent;")
        self.tot_lbl.setStyleSheet(f"color: {lbl_text}; font-size: 16px; font-weight: 800; background: transparent;")
        self.total_val_lbl.setStyleSheet(f"color: {lbl_total}; font-size: 18px; font-weight: 900; background: transparent;")

        # Update payment tab buttons
        if hasattr(self, "pay_buttons"):
            for m, btn in self.pay_buttons.items():
                self._apply_payment_pill_style(btn, btn.isChecked())

        # Update quick cash buttons
        if hasattr(self, "btn_pas"):
            for b in [self.btn_pas, self.btn_50k, self.btn_100k, self.btn_200k]:
                if is_dark:
                    b.setStyleSheet("""
                        QPushButton {
                            background-color: #21263A;
                            color: #93C5FD;
                            border: 1px solid #2D3250;
                            border-radius: 8px;
                            font-size: 12px;
                            font-weight: 700;
                            padding: 0 8px;
                        }
                        QPushButton:hover { background-color: #2D3250; border-color: #3B82F6; }
                    """)
                else:
                    b.setStyleSheet("""
                        QPushButton {
                            background-color: #EFF6FF;
                            color: #1E40AF;
                            border: 1px solid #BFDBFE;
                            border-radius: 8px;
                            font-size: 12px;
                            font-weight: 700;
                            padding: 0 8px;
                        }
                        QPushButton:hover { background-color: #DBEAFE; }
                    """)

        # Update category buttons
        if hasattr(self, "_category_buttons"):
            for c, btn in self._category_buttons:
                self._apply_category_pill_style(btn, c == self._active_category)

    def on_theme_changed(self, theme: str):
        """Dipanggil saat tema tampilan diganti (light / dark)"""
        self._apply_theme_to_ui()
        self._render_product_grid()
        self._update_cart_display()

    def _apply_payment_pill_style(self, btn: QPushButton, is_active: bool):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0 10px;
                }
            """)
        else:
            if is_dark:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #21263A;
                        color: #94A3B8;
                        border: 1px solid #2D3250;
                        border-radius: 8px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 10px;
                    }
                    QPushButton:hover {
                        background-color: #2D3250;
                        color: #F1F5F9;
                        border-color: #3B82F6;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #475569;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 0 10px;
                    }
                    QPushButton:hover {
                        background-color: #F8FAFC;
                        border-color: #CBD5E1;
                    }
                """)

    def _on_payment_tab_toggled(self, btn: QPushButton, name: str, is_checked: bool):
        self._apply_payment_pill_style(btn, is_checked)
        if is_checked:
            self._selected_metode = name
            self.quick_cash_frame.setVisible(name == "Tunai")

    # =========================================================================
    # Data Loading & Category Pills
    # =========================================================================

    def _load_barang(self):
        """Ambil data barang dari database"""
        with db.get_session() as session:
            items = session.query(Barang).filter_by(aktif=True).order_by(Barang.nama).all()
            session.expunge_all()
            self._all_barang = items

        self._setup_category_pills()
        self._render_product_grid()

    def _setup_category_pills(self):
        """Buat pill kategori dinamis berdasarkan barang yang ada di DB"""
        # Clear existing buttons
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        categories = ["Semua"]
        cat_set = sorted(list({b.kategori for b in self._all_barang if b.kategori}))
        categories.extend(cat_set)

        self._category_buttons = []
        for cat in categories:
            btn = QPushButton(cat)
            btn.setFixedHeight(34)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            is_active = (cat == self._active_category)
            btn.setChecked(is_active)
            self._apply_category_pill_style(btn, is_active)
            btn.clicked.connect(lambda _, c=cat: self._filter_by_category(c))
            self.pills_layout.addWidget(btn)
            self._category_buttons.append((cat, btn))

    def _apply_category_pill_style(self, btn: QPushButton, is_active: bool):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 17px;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0 18px;
                }
            """)
        else:
            if is_dark:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1A1D27;
                        color: #94A3B8;
                        border: 1px solid #2D3250;
                        border-radius: 17px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 18px;
                    }
                    QPushButton:hover {
                        background-color: #21263A;
                        border-color: #3B82F6;
                        color: #F1F5F9;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #475569;
                        border: 1px solid #E2E8F0;
                        border-radius: 17px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 18px;
                    }
                    QPushButton:hover {
                        background-color: #F8FAFC;
                        border-color: #CBD5E1;
                        color: #1E293B;
                    }
                """)

    def _filter_by_category(self, cat: str):
        self._active_category = cat
        for c, btn in self._category_buttons:
            self._apply_category_pill_style(btn, c == cat)
        self._render_product_grid()

    def _on_search(self, text: str):
        self._render_product_grid()

    def _render_product_grid(self):
        """Render grid kartu produk sesuai kategori dan search keyword"""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.search_input.text().strip().lower()

        filtered = []
        for b in self._all_barang:
            # Filter category
            if self._active_category != "Semua" and (b.kategori or "") != self._active_category:
                continue
            # Filter search query
            if query:
                match_name = query in b.nama.lower()
                match_kode = query in (b.kode or "").lower()
                match_bar = query in (b.barcode or "").lower()
                if not (match_name or match_kode or match_bar):
                    continue
            filtered.append(b)

        if not filtered:
            empty_lbl = QLabel("Tidak ada produk yang cocok.")
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 40px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_lbl, 0, 0, 1, 3)
            return

        columns = 3  # Match reference layout 3-kolom
        for idx, b in enumerate(filtered):
            card = ProductCard(b)
            card.clicked.connect(self._add_to_cart)
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)

    # =========================================================================
    # Cart Operations
    # =========================================================================

    def _add_to_cart(self, barang: Barang):
        """Tambah barang ke keranjang atau tambah qty jika sudah ada"""
        if barang.stok <= 0:
            QMessageBox.warning(self, "Stok Habis", f"Stok untuk '{barang.nama}' sudah habis!")
            return

        # Cek apakah item sudah ada di cart
        existing = next((i for i in self.cart if i.barang_id == barang.id), None)
        if existing:
            if existing.qty >= barang.stok:
                QMessageBox.warning(self, "Stok Tidak Cukup", f"Stok tersedia hanya {barang.stok}!")
                return
            existing.qty += 1
        else:
            new_item = CartItem(
                barang_id=barang.id,
                kode=barang.kode,
                nama=barang.nama,
                harga=barang.harga_jual,
                stok_available=barang.stok,
                kategori=barang.kategori or ""
            )
            self.cart.append(new_item)

        self._update_cart_display()

    def _add_by_barcode(self):
        code = self.search_input.text().strip()
        if not code:
            return

        barang = next(
            (b for b in self._all_barang if b.barcode == code or b.kode.lower() == code.lower()),
            None
        )
        if barang:
            self._add_to_cart(barang)
            self.search_input.clear()
        else:
            QMessageBox.information(self, "Tidak Ditemukan", f"Barang dengan kode '{code}' tidak ditemukan.")

    def _update_cart_qty(self, item: CartItem, new_qty: int):
        if new_qty <= 0:
            self._remove_from_cart(item)
            return

        if new_qty > item.stok_available:
            QMessageBox.warning(
                self, "Stok Terbatas",
                f"Jumlah melebihi stok yang tersedia ({item.stok_available})!"
            )
            return

        item.qty = new_qty
        self._update_cart_display()

    def _remove_from_cart(self, item: CartItem):
        if item in self.cart:
            self.cart.remove(item)
        self._update_cart_display()

    def _clear_cart(self):
        if not self.cart:
            return
        self.cart.clear()
        self._update_cart_display()

    def _update_cart_display(self):
        """Render ulang daftar keranjang belanja & update total"""
        # Clear items
        while self.cart_list_layout.count():
            it = self.cart_list_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        total_items = sum(item.qty for item in self.cart)
        self.item_count_badge.setText(f"{total_items} item")

        if not self.cart:
            empty_box = QFrame()
            empty_box.setStyleSheet("background: transparent; padding: 30px;")
            eb_layout = QVBoxLayout(empty_box)
            eb_layout.setAlignment(Qt.AlignCenter)
            e_icon = QLabel("🛒")
            e_icon.setStyleSheet("font-size: 38px; background: transparent;")
            e_icon.setAlignment(Qt.AlignCenter)
            is_dark = db.get_setting("app_theme", "light") == "dark"
            e_txt = QLabel("Keranjang kosong")
            e_txt.setStyleSheet(f"color: {'#94A3B8' if is_dark else '#64748B'}; font-size: 13px; font-weight: 600; background: transparent;")
            e_txt.setAlignment(Qt.AlignCenter)
            eb_layout.addWidget(e_icon)
            eb_layout.addWidget(e_txt)
            self.cart_list_layout.addWidget(empty_box)
        else:
            for item in self.cart:
                row_widget = CartItemRow(item)
                row_widget.qty_changed.connect(lambda q, it=item: self._update_cart_qty(it, q))
                row_widget.remove_clicked.connect(lambda it=item: self._remove_from_cart(it))
                self.cart_list_layout.addWidget(row_widget)

        # Hitung Subtotal, Pajak PPN dinamis dari pengaturan, Total
        try:
            ppn_rate = float(db.get_setting("tax_default_ppn", "11")) / 100.0
        except ValueError:
            ppn_rate = 0.11

        subtotal = sum(i.subtotal for i in self.cart)
        pajak = subtotal * ppn_rate if subtotal > 0 else 0
        total = subtotal + pajak

        self.tax_lbl.setText(f"PPN ({int(ppn_rate * 100)}%)")
        self.subtotal_val_lbl.setText(format_rupiah(subtotal))
        self.tax_val_lbl.setText(format_rupiah(pajak))
        self.total_val_lbl.setText(format_rupiah(total))

        # Enable/disable checkout button
        self.btn_checkout.setEnabled(len(self.cart) > 0)

    # =========================================================================
    # Quick Cash & Checkout
    # =========================================================================

    def _get_grand_total(self) -> float:
        try:
            ppn_rate = float(db.get_setting("tax_default_ppn", "11")) / 100.0
        except ValueError:
            ppn_rate = 0.11

        subtotal = sum(i.subtotal for i in self.cart)
        pajak = subtotal * ppn_rate if subtotal > 0 else 0
        return subtotal + pajak

    def _on_quick_cash_clicked(self, val):
        total = self._get_grand_total()
        if val == "pas":
            self._nominal_bayar = total
        else:
            self._nominal_bayar = float(val)

        # Beri feedback visual pada tombol checkout
        if self._nominal_bayar >= total > 0:
            kembali = self._nominal_bayar - total
            self.btn_checkout.setText(f"BAYAR SEKARANG (Kembalian {format_rupiah(kembali)})")
        else:
            self.btn_checkout.setText("BAYAR SEKARANG")

    def _do_checkout(self):
        """Proses pembayaran transaksi dengan validasi stok atomik"""
        if not self.cart:
            return

        total = self._get_grand_total()
        bayar = self._nominal_bayar if self._selected_metode == "Tunai" and self._nominal_bayar >= total else total

        self._process_payment(bayar=bayar, metode=self._selected_metode)

    def _process_payment(self, bayar: float, metode: str):
        """
        Proses pembayaran dan simpan transaksi dengan optimistic locking
        """
        total = self._get_grand_total()
        diskon_total = sum((item.harga * item.qty * item.diskon / 100) for item in self.cart)
        kembalian = max(0.0, bayar - total)

        no_invoice = None

        try:
            with db.get_session() as session:
                # Validasi stok terkini secara atomik
                stok_issues = []
                for cart_item in self.cart:
                    if not cart_item.barang_id:
                        continue
                    b = session.query(Barang).filter_by(id=cart_item.barang_id).first()
                    if not b:
                        stok_issues.append(f"Barang '{cart_item.nama}' tidak ditemukan di database.")
                    elif b.stok < cart_item.qty:
                        stok_issues.append(
                            f"Stok '{b.nama}' tidak cukup.\n"
                            f"Tersedia: {b.stok}, diminta: {cart_item.qty}"
                        )

                if stok_issues:
                    raise ValueError("\n\n".join(stok_issues))

                # Generate invoice & tax invoice number
                no_invoice = generate_invoice_number(session)
                try:
                    ppn_rate = float(db.get_setting("tax_default_ppn", "11"))
                except ValueError:
                    ppn_rate = 11.0

                subtotal = sum(i.subtotal for i in self.cart)
                ppn_nominal = subtotal * (ppn_rate / 100.0) if subtotal > 0 else 0
                is_pkp = db.get_setting("tax_is_pkp", "0") == "1"
                no_faktur_pajak = generate_tax_invoice_number(session) if is_pkp else None

                # Simpan transaksi dengan rincian DPP & PPN
                transaksi = Transaksi(
                    no_invoice=no_invoice,
                    kasir_id=auth.current_user.id if auth.current_user else None,
                    total=total,
                    diskon_total=diskon_total,
                    dpp=subtotal,
                    ppn_persen=ppn_rate,
                    ppn_nominal=ppn_nominal,
                    no_faktur_pajak=no_faktur_pajak,
                    bayar=bayar,
                    kembalian=kembalian,
                    metode_bayar=metode,
                    status="selesai",
                    status_bayar="lunas"
                )
                session.add(transaksi)
                session.flush()

                # Simpan detail dan kurangi stok
                for cart_item in self.cart:
                    detail = TransaksiDetail(
                        transaksi_id=transaksi.id,
                        barang_id=cart_item.barang_id,
                        nama_barang=cart_item.nama,
                        kode_barang=cart_item.kode,
                        qty=cart_item.qty,
                        harga=cart_item.harga,
                        diskon=cart_item.diskon,
                        subtotal=cart_item.subtotal
                    )
                    session.add(detail)

                    b = session.query(Barang).filter_by(id=cart_item.barang_id).first()
                    if b:
                        b.stok -= cart_item.qty

        except ValueError as e:
            QMessageBox.warning(
                self, "Stok Tidak Cukup ⚠️",
                f"Transaksi dibatalkan karena:\n\n{e}\n\n"
                "Silakan perbarui keranjang dan coba lagi."
            )
            self._load_barang()
            return
        except Exception as e:
            QMessageBox.critical(
                self, "Error Transaksi",
                f"Transaksi gagal disimpan:\n{e}"
            )
            return

        # Cetak struk & buka drawer
        self._print_receipt(no_invoice)
        try:
            DrawerService().open_drawer()
        except Exception:
            pass

        # Tampilkan konfirmasi sukses yang bersih dengan opsi Cetak Faktur PDF
        msg = QMessageBox(self)
        msg.setWindowTitle("Transaksi Berhasil ✅")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f"Transaksi <b>{no_invoice}</b> berhasil disimpan!\n\n"
            f"Total: {format_rupiah(total)}\n"
            f"Bayar ({metode}): {format_rupiah(bayar)}\n"
            f"Kembalian: {format_rupiah(kembalian)}"
        )
        btn_ok = msg.addButton("Selesai", QMessageBox.AcceptRole)
        btn_pdf = msg.addButton("📄 Cetak Faktur (A4 PDF)", QMessageBox.ActionRole)
        msg.exec_()

        if msg.clickedButton() == btn_pdf:
            self._export_faktur_pdf(no_invoice)

        # Reset cart & refresh
        self.cart.clear()
        self._nominal_bayar = 0.0
        self.btn_checkout.setText("BAYAR SEKARANG")
        self._update_cart_display()
        self._load_barang()
        self.transaction_completed.emit()

    def _export_faktur_pdf(self, no_invoice: str):
        """Ekspor faktur penjualan ke file PDF A4"""
        if not no_invoice:
            return
        with db.get_session() as session:
            t = session.query(Transaksi).filter_by(no_invoice=no_invoice).first()
            if not t:
                return
            html = InvoicePdfService.generate_sales_invoice_html(t)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan Faktur Penjualan (PDF)",
                f"Faktur_Penjualan_{no_invoice}.pdf",
                "PDF Files (*.pdf)"
            )
            if file_path:
                ok = InvoicePdfService.save_html_to_pdf(html, file_path)
                if ok:
                    QMessageBox.information(self, "Sukses", f"Faktur Penjualan A4 PDF berhasil disimpan ke:\n{file_path}")
                else:
                    QMessageBox.critical(self, "Gagal", "Gagal menyimpan file PDF.")

    def _print_receipt(self, no_invoice: str):
        """Cetak struk transaksi"""
        if not no_invoice:
            return
        with db.get_session() as session:
            transaksi = session.query(Transaksi).filter_by(no_invoice=no_invoice).first()
            if transaksi:
                PrinterService().print_receipt(transaksi)

    def refresh(self):
        self._load_barang()
