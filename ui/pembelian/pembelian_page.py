"""
KasirKu Modul Faktur Pembelian & Supplier
Mengelola Purchase Order / Faktur Pembelian ke vendor,
restock otomatis ke inventaris, dan master data supplier.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QDialog, QDateEdit,
    QFormLayout, QTabWidget, QSpinBox, QDoubleSpinBox,
    QFileDialog, QAbstractItemView, QTextEdit
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QCursor

from database.db import db
from database.models import Supplier, Pembelian, PembelianDetail, Barang
from auth.auth_manager import auth
from utils.helpers import (
    format_rupiah, format_tanggal, format_datetime,
    generate_po_number, generate_supplier_code
)
from services.invoice_pdf_service import InvoicePdfService
from ui.pembelian.retur_pembelian_dialog import ReturPembelianDialog
from datetime import datetime, date


class SupplierDialog(QDialog):
    """Dialog Tambah / Edit Supplier"""
    saved = pyqtSignal()

    def __init__(self, supplier: Supplier = None, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Tambah Supplier Baru")
        self.setFixedSize(480, 500)
        self.setModal(True)
        self._setup_ui()
        if supplier:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = QLabel("🏢 " + ("Edit Data Supplier" if self.supplier else "Tambah Data Supplier"))
        header.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(header)

        form_frame = QFrame()
        form_frame.setObjectName("card")
        form = QFormLayout(form_frame)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.kode_input = QLineEdit()
        self.kode_input.setPlaceholderText("Kode otomatis (SUPxxx)")
        self.kode_input.setReadOnly(True)
        with db.get_session() as session:
            self.kode_input.setText(self.supplier.kode if self.supplier else generate_supplier_code(session))

        self.nama_input = QLineEdit()
        self.nama_input.setPlaceholderText("Nama Perusahaan / Supplier (Wajib)")

        self.kontak_input = QLineEdit()
        self.kontak_input.setPlaceholderText("Nama Kontak Person / Sales")

        self.telepon_input = QLineEdit()
        self.telepon_input.setPlaceholderText("Nomor Telepon / HP")

        self.npwp_input = QLineEdit()
        self.npwp_input.setPlaceholderText("NPWP Supplier (Opsional untuk Faktur Pajak)")

        self.alamat_input = QTextEdit()
        self.alamat_input.setPlaceholderText("Alamat kantor / gudang supplier")
        self.alamat_input.setMaximumHeight(70)

        form.addRow("Kode:", self.kode_input)
        form.addRow("Nama Supplier:*", self.nama_input)
        form.addRow("Kontak Person:", self.kontak_input)
        form.addRow("No. Telepon:", self.telepon_input)
        form.addRow("NPWP:", self.npwp_input)
        form.addRow("Alamat:", self.alamat_input)
        layout.addWidget(form_frame)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("💾 Simpan Supplier")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _load_data(self):
        self.nama_input.setText(self.supplier.nama)
        self.kontak_input.setText(self.supplier.kontak or "")
        self.telepon_input.setText(self.supplier.telepon or "")
        self.npwp_input.setText(self.supplier.npwp or "")
        self.alamat_input.setText(self.supplier.alamat or "")

    def _save(self):
        nama = self.nama_input.text().strip()
        if not nama:
            QMessageBox.warning(self, "Validasi", "Nama supplier wajib diisi!")
            return

        with db.get_session() as session:
            if self.supplier:
                s = session.query(Supplier).get(self.supplier.id)
                if s:
                    s.nama = nama
                    s.kontak = self.kontak_input.text().strip()
                    s.telepon = self.telepon_input.text().strip()
                    s.npwp = self.npwp_input.text().strip()
                    s.alamat = self.alamat_input.toPlainText().strip()
            else:
                s = Supplier(
                    kode=self.kode_input.text().strip() or generate_supplier_code(session),
                    nama=nama,
                    kontak=self.kontak_input.text().strip(),
                    telepon=self.telepon_input.text().strip(),
                    npwp=self.npwp_input.text().strip(),
                    alamat=self.alamat_input.toPlainText().strip()
                )
                session.add(s)

        self.saved.emit()
        self.accept()


class PembelianPage(QWidget):
    """Halaman Utama Faktur Pembelian (PO), Restock Barang, & Supplier"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cart_items = []  # list of dict: {barang_id, kode, nama, qty, harga_beli, subtotal}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("🧾 Faktur Pembelian & PO Supplier")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_riwayat_tab(), "📋 Riwayat Faktur Pembelian")
        self.tabs.addTab(self._create_input_tab(), "➕ Input Faktur Baru (Restock)")
        self.tabs.addTab(self._create_supplier_tab(), "🏢 Master Supplier")
        layout.addWidget(self.tabs)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1: RIWAYAT FAKTUR PEMBELIAN
    # ──────────────────────────────────────────────────────────────────────────
    def _create_riwayat_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        # Filter row
        filter_row = QHBoxLayout()
        self.search_po_input = QLineEdit()
        self.search_po_input.setPlaceholderText("🔍 Cari No PO / No Faktur / Supplier...")
        self.search_po_input.setFixedHeight(36)
        self.search_po_input.textChanged.connect(self._filter_pembelian_table)
        filter_row.addWidget(self.search_po_input, 2)

        self.filter_status_combo = QComboBox()
        self.filter_status_combo.addItems(["Semua Status", "Lunas", "Tempo"])
        self.filter_status_combo.setFixedHeight(36)
        self.filter_status_combo.currentIndexChanged.connect(self._filter_pembelian_table)
        filter_row.addWidget(self.filter_status_combo, 1)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self._load_pembelian_data)
        filter_row.addWidget(btn_refresh)
        layout.addLayout(filter_row)

        # Table
        self.po_table = QTableWidget()
        self.po_table.setColumnCount(8)
        self.po_table.setHorizontalHeaderLabels([
            "No PO", "No Faktur Vendor", "Tanggal", "Supplier", "Total DPP", "PPN Masukan", "Total Akhir", "Status Bayar"
        ])
        self.po_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.po_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.po_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.po_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.po_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.po_table)

        # Actions
        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_cetak_po = QPushButton("📄 Cetak Faktur PO (A4 / PDF)")
        self.btn_cetak_po.setObjectName("btn_primary")
        self.btn_cetak_po.setFixedHeight(38)
        self.btn_cetak_po.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cetak_po.clicked.connect(self._cetak_selected_po)
        action_row.addWidget(self.btn_cetak_po)

        self.btn_lunasi_tempo = QPushButton("💳 Lunasi Faktur Tempo")
        self.btn_lunasi_tempo.setFixedHeight(38)
        self.btn_lunasi_tempo.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_lunasi_tempo.clicked.connect(self._lunasi_selected_tempo)
        action_row.addWidget(self.btn_lunasi_tempo)

        self.btn_retur_po = QPushButton("↩️ Retur ke Supplier")
        self.btn_retur_po.setObjectName("btn_warning")
        self.btn_retur_po.setFixedHeight(38)
        self.btn_retur_po.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_retur_po.clicked.connect(self._retur_selected_pembelian)
        action_row.addWidget(self.btn_retur_po)

        layout.addLayout(action_row)
        return w

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2: INPUT FAKTUR PEMBELIAN BARU (RESTOCK STOK)
    # ──────────────────────────────────────────────────────────────────────────
    def _create_input_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(12)

        # Form Header Info (Supplier, No Faktur Vendor, No PO, Tanggal, Status)
        header_card = QFrame()
        header_card.setObjectName("card")
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(14, 12, 14, 12)

        row1 = QHBoxLayout()
        self.in_supplier_combo = QComboBox()
        self.in_supplier_combo.setFixedHeight(36)

        btn_tambah_sup = QPushButton("+ Supplier")
        btn_tambah_sup.setFixedHeight(36)
        btn_tambah_sup.clicked.connect(self._tambah_supplier_quick)

        self.in_no_po = QLineEdit()
        self.in_no_po.setPlaceholderText("No PO Otomatis")
        self.in_no_po.setReadOnly(True)
        self.in_no_po.setFixedHeight(36)

        self.in_no_faktur = QLineEdit()
        self.in_no_faktur.setPlaceholderText("Nomor Faktur Vendor / Surat Jalan")
        self.in_no_faktur.setFixedHeight(36)

        row1.addWidget(QLabel("Supplier:"))
        row1.addWidget(self.in_supplier_combo, 2)
        row1.addWidget(btn_tambah_sup)
        row1.addWidget(QLabel("No PO:"))
        row1.addWidget(self.in_no_po, 1)
        row1.addWidget(QLabel("No Faktur Vendor:"))
        row1.addWidget(self.in_no_faktur, 1)
        h_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.in_tgl_masuk = QDateEdit()
        self.in_tgl_masuk.setCalendarPopup(True)
        self.in_tgl_masuk.setDate(QDate.currentDate())
        self.in_tgl_masuk.setFixedHeight(36)

        self.in_jatuh_tempo = QDateEdit()
        self.in_jatuh_tempo.setCalendarPopup(True)
        self.in_jatuh_tempo.setDate(QDate.currentDate().addDays(14))
        self.in_jatuh_tempo.setFixedHeight(36)

        self.in_status_bayar = QComboBox()
        self.in_status_bayar.addItems(["Lunas", "Tempo"])
        self.in_status_bayar.setFixedHeight(36)

        self.in_metode_bayar = QComboBox()
        self.in_metode_bayar.addItems(["Transfer Bank", "Tunai / Cash"])
        self.in_metode_bayar.setFixedHeight(36)

        row2.addWidget(QLabel("Tgl Masuk:"))
        row2.addWidget(self.in_tgl_masuk, 1)
        row2.addWidget(QLabel("Jatuh Tempo:"))
        row2.addWidget(self.in_jatuh_tempo, 1)
        row2.addWidget(QLabel("Status Bayar:"))
        row2.addWidget(self.in_status_bayar, 1)
        row2.addWidget(QLabel("Metode:"))
        row2.addWidget(self.in_metode_bayar, 1)
        h_layout.addLayout(row2)
        layout.addWidget(header_card)

        # Baris Input Produk ke Keranjang Pembelian
        add_item_card = QFrame()
        add_item_card.setObjectName("card")
        add_layout = QHBoxLayout(add_item_card)
        add_layout.setContentsMargins(14, 10, 14, 10)

        self.in_barang_combo = QComboBox()
        self.in_barang_combo.setFixedHeight(36)
        self.in_barang_combo.currentIndexChanged.connect(self._on_barang_selected)

        self.in_qty = QSpinBox()
        self.in_qty.setRange(1, 100000)
        self.in_qty.setValue(1)
        self.in_qty.setFixedHeight(36)

        self.in_harga_beli = QDoubleSpinBox()
        self.in_harga_beli.setRange(0, 1000000000)
        self.in_harga_beli.setSingleStep(1000)
        self.in_harga_beli.setFixedHeight(36)
        self.in_harga_beli.setPrefix("Rp ")

        btn_tambah_item = QPushButton("➕ Tambah ke Faktur")
        btn_tambah_item.setObjectName("btn_primary")
        btn_tambah_item.setFixedHeight(36)
        btn_tambah_item.clicked.connect(self._tambah_item_ke_keranjang)

        add_layout.addWidget(QLabel("Pilih Barang:"))
        add_layout.addWidget(self.in_barang_combo, 3)
        add_layout.addWidget(QLabel("Qty Masuk:"))
        add_layout.addWidget(self.in_qty, 1)
        add_layout.addWidget(QLabel("Harga Beli:"))
        add_layout.addWidget(self.in_harga_beli, 2)
        add_layout.addWidget(btn_tambah_item, 1)
        layout.addWidget(add_item_card)

        # Tabel Item Pembelian
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels([
            "Kode", "Nama Barang", "Qty", "Harga Beli Satuan", "Subtotal", "Aksi"
        ])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.cart_table, 1)

        # Bottom: Kalkulasi Pajak & Simpan
        bottom_card = QFrame()
        bottom_card.setObjectName("card")
        bot_layout = QHBoxLayout(bottom_card)
        bot_layout.setContentsMargins(14, 12, 14, 12)

        tax_box = QHBoxLayout()
        tax_box.setSpacing(10)
        self.in_ppn_check = QComboBox()
        self.in_ppn_check.addItems(["Non-PPN (0%)", "PPN 11%", "PPN 12%"])
        self.in_ppn_check.setFixedHeight(36)
        self.in_ppn_check.currentIndexChanged.connect(self._hitung_kalkulasi_total)

        self.in_catatan = QLineEdit()
        self.in_catatan.setPlaceholderText("Catatan pembelian / penerimaan gudang...")
        self.in_catatan.setFixedHeight(36)

        tax_box.addWidget(QLabel("Pajak Masukan:"))
        tax_box.addWidget(self.in_ppn_check)
        tax_box.addWidget(QLabel("Catatan:"))
        tax_box.addWidget(self.in_catatan, 2)
        bot_layout.addLayout(tax_box, 2)

        # Ringkasan Total
        summary_box = QVBoxLayout()
        self.lbl_subtotal = QLabel("DPP: Rp 0")
        self.lbl_subtotal.setStyleSheet("font-weight: 600; color: #64748B;")
        self.lbl_ppn = QLabel("PPN: Rp 0")
        self.lbl_ppn.setStyleSheet("font-weight: 600; color: #64748B;")
        self.lbl_grand_total = QLabel("Total: Rp 0")
        self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: 900; color: #10B981;")

        summary_box.addWidget(self.lbl_subtotal)
        summary_box.addWidget(self.lbl_ppn)
        summary_box.addWidget(self.lbl_grand_total)
        bot_layout.addLayout(summary_box, 1)

        btn_simpan_faktur = QPushButton("💾 Simpan Faktur & Tambah Stok")
        btn_simpan_faktur.setObjectName("btn_primary")
        btn_simpan_faktur.setFixedHeight(46)
        btn_simpan_faktur.setCursor(QCursor(Qt.PointingHandCursor))
        btn_simpan_faktur.clicked.connect(self._simpan_faktur_pembelian)
        bot_layout.addWidget(btn_simpan_faktur, 1)

        layout.addWidget(bottom_card)
        return w

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3: MASTER DATA SUPPLIER
    # ──────────────────────────────────────────────────────────────────────────
    def _create_supplier_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.search_sup_input = QLineEdit()
        self.search_sup_input.setPlaceholderText("🔍 Cari Nama / Kontak / NPWP Supplier...")
        self.search_sup_input.setFixedHeight(36)
        self.search_sup_input.textChanged.connect(self._filter_supplier_table)
        top_row.addWidget(self.search_sup_input, 2)

        btn_add_sup = QPushButton("➕ Tambah Supplier")
        btn_add_sup.setObjectName("btn_primary")
        btn_add_sup.setFixedHeight(36)
        btn_add_sup.clicked.connect(self._tambah_supplier_quick)
        top_row.addWidget(btn_add_sup)
        layout.addLayout(top_row)

        self.sup_table = QTableWidget()
        self.sup_table.setColumnCount(6)
        self.sup_table.setHorizontalHeaderLabels([
            "Kode", "Nama Supplier", "Kontak Person", "Telepon", "NPWP", "Alamat"
        ])
        self.sup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.sup_table)

        btn_edit_sup = QPushButton("✏️ Edit Supplier Terpilih")
        btn_edit_sup.setFixedHeight(36)
        btn_edit_sup.clicked.connect(self._edit_selected_supplier)
        layout.addWidget(btn_edit_sup, alignment=Qt.AlignRight)

        return w

    # ──────────────────────────────────────────────────────────────────────────
    # LOGIKA DAN AKSI
    # ──────────────────────────────────────────────────────────────────────────
    def refresh(self):
        """Muat ulang seluruh data"""
        self._load_pembelian_data()
        self._load_supplier_data()
        self._load_barang_options()
        with db.get_session() as session:
            self.in_no_po.setText(generate_po_number(session))

    def _load_supplier_data(self):
        with db.get_session() as session:
            suppliers = session.query(Supplier).filter_by(aktif=True).order_by(Supplier.nama.asc()).all()
            self._suppliers_cache = suppliers

            # Update dropdown supplier di tab 2
            self.in_supplier_combo.clear()
            for s in suppliers:
                self.in_supplier_combo.addItem(f"{s.kode} - {s.nama}", s.id)

            # Update tabel supplier di tab 3
            self.sup_table.setRowCount(len(suppliers))
            for i, s in enumerate(suppliers):
                self.sup_table.setItem(i, 0, QTableWidgetItem(s.kode))
                self.sup_table.setItem(i, 1, QTableWidgetItem(s.nama))
                self.sup_table.setItem(i, 2, QTableWidgetItem(s.kontak or "-"))
                self.sup_table.setItem(i, 3, QTableWidgetItem(s.telepon or "-"))
                self.sup_table.setItem(i, 4, QTableWidgetItem(s.npwp or "-"))
                self.sup_table.setItem(i, 5, QTableWidgetItem(s.alamat or "-"))

    def _load_barang_options(self):
        with db.get_session() as session:
            barangs = session.query(Barang).filter_by(aktif=True).order_by(Barang.nama.asc()).all()
            self._barang_map = {b.id: b for b in barangs}
            self.in_barang_combo.clear()
            for b in barangs:
                self.in_barang_combo.addItem(f"{b.kode} - {b.nama} (Stok: {b.stok})", b.id)

    def _on_barang_selected(self):
        barang_id = self.in_barang_combo.currentData()
        if barang_id and hasattr(self, '_barang_map') and barang_id in self._barang_map:
            b = self._barang_map[barang_id]
            self.in_harga_beli.setValue(b.harga_beli or 0)

    def _tambah_item_ke_keranjang(self):
        barang_id = self.in_barang_combo.currentData()
        if not barang_id or barang_id not in self._barang_map:
            return

        b = self._barang_map[barang_id]
        qty = self.in_qty.value()
        harga_beli = self.in_harga_beli.value()
        subtotal = qty * harga_beli

        # Cek jika barang sudah ada di keranjang, akumulasi qty
        for item in self._cart_items:
            if item["barang_id"] == b.id:
                item["qty"] += qty
                item["harga_beli"] = harga_beli
                item["subtotal"] = item["qty"] * harga_beli
                self._render_cart_table()
                self._hitung_kalkulasi_total()
                return

        self._cart_items.append({
            "barang_id": b.id,
            "kode": b.kode,
            "nama": b.nama,
            "qty": qty,
            "harga_beli": harga_beli,
            "subtotal": subtotal
        })
        self._render_cart_table()
        self._hitung_kalkulasi_total()

    def _render_cart_table(self):
        self.cart_table.setRowCount(len(self._cart_items))
        for i, itm in enumerate(self._cart_items):
            self.cart_table.setItem(i, 0, QTableWidgetItem(itm["kode"]))
            self.cart_table.setItem(i, 1, QTableWidgetItem(itm["nama"]))
            self.cart_table.setItem(i, 2, QTableWidgetItem(str(itm["qty"])))
            self.cart_table.setItem(i, 3, QTableWidgetItem(format_rupiah(itm["harga_beli"])))
            self.cart_table.setItem(i, 4, QTableWidgetItem(format_rupiah(itm["subtotal"])))

            btn_del = QPushButton("❌")
            btn_del.setFixedWidth(36)
            btn_del.clicked.connect(lambda _, idx=i: self._hapus_cart_item(idx))
            self.cart_table.setCellWidget(i, 5, btn_del)

    def _hapus_cart_item(self, idx: int):
        if 0 <= idx < len(self._cart_items):
            self._cart_items.pop(idx)
            self._render_cart_table()
            self._hitung_kalkulasi_total()

    def _hitung_kalkulasi_total(self):
        dpp = sum(itm["subtotal"] for itm in self._cart_items)
        ppn_choice = self.in_ppn_check.currentIndex()
        ppn_rate = 0.11 if ppn_choice == 1 else (0.12 if ppn_choice == 2 else 0.0)
        ppn_nominal = dpp * ppn_rate
        grand_total = dpp + ppn_nominal

        self.lbl_subtotal.setText(f"DPP: {format_rupiah(dpp)}")
        self.lbl_ppn.setText(f"PPN ({int(ppn_rate*100)}%): {format_rupiah(ppn_nominal)}")
        self.lbl_grand_total.setText(f"Total: {format_rupiah(grand_total)}")

    def _simpan_faktur_pembelian(self):
        if not self._cart_items:
            QMessageBox.warning(self, "Keranjang Kosong", "Tambahkan minimal satu barang ke dalam faktur pembelian!")
            return

        no_faktur = self.in_no_faktur.text().strip()
        if not no_faktur:
            QMessageBox.warning(self, "Validasi", "Nomor Faktur Vendor / Surat Jalan wajib diisi!")
            return

        supplier_id = self.in_supplier_combo.currentData()
        status_bayar = "lunas" if self.in_status_bayar.currentIndex() == 0 else "tempo"
        metode = "transfer" if self.in_metode_bayar.currentIndex() == 0 else "cash"

        dpp = sum(itm["subtotal"] for itm in self._cart_items)
        ppn_choice = self.in_ppn_check.currentIndex()
        ppn_persen = 11.0 if ppn_choice == 1 else (12.0 if ppn_choice == 2 else 0.0)
        ppn_nominal = dpp * (ppn_persen / 100.0)
        grand_total = dpp + ppn_nominal

        with db.get_session() as session:
            no_po = generate_po_number(session)
            tgl_masuk = self.in_tgl_masuk.date().toPyDate()
            tgl_dt = datetime.combine(tgl_masuk, datetime.now().time())
            jt_date = self.in_jatuh_tempo.date().toPyDate()
            jt_dt = datetime.combine(jt_date, datetime.min.time())

            user_id = auth.current_user.id if auth.current_user else None

            pembelian = Pembelian(
                no_faktur=no_faktur,
                no_po=no_po,
                supplier_id=supplier_id,
                tanggal=tgl_dt,
                jatuh_tempo=jt_dt if status_bayar == "tempo" else None,
                subtotal=dpp,
                dpp=dpp,
                ppn_persen=ppn_persen,
                ppn_nominal=ppn_nominal,
                total=grand_total,
                status_bayar=status_bayar,
                metode_bayar=metode,
                catatan=self.in_catatan.text().strip(),
                user_id=user_id
            )
            session.add(pembelian)
            session.flush()

            # Tambahkan detail dan OTOMATIS TAMBAH STOK BARANG DI DATABASE
            for itm in self._cart_items:
                detail = PembelianDetail(
                    pembelian_id=pembelian.id,
                    barang_id=itm["barang_id"],
                    kode_barang=itm["kode"],
                    nama_barang=itm["nama"],
                    qty=itm["qty"],
                    harga_beli=itm["harga_beli"],
                    subtotal=itm["subtotal"]
                )
                session.add(detail)

                # Restock barang otomatis
                b = session.query(Barang).get(itm["barang_id"])
                if b:
                    b.stok += itm["qty"]
                    b.harga_beli = itm["harga_beli"]  # Update HPP terbaru

            session.commit()
            created_po = no_po

        # Reset form
        self._cart_items.clear()
        self._render_cart_table()
        self._hitung_kalkulasi_total()
        self.in_no_faktur.clear()
        self.in_catatan.clear()
        self.refresh()

        # Konfirmasi Sukses & Tawarkan Cetak PO
        reply = QMessageBox.question(
            self,
            "Pembelian Berhasil",
            f"Faktur Pembelian <b>{created_po}</b> berhasil disimpan!\n"
            f"Stok barang telah otomatis ditambahkan ke inventaris.\n\n"
            f"Apakah Anda ingin mencetak / menyimpan lembar Faktur PO (A4 PDF)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._cetak_po_by_no(created_po)

        self.tabs.setCurrentIndex(0)

    def _load_pembelian_data(self):
        with db.get_session() as session:
            pembelians = session.query(Pembelian).order_by(Pembelian.tanggal.desc()).all()
            self._pembelian_cache = pembelians
            self._filter_pembelian_table()

    def _filter_pembelian_table(self):
        if not hasattr(self, '_pembelian_cache'):
            return

        q = self.search_po_input.text().strip().lower()
        filter_st = self.filter_status_combo.currentText().lower()

        filtered = []
        for p in self._pembelian_cache:
            sup_name = p.supplier.nama.lower() if p.supplier else ""
            matches_q = (
                q in p.no_po.lower() or
                q in p.no_faktur.lower() or
                q in sup_name
            ) if q else True

            matches_st = True
            if filter_st == "lunas":
                matches_st = (p.status_bayar == "lunas")
            elif filter_st == "tempo":
                matches_st = (p.status_bayar == "tempo")

            if matches_q and matches_st:
                filtered.append(p)

        self.po_table.setRowCount(len(filtered))
        self._filtered_pembelian = filtered

        for i, p in enumerate(filtered):
            sup_name = p.supplier.nama if p.supplier else "Umum"
            st_text = "LUNAS" if p.status_bayar == "lunas" else "TEMPO (HUTANG)"

            self.po_table.setItem(i, 0, QTableWidgetItem(p.no_po))
            self.po_table.setItem(i, 1, QTableWidgetItem(p.no_faktur))
            self.po_table.setItem(i, 2, QTableWidgetItem(format_tanggal(p.tanggal)))
            self.po_table.setItem(i, 3, QTableWidgetItem(sup_name))
            self.po_table.setItem(i, 4, QTableWidgetItem(format_rupiah(p.dpp or p.subtotal)))
            self.po_table.setItem(i, 5, QTableWidgetItem(format_rupiah(p.ppn_nominal or 0)))
            self.po_table.setItem(i, 6, QTableWidgetItem(format_rupiah(p.total)))

            st_item = QTableWidgetItem(st_text)
            if p.status_bayar == "tempo":
                st_item.setForeground(QColor("#EF4444"))
            else:
                st_item.setForeground(QColor("#10B981"))
            self.po_table.setItem(i, 7, st_item)

    def _cetak_selected_po(self):
        row = self.po_table.currentRow()
        if row < 0 or row >= len(self._filtered_pembelian):
            QMessageBox.information(self, "Pilih Data", "Pilih salah satu faktur pembelian di tabel untuk dicetak.")
            return
        p = self._filtered_pembelian[row]
        self._cetak_po_by_no(p.no_po)

    def _cetak_po_by_no(self, no_po: str):
        with db.get_session() as session:
            pembelian = session.query(Pembelian).filter_by(no_po=no_po).first()
            if not pembelian:
                QMessageBox.warning(self, "Error", f"Data pembelian {no_po} tidak ditemukan.")
                return

            html = InvoicePdfService.generate_purchase_order_html(pembelian)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan Faktur Pembelian (PDF)",
                f"Faktur_PO_{no_po}.pdf",
                "PDF Files (*.pdf)"
            )
            if file_path:
                ok = InvoicePdfService.save_html_to_pdf(html, file_path)
                if ok:
                    QMessageBox.information(self, "Sukses", f"Faktur PO berhasil disimpan ke:\n{file_path}")
                else:
                    QMessageBox.critical(self, "Gagal", "Gagal menyimpan file PDF.")

    def _lunasi_selected_tempo(self):
        row = self.po_table.currentRow()
        if row < 0 or row >= len(self._filtered_pembelian):
            QMessageBox.information(self, "Pilih Data", "Pilih faktur pembelian bertatus tempo yang ingin dilunasi.")
            return
        p = self._filtered_pembelian[row]
        if p.status_bayar == "lunas":
            QMessageBox.information(self, "Informasi", "Faktur pembelian ini sudah lunas.")
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi Pelunasan",
            f"Tandai faktur pembelian <b>{p.no_po}</b> ({format_rupiah(p.total)}) sebagai LUNAS?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with db.get_session() as session:
                target = session.query(Pembelian).get(p.id)
                if target:
                    target.status_bayar = "lunas"
                    session.commit()
            self._load_pembelian_data()
            QMessageBox.information(self, "Sukses", "Status pembayaran berhasil diubah menjadi Lunas.")

    def _retur_selected_pembelian(self):
        row = self.po_table.currentRow()
        if row < 0 or row >= len(self._filtered_pembelian):
            QMessageBox.information(self, "Pilih Data", "Pilih salah satu faktur pembelian di tabel untuk diretur.")
            return
        p = self._filtered_pembelian[row]
        dlg = ReturPembelianDialog(p.id, parent=self)
        dlg.retur_processed.connect(self._load_pembelian_data)
        dlg.exec_()

    def _tambah_supplier_quick(self):
        dlg = SupplierDialog(parent=self)
        dlg.saved.connect(self._load_supplier_data)
        dlg.exec_()

    def _edit_selected_supplier(self):
        row = self.sup_table.currentRow()
        if row < 0 or not hasattr(self, '_suppliers_cache') or row >= len(self._suppliers_cache):
            QMessageBox.information(self, "Pilih Data", "Pilih salah satu supplier di tabel untuk diedit.")
            return
        s = self._suppliers_cache[row]
        dlg = SupplierDialog(supplier=s, parent=self)
        dlg.saved.connect(self._load_supplier_data)
        dlg.exec_()

    def _filter_supplier_table(self):
        q = self.search_sup_input.text().strip().lower()
        if not hasattr(self, '_suppliers_cache'):
            return
        filtered = [
            s for s in self._suppliers_cache
            if q in s.nama.lower() or q in (s.kontak or "").lower() or q in (s.npwp or "").lower()
        ]
        self.sup_table.setRowCount(len(filtered))
        for i, s in enumerate(filtered):
            self.sup_table.setItem(i, 0, QTableWidgetItem(s.kode))
            self.sup_table.setItem(i, 1, QTableWidgetItem(s.nama))
            self.sup_table.setItem(i, 2, QTableWidgetItem(s.kontak or "-"))
            self.sup_table.setItem(i, 3, QTableWidgetItem(s.telepon or "-"))
            self.sup_table.setItem(i, 4, QTableWidgetItem(s.npwp or "-"))
            self.sup_table.setItem(i, 5, QTableWidgetItem(s.alamat or "-"))
