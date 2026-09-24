"""
KasirKu Dialog Retur Pembelian (Purchase Return to Vendor)
Menangani pengembalian barang ke supplier / distributor:
- Mengurangi stok barang di gudang (Barang.stok -= qty_retur)
- Memotong sisa hutang / tempo pembelian atau mencatat refund kas
- Validasi stok toko saat ini mencukupi untuk dikembalikan
"""

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QCursor

from database.db import db
from database.models import Pembelian, ReturPembelian, ReturPembelianDetail, Barang
from auth.auth_manager import auth
from utils.helpers import format_rupiah, format_datetime, generate_retur_pembelian_number


class ReturPembelianDialog(QDialog):
    """Dialog proses Retur Pembelian ke Supplier"""
    retur_processed = pyqtSignal()

    def __init__(self, pembelian_id: int, parent=None):
        super().__init__(parent)
        self.pembelian_id = pembelian_id
        self.pembelian = None
        self.spinboxes = {}
        self.subtotal_labels = {}
        self.item_data = {}

        self.setWindowTitle("↩️ Retur Pembelian ke Supplier")
        self.setMinimumSize(820, 580)
        self.setModal(True)

        self._setup_ui()
        self._load_pembelian()

    def _setup_ui(self):
        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")

        bg_col = "#0F172A" if is_dark else "#FFFFFF"
        text_col = "#F1F5F9" if is_dark else "#0F172A"
        card_bg = "#1E293B" if is_dark else "#F8FAFC"
        border_col = "#334155" if is_dark else "#E2E8F0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
            QFrame#card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 10px;
            }}
            QTableWidget {{
                background-color: {card_bg};
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 8px;
                gridline-color: {border_col};
            }}
            QHeaderView::section {{
                background-color: {'#1E3A8A' if is_dark else '#EFF6FF'};
                color: {'#93C5FD' if is_dark else '#1E40AF'};
                font-weight: 700;
                padding: 6px;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header_row = QHBoxLayout()
        icon_lbl = QLabel("↩️")
        icon_lbl.setStyleSheet("font-size: 24px;")
        header_row.addWidget(icon_lbl)

        header_title = QLabel("Proses Retur Pembelian ke Supplier")
        header_title.setStyleSheet("font-size: 18px; font-weight: 800;")
        header_row.addWidget(header_title)
        header_row.addStretch()

        self.po_badge = QLabel("")
        self.po_badge.setStyleSheet("""
            background: #047857; color: #FFFFFF; font-weight: bold;
            padding: 4px 10px; border-radius: 6px; font-size: 12px;
        """)
        header_row.addWidget(self.po_badge)
        layout.addLayout(header_row)

        # Info PO Card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(14, 10, 14, 10)

        self.lbl_supplier = QLabel("Supplier: -")
        self.lbl_supplier.setStyleSheet("font-weight: 600; font-size: 12px;")
        info_layout.addWidget(self.lbl_supplier)

        self.lbl_faktur_vendor = QLabel("No Faktur Vendor: -")
        self.lbl_faktur_vendor.setStyleSheet("color: #64748B; font-size: 12px;")
        info_layout.addWidget(self.lbl_faktur_vendor)

        self.lbl_status_bayar = QLabel("Status: -")
        self.lbl_status_bayar.setStyleSheet("font-weight: bold; font-size: 12px;")
        info_layout.addWidget(self.lbl_status_bayar)

        self.lbl_total_po = QLabel("Total PO: Rp 0")
        self.lbl_total_po.setStyleSheet("color: #047857; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(self.lbl_total_po)

        layout.addWidget(info_card)

        # Table
        lbl_tbl = QLabel("Daftar Item Faktur (Tentukan Qty yang Dikembalikan ke Vendor):")
        lbl_tbl.setStyleSheet("font-weight: 700; font-size: 12px; margin-top: 4px;")
        layout.addWidget(lbl_tbl)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Nama Produk", "Qty Masuk", "Sudah Retur", "Stok Toko", "Bisa Retur", "Qty Retur", "Nilai Retur"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 110)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        # Form Inputs Card
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        row_inputs = QHBoxLayout()
        row_inputs.setSpacing(12)

        metode_box = QVBoxLayout()
        lbl_metode = QLabel("Kompensasi / Penyelesaian:")
        lbl_metode.setStyleSheet("font-size: 11px; font-weight: 600;")
        metode_box.addWidget(lbl_metode)

        self.combo_metode = QComboBox()
        self.combo_metode.setFixedHeight(36)
        self.combo_metode.addItem("💳 Potong Hutang / Tagihan Tempo", "potong_hutang")
        self.combo_metode.addItem("💵 Refund Kas / Transfer Masuk", "refund_cash")
        metode_box.addWidget(self.combo_metode)
        row_inputs.addLayout(metode_box, 1)

        alasan_box = QVBoxLayout()
        lbl_alasan = QLabel("Alasan Retur ke Supplier (Wajib):")
        lbl_alasan.setStyleSheet("font-size: 11px; font-weight: 600;")
        alasan_box.addWidget(lbl_alasan)

        self.input_alasan = QLineEdit()
        self.input_alasan.setPlaceholderText("Contoh: Barang cacat dari pabrik, mendekati kadaluarsa, salah kirim...")
        self.input_alasan.setFixedHeight(36)
        alasan_box.addWidget(self.input_alasan)
        row_inputs.addLayout(alasan_box, 2)

        form_layout.addLayout(row_inputs)

        # Total Nilai Retur
        tot_row = QHBoxLayout()
        tot_lbl = QLabel("TOTAL NILAI RETUR PEMBELIAN:")
        tot_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #DC2626;")
        tot_row.addWidget(tot_lbl)
        tot_row.addStretch()

        self.lbl_total_retur = QLabel("Rp 0")
        self.lbl_total_retur.setStyleSheet("font-size: 18px; font-weight: 800; color: #DC2626;")
        tot_row.addWidget(self.lbl_total_retur)
        form_layout.addLayout(tot_row)

        layout.addWidget(form_card)

        # Actions
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton("↩️ Konfirmasi Retur ke Supplier")
        self.btn_submit.setFixedHeight(38)
        self.btn_submit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #DC2626; color: white; font-weight: bold;
                border-radius: 6px; padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_submit.clicked.connect(self._process_retur)
        btn_row.addWidget(self.btn_submit)

        layout.addLayout(btn_row)

    def _load_pembelian(self):
        with db.get_session() as session:
            p = session.query(Pembelian).filter_by(id=self.pembelian_id).first()
            if not p:
                QMessageBox.critical(self, "Error", "Data faktur pembelian tidak ditemukan.")
                self.reject()
                return

            self.pembelian = p
            self.po_badge.setText(f"PO #{p.no_po}")

            sup_name = p.supplier.nama if p.supplier else "Supplier Umum"
            self.lbl_supplier.setText(f"Supplier: {sup_name}")
            self.lbl_faktur_vendor.setText(f"Faktur Vendor: {p.no_faktur}")
            st_color = "#EF4444" if p.status_bayar == "tempo" else "#10B981"
            self.lbl_status_bayar.setStyleSheet(f"color: {st_color}; font-weight: bold; font-size: 12px;")
            self.lbl_status_bayar.setText(f"Status: {p.status_bayar.upper()}")
            self.lbl_total_po.setText(f"Total PO: {format_rupiah(p.total)}")

            # Riwayat retur sebelumnya
            already_returned_map = {}
            for ret in p.retur:
                for rd in ret.detail:
                    bid = rd.barang_id or rd.nama_barang
                    already_returned_map[bid] = already_returned_map.get(bid, 0) + rd.qty

            self.table.setRowCount(len(p.detail))
            has_returnable = False

            for row, d in enumerate(p.detail):
                bid = d.barang_id or d.nama_barang
                qty_ret = already_returned_map.get(bid, 0)
                rem_po = max(0, d.qty - qty_ret)

                current_stock = 0
                if d.barang_id:
                    brg = session.query(Barang).get(d.barang_id)
                    if brg:
                        current_stock = brg.stok or 0

                # Max bisa diretur: tidak melebihi sisa PO dan tidak melebihi stok yang ada di toko
                max_return = min(rem_po, max(0, current_stock))

                self.item_data[d.id] = {
                    "barang_id": d.barang_id,
                    "kode_barang": d.kode_barang,
                    "nama_barang": d.nama_barang,
                    "qty_masuk": d.qty,
                    "qty_sudah_retur": qty_ret,
                    "rem_po": rem_po,
                    "stok_toko": current_stock,
                    "max_return": max_return,
                    "harga_beli": d.harga_beli,
                }

                # Col 0: Nama Produk
                self.table.setItem(row, 0, QTableWidgetItem(d.nama_barang))

                # Col 1: Qty Masuk
                self.table.setItem(row, 1, QTableWidgetItem(str(d.qty)))
                self.table.item(row, 1).setTextAlignment(Qt.AlignCenter)

                # Col 2: Sudah Retur
                self.table.setItem(row, 2, QTableWidgetItem(str(qty_ret)))
                self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

                # Col 3: Stok Toko
                stk_item = QTableWidgetItem(str(current_stock))
                stk_item.setTextAlignment(Qt.AlignCenter)
                if current_stock <= 0:
                    stk_item.setForeground(QColor("#EF4444"))
                self.table.setItem(row, 3, stk_item)

                # Col 4: Bisa Retur
                can_item = QTableWidgetItem(str(max_return))
                can_item.setTextAlignment(Qt.AlignCenter)
                if max_return > 0:
                    can_item.setForeground(QColor("#10B981"))
                    can_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    has_returnable = True
                else:
                    can_item.setForeground(QColor("#94A3B8"))
                self.table.setItem(row, 4, can_item)

                # Col 5: SpinBox
                spin = QSpinBox()
                spin.setRange(0, max_return)
                spin.setValue(0)
                spin.setEnabled(max_return > 0)
                spin.setFixedHeight(30)
                spin.setAlignment(Qt.AlignCenter)
                spin.valueChanged.connect(lambda val, iid=d.id: self._on_qty_changed(iid, val))
                self.spinboxes[d.id] = spin
                self.table.setCellWidget(row, 5, spin)

                # Col 6: Subtotal
                lbl_sub = QLabel("Rp 0")
                lbl_sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                lbl_sub.setStyleSheet("font-weight: 600; padding-right: 6px;")
                self.subtotal_labels[d.id] = lbl_sub
                self.table.setCellWidget(row, 6, lbl_sub)

            if not has_returnable:
                self.btn_submit.setEnabled(False)
                QMessageBox.information(
                    self, "Informasi Retur",
                    "Tidak ada barang yang dapat diretur pada faktur ini (stok habis atau sudah diretur penuh)."
                )

    def _on_qty_changed(self, item_id: int, qty: int):
        data = self.item_data.get(item_id, {})
        harga = data.get("harga_beli", 0)
        subtotal = qty * harga
        if item_id in self.subtotal_labels:
            self.subtotal_labels[item_id].setText(format_rupiah(subtotal))

        grand_total = 0
        for iid, spin in self.spinboxes.items():
            q = spin.value()
            h = self.item_data.get(iid, {}).get("harga_beli", 0)
            grand_total += (q * h)

        self.lbl_total_retur.setText(format_rupiah(grand_total))

    def _process_retur(self):
        items_to_return = []
        total_retur = 0

        for item_id, spin in self.spinboxes.items():
            qty = spin.value()
            if qty > 0:
                data = self.item_data[item_id]
                if qty > data["max_return"]:
                    QMessageBox.warning(
                        self, "Validasi Gagal",
                        f"Qty retur untuk '{data['nama_barang']}' ({qty}) melebihi stok yang tersedia ({data['max_return']})."
                    )
                    return

                subtotal = qty * data["harga_beli"]
                total_retur += subtotal
                items_to_return.append({
                    "barang_id": data["barang_id"],
                    "kode_barang": data["kode_barang"],
                    "nama_barang": data["nama_barang"],
                    "qty": qty,
                    "harga_beli": data["harga_beli"],
                    "subtotal": subtotal,
                })

        if not items_to_return:
            QMessageBox.warning(self, "Perhatian", "Silakan tentukan minimal 1 barang dengan jumlah retur > 0.")
            return

        alasan = self.input_alasan.text().strip()
        if not alasan:
            QMessageBox.warning(self, "Wajib Diisi", "Mohon masukkan alasan retur ke supplier.")
            self.input_alasan.setFocus()
            return

        metode_kembali = self.combo_metode.currentData()

        confirm = QMessageBox.question(
            self, "Konfirmasi Retur ke Supplier",
            f"Anda akan mengembalikan {len(items_to_return)} item senilai {format_rupiah(total_retur)} ke Supplier.\n\n"
            f"Metode: {self.combo_metode.currentText()}\n"
            f"Alasan: {alasan}\n\n"
            f"Stok barang di toko akan otomatis DIKURANGI.\nLanjutkan?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            with db.get_session() as session:
                p = session.query(Pembelian).filter_by(id=self.pembelian_id).first()
                if not p:
                    raise ValueError("Faktur pembelian tidak ditemukan.")

                no_retur = generate_retur_pembelian_number(session)
                user_id = auth.current_user.id if auth.current_user else None

                retur_obj = ReturPembelian(
                    no_retur=no_retur,
                    pembelian_id=p.id,
                    no_po=p.no_po,
                    supplier_id=p.supplier_id,
                    total_retur=total_retur,
                    alasan=alasan,
                    metode_kembali=metode_kembali,
                    user_id=user_id,
                )
                session.add(retur_obj)
                session.flush()

                for item in items_to_return:
                    rd = ReturPembelianDetail(
                        retur_id=retur_obj.id,
                        barang_id=item["barang_id"],
                        kode_barang=item["kode_barang"],
                        nama_barang=item["nama_barang"],
                        qty=item["qty"],
                        harga_beli=item["harga_beli"],
                        subtotal=item["subtotal"],
                    )
                    session.add(rd)

                    # Kurangi stok barang karena dikembalikan ke supplier
                    if item["barang_id"]:
                        brg = session.query(Barang).filter_by(id=item["barang_id"]).first()
                        if brg:
                            brg.stok = max(0, brg.stok - item["qty"])

                # Jika metode potong hutang dan status tempo, potong tagihan PO
                if metode_kembali == "potong_hutang" and p.status_bayar == "tempo":
                    p.total = max(0.0, p.total - total_retur)
                    if p.total <= 0:
                        p.status_bayar = "lunas"

                session.commit()

            QMessageBox.information(
                self, "Retur Berhasil",
                f"Retur Pembelian berhasil diproses!\nNomor Retur: {no_retur}\n"
                f"Stok gudang telah diperbarui."
            )
            self.retur_processed.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Gagal Memproses", f"Terjadi kesalahan saat memproses retur pembelian:\n{str(e)}")
