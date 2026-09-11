"""
KasirKu Kasir Page (POS)
Halaman utama transaksi penjualan - layout 3 panel
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QSpinBox, QMessageBox, QSplitter,
    QAbstractItemView, QScrollArea, QListWidget, QListWidgetItem,
    QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QKeySequence

from database.db import db
from database.models import Barang, Transaksi, TransaksiDetail
from auth.auth_manager import auth
from utils.helpers import format_rupiah, generate_invoice_number, format_datetime
from services.printer_service import PrinterService
from services.drawer_service import DrawerService
from .payment_dialog import PaymentDialog


class CartItem:
    def __init__(self, barang_id, kode, nama, harga, stok_available):
        self.barang_id = barang_id
        self.kode = kode
        self.nama = nama
        self.harga = harga
        self.qty = 1
        self.diskon = 0.0  # persen
        self.stok_available = stok_available

    @property
    def subtotal(self):
        diskon_amount = self.harga * (self.diskon / 100)
        return (self.harga - diskon_amount) * self.qty

    @property
    def harga_after_discount(self):
        return self.harga * (1 - self.diskon / 100)


class KasirPage(QWidget):
    """Halaman POS kasir"""
    transaction_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart: list[CartItem] = []
        self._all_barang = []
        self._setup_ui()
        self._load_barang()
        self._setup_shortcuts()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== LEFT PANEL: Product search =====
        left = QFrame()
        left.setFixedWidth(300)
        left.setStyleSheet("""
            QFrame {
                background: #1A1D27;
                border-right: 1px solid #2D3250;
            }
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Search header
        search_header = QFrame()
        search_header.setFixedHeight(64)
        search_header.setStyleSheet("""
            QFrame {
                background: #21263A;
                border-bottom: 1px solid #2D3250;
            }
        """)
        sh_layout = QVBoxLayout(search_header)
        sh_layout.setContentsMargins(12, 12, 12, 12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari / Scan Barcode (F2)")
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #2D3250;
                border: 1px solid #3D4466;
                border-radius: 8px;
                padding: 0 12px;
                color: #F1F5F9;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #6C63FF; }
        """)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.returnPressed.connect(self._add_by_barcode)
        sh_layout.addWidget(self.search_input)
        left_layout.addWidget(search_header)

        # Product list
        self.product_list = QListWidget()
        self.product_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                color: #F1F5F9;
                padding: 0;
                margin: 4px 8px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        self.product_list.itemDoubleClicked.connect(self._add_from_list)
        left_layout.addWidget(self.product_list)
        main_layout.addWidget(left)

        # ===== CENTER PANEL: Cart =====
        center = QFrame()
        center.setStyleSheet("QFrame { background: #0F1117; }")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(16, 16, 16, 16)
        center_layout.setSpacing(12)

        # Invoice number & title
        center_header = QHBoxLayout()
        title_lbl = QLabel("🧾 Keranjang Belanja")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #F1F5F9;")
        center_header.addWidget(title_lbl)
        center_header.addStretch()

        self.invoice_lbl = QLabel("INV-...")
        self.invoice_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        center_header.addWidget(self.invoice_lbl)

        btn_clear = QPushButton("🗑 Hapus Semua")
        btn_clear.setFixedHeight(32)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.1); }
        """)
        btn_clear.clicked.connect(self._clear_cart)
        center_header.addWidget(btn_clear)
        center_layout.addLayout(center_header)

        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(
            ["Nama Barang", "Harga", "Qty", "Diskon%", "Subtotal", ""]
        )
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 70)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(3, 70)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(5, 36)
        self.cart_table.setEditTriggers(QTableWidget.DoubleClicked)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background: #1A1D27;
                border: 1px solid #2D3250;
                border-radius: 10px;
                gridline-color: #2D3250;
                alternate-background-color: #1E2235;
            }
            QTableWidget::item { padding: 8px; color: #F1F5F9; }
            QTableWidget::item:selected { background: #2A2F45; }
            QHeaderView::section {
                background: #21263A; color: #94A3B8;
                padding: 8px; font-size: 11px; font-weight: 600;
                border: none; border-bottom: 2px solid #2D3250;
            }
        """)
        self.cart_table.cellChanged.connect(self._on_cart_cell_changed)
        center_layout.addWidget(self.cart_table)

        # Cart summary
        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                background: #1A1D27;
                border: 1px solid #2D3250;
                border-radius: 10px;
            }
        """)
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(16, 12, 16, 12)

        item_count_lbl = QLabel("Item:")
        item_count_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        summary_layout.addWidget(item_count_lbl)

        self.item_count_lbl = QLabel("0 item")
        self.item_count_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        summary_layout.addWidget(self.item_count_lbl)
        summary_layout.addStretch()

        center_layout.addWidget(summary_frame)
        main_layout.addWidget(center, 1)

        # ===== RIGHT PANEL: Payment summary =====
        right = QFrame()
        right.setFixedWidth(280)
        right.setStyleSheet("""
            QFrame {
                background: #1A1D27;
                border-left: 1px solid #2D3250;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(14)

        pay_title = QLabel("💰 Ringkasan")
        pay_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F1F5F9;")
        right_layout.addWidget(pay_title)

        # Summary rows
        def summary_row(title, value_ref, value_style="color: #F1F5F9;"):
            row = QHBoxLayout()
            lbl = QLabel(title)
            lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
            row.addWidget(lbl)
            row.addStretch()
            val = QLabel(value_ref)
            val.setStyleSheet(f"{value_style} font-size: 13px; font-weight: 600;")
            row.addWidget(val)
            return row, val

        row1, self.subtotal_lbl = summary_row("Subtotal:", "Rp 0")
        right_layout.addLayout(row1)

        row2, self.diskon_lbl = summary_row("Diskon:", "Rp 0", "color: #F59E0B;")
        right_layout.addLayout(row2)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background: #2D3250; max-height: 1px; border: none;")
        right_layout.addWidget(div)

        # Total big
        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background: #21263A;
                border-radius: 10px;
                border: 1px solid #2D3250;
            }
        """)
        total_inner = QVBoxLayout(total_frame)
        total_inner.setContentsMargins(14, 14, 14, 14)
        total_inner.setSpacing(4)
        total_title = QLabel("TOTAL")
        total_title.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
        total_inner.addWidget(total_title)
        self.total_lbl = QLabel("Rp 0")
        self.total_lbl.setStyleSheet(
            "color: #F1F5F9; font-size: 26px; font-weight: 900; background: transparent;"
        )
        total_inner.addWidget(self.total_lbl)
        right_layout.addWidget(total_frame)

        right_layout.addStretch()

        # Pay button (F1)
        self.btn_pay = QPushButton("💳 Bayar (F1)")
        self.btn_pay.setFixedHeight(56)
        self.btn_pay.setEnabled(False)
        self.btn_pay.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10B981, stop:1 #34D399);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 800;
            }
            QPushButton:hover { background: #34D399; }
            QPushButton:pressed { background: #059669; }
            QPushButton:disabled {
                background: #21263A;
                color: #64748B;
            }
        """)
        self.btn_pay.clicked.connect(self._open_payment)
        right_layout.addWidget(self.btn_pay)

        main_layout.addWidget(right)

        # Preview invoice number
        self._update_invoice_preview()

    def _setup_shortcuts(self):
        from PyQt5.QtWidgets import QShortcut
        QShortcut(QKeySequence("F1"), self).activated.connect(self._open_payment)
        QShortcut(QKeySequence("F2"), self).activated.connect(self.search_input.setFocus)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._clear_cart)

    def _update_invoice_preview(self):
        with db.get_session() as session:
            inv = generate_invoice_number(session)
        self.invoice_lbl.setText(inv)

    def _load_barang(self):
        with db.get_session() as session:
            barang_list = session.query(Barang).filter(
                Barang.aktif == True,
                Barang.stok > 0
            ).order_by(Barang.nama).all()
            self._all_barang = [
                {
                    "id": b.id,
                    "kode": b.kode,
                    "barcode": b.barcode or "",
                    "nama": b.nama,
                    "harga": b.harga_jual,
                    "stok": b.stok,
                    "kategori": b.kategori or "",
                }
                for b in barang_list
            ]
        self._render_product_list(self._all_barang)

    def _render_product_list(self, data: list):
        self.product_list.clear()
        for b in data:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, b)
            widget = self._create_product_item_widget(b)
            item.setSizeHint(widget.sizeHint())
            self.product_list.addItem(item)
            self.product_list.setItemWidget(item, widget)

    def _create_product_item_widget(self, b: dict) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #21263A;
                border-radius: 8px;
                border: 1px solid #2D3250;
            }
            QFrame:hover {
                border-color: #6C63FF;
                background: #252B40;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        name_lbl = QLabel(b["nama"])
        name_lbl.setStyleSheet("color: #F1F5F9; font-size: 13px; font-weight: 600; background: transparent;")
        name_lbl.setWordWrap(False)
        layout.addWidget(name_lbl)

        info_row = QHBoxLayout()
        price_lbl = QLabel(format_rupiah(b["harga"]))
        price_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600; background: transparent;")
        info_row.addWidget(price_lbl)
        info_row.addStretch()
        stock_lbl = QLabel(f"Stok: {b['stok']}")
        stock_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        info_row.addWidget(stock_lbl)
        layout.addLayout(info_row)

        return frame

    def _on_search(self, text: str):
        q = text.lower().strip()
        if not q:
            self._render_product_list(self._all_barang)
            return
        filtered = [b for b in self._all_barang if (
            q in b["nama"].lower() or
            q in b["kode"].lower() or
            q in b["barcode"].lower()
        )]
        self._render_product_list(filtered)

    def _add_by_barcode(self):
        """Tambah barang ke keranjang via barcode/kode"""
        text = self.search_input.text().strip()
        if not text:
            return

        # Cari exact match barcode
        match = None
        for b in self._all_barang:
            if b["barcode"] == text or b["kode"] == text:
                match = b
                break

        if match:
            self._add_to_cart(match)
            self.search_input.clear()
        else:
            # Cari partial match - kalau hanya 1 hasil
            filtered = [b for b in self._all_barang if (
                text.lower() in b["nama"].lower() or
                text.lower() in b["kode"].lower()
            )]
            if len(filtered) == 1:
                self._add_to_cart(filtered[0])
                self.search_input.clear()

    def _add_from_list(self, item: QListWidgetItem):
        b = item.data(Qt.UserRole)
        if b:
            self._add_to_cart(b)

    def _add_to_cart(self, b: dict):
        """Tambah barang ke keranjang"""
        # Cek apakah sudah ada di keranjang
        for cart_item in self.cart:
            if cart_item.barang_id == b["id"]:
                if cart_item.qty < cart_item.stok_available:
                    cart_item.qty += 1
                    self._update_cart_table()
                    self._update_totals()
                else:
                    QMessageBox.warning(self, "Stok Tidak Cukup",
                                        f"Stok {b['nama']} hanya {b['stok']} unit!")
                return

        # Cek stok
        if b["stok"] <= 0:
            QMessageBox.warning(self, "Stok Habis", f"Stok {b['nama']} sudah habis!")
            return

        cart_item = CartItem(
            barang_id=b["id"],
            kode=b["kode"],
            nama=b["nama"],
            harga=b["harga"],
            stok_available=b["stok"]
        )
        self.cart.append(cart_item)
        self._update_cart_table()
        self._update_totals()

    def _update_cart_table(self):
        """Update tampilan tabel keranjang"""
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(self.cart))

        for row, item in enumerate(self.cart):
            self.cart_table.setRowHeight(row, 46)

            # Nama
            name_item = QTableWidgetItem(item.nama)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setForeground(QColor("#F1F5F9"))
            self.cart_table.setItem(row, 0, name_item)

            # Harga
            price_item = QTableWidgetItem(format_rupiah(item.harga))
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            price_item.setForeground(QColor("#94A3B8"))
            self.cart_table.setItem(row, 1, price_item)

            # Qty (editable)
            qty_item = QTableWidgetItem(str(item.qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            qty_item.setForeground(QColor("#F1F5F9"))
            self.cart_table.setItem(row, 2, qty_item)

            # Diskon (editable)
            diskon_item = QTableWidgetItem(str(item.diskon))
            diskon_item.setTextAlignment(Qt.AlignCenter)
            diskon_item.setForeground(QColor("#F59E0B"))
            self.cart_table.setItem(row, 3, diskon_item)

            # Subtotal
            sub_item = QTableWidgetItem(format_rupiah(item.subtotal))
            sub_item.setFlags(sub_item.flags() & ~Qt.ItemIsEditable)
            sub_item.setForeground(QColor("#10B981"))
            sub_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.cart_table.setItem(row, 4, sub_item)

            # Delete button
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #64748B;
                    border: 1px solid #2D3250;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #EF4444; color: white; border-color: #EF4444; }
            """)
            del_btn.clicked.connect(lambda _, r=row: self._remove_cart_item(r))
            self.cart_table.setCellWidget(row, 5, del_btn)

        self.cart_table.blockSignals(False)
        self.item_count_lbl.setText(f"{sum(i.qty for i in self.cart)} item")

    def _on_cart_cell_changed(self, row: int, col: int):
        """Update qty/diskon saat sel diedit"""
        if row >= len(self.cart):
            return
        item = self.cart[row]

        if col == 2:  # Qty
            try:
                qty = int(self.cart_table.item(row, col).text())
                if qty <= 0:
                    self._remove_cart_item(row)
                    return
                if qty > item.stok_available:
                    QMessageBox.warning(self, "Stok Tidak Cukup",
                                        f"Stok tersedia: {item.stok_available}")
                    qty = item.stok_available
                item.qty = qty
            except (ValueError, AttributeError):
                pass
        elif col == 3:  # Diskon
            try:
                diskon = float(self.cart_table.item(row, col).text())
                item.diskon = max(0, min(100, diskon))
            except (ValueError, AttributeError):
                pass

        self._update_cart_table()
        self._update_totals()

    def _remove_cart_item(self, row: int):
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self._update_cart_table()
            self._update_totals()

    def _clear_cart(self):
        if not self.cart:
            return
        self.cart.clear()
        self.cart_table.setRowCount(0)
        self._update_totals()
        self._update_invoice_preview()

    def _update_totals(self):
        """Update ringkasan total di panel kanan"""
        subtotal_before = sum(item.harga * item.qty for item in self.cart)
        total_diskon = sum((item.harga * item.qty * item.diskon / 100) for item in self.cart)
        total = sum(item.subtotal for item in self.cart)

        self.subtotal_lbl.setText(format_rupiah(subtotal_before))
        self.diskon_lbl.setText(f"- {format_rupiah(total_diskon)}")
        self.total_lbl.setText(format_rupiah(total))

        self.btn_pay.setEnabled(len(self.cart) > 0)

    def _open_payment(self):
        """Buka dialog pembayaran"""
        if not self.cart:
            return

        total = sum(item.subtotal for item in self.cart)
        dialog = PaymentDialog(total=total, parent=self)
        dialog.payment_confirmed.connect(self._process_payment)
        dialog.exec_()

    def _process_payment(self, bayar: float, metode: str):
        """Proses pembayaran dan simpan transaksi"""
        total = sum(item.subtotal for item in self.cart)
        diskon_total = sum((item.harga * item.qty * item.diskon / 100) for item in self.cart)
        kembalian = bayar - total

        with db.get_session() as session:
            # Generate invoice
            no_invoice = generate_invoice_number(session)

            # Simpan transaksi
            transaksi = Transaksi(
                no_invoice=no_invoice,
                kasir_id=auth.current_user.id if auth.current_user else None,
                total=total,
                diskon_total=diskon_total,
                bayar=bayar,
                kembalian=kembalian,
                metode_bayar=metode,
                status="selesai"
            )
            session.add(transaksi)
            session.flush()  # Dapatkan transaksi ID

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

                # Kurangi stok
                if cart_item.barang_id:
                    b = session.query(Barang).filter_by(id=cart_item.barang_id).first()
                    if b:
                        b.stok -= cart_item.qty

            session.commit()

        # Cetak struk
        self._print_receipt(no_invoice)

        # Buka cash drawer jika cash
        if metode == "cash":
            DrawerService().open_drawer(
                user_id=auth.current_user.id if auth.current_user else None,
                keterangan=f"Auto buka - {no_invoice}"
            )

        # Tampilkan konfirmasi sukses
        msg = QMessageBox(self)
        msg.setWindowTitle("Transaksi Berhasil! ✅")
        msg.setText(
            f"<b>Transaksi Selesai!</b><br><br>"
            f"📋 Invoice: <b>{no_invoice}</b><br>"
            f"💰 Total: <b>{format_rupiah(total)}</b><br>"
            f"💵 Bayar: <b>{format_rupiah(bayar)}</b><br>"
            f"🪙 Kembalian: <b>{format_rupiah(kembalian)}</b>"
        )
        msg.setStyleSheet("""
            QMessageBox { background: #1A1D27; }
            QMessageBox QLabel { color: #F1F5F9; font-size: 13px; }
            QPushButton {
                background: #6C63FF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover { background: #8B84FF; }
        """)
        msg.exec_()

        # Reset keranjang
        self._clear_cart()
        self._load_barang()  # Refresh stok
        self.transaction_completed.emit()

    def _print_receipt(self, no_invoice: str):
        """Cetak struk ke printer"""
        try:
            with db.get_session() as session:
                from database.models import Transaksi
                t = session.query(Transaksi).filter_by(no_invoice=no_invoice).first()
                if t:
                    PrinterService().print_receipt(t)
        except Exception as e:
            # Jangan gagalkan transaksi karena printer error
            print(f"[Printer Warning] {e}")

    def refresh(self):
        self._load_barang()
        self._update_invoice_preview()
