"""
KasirKu Sales Return Dialog (Retur Penjualan)
Dialog pengembalian barang konsumen:
- Partial / full item return
- Validasi sisa barang yang belum diretur
- Auto restock barang (Barang.stok += qty_retur)
- Pilihan metode pengembalian dana (cash refund, potong piutang, tukar barang)
- Cetak / simpan Nota Retur A4 PDF
"""

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QFileDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QCursor

from database.db import db
from database.models import Transaksi, ReturPenjualan, ReturPenjualanDetail, Barang, Pengeluaran
from auth.auth_manager import auth
from utils.helpers import format_rupiah, format_datetime, generate_retur_penjualan_number
from services.invoice_pdf_service import InvoicePdfService


class ReturPenjualanDialog(QDialog):
    """Dialog pengajuan dan pemrosesan Retur Penjualan"""
    retur_processed = pyqtSignal()

    def __init__(self, transaksi_id: int, parent=None):
        super().__init__(parent)
        self.transaksi_id = transaksi_id
        self.transaksi = None
        self.spinboxes = {}  # {item_id: QSpinBox}
        self.subtotal_labels = {}  # {item_id: QLabel}
        self.item_data = {}  # {item_id: dict info}

        self.setWindowTitle("↩️ Retur Penjualan (Sales Return)")
        self.setMinimumSize(780, 560)
        self.setModal(True)

        self._setup_ui()
        self._load_transaksi()

    def _setup_ui(self):
        theme = db.get_setting("app_theme", "dark")
        is_dark = (theme == "dark")
        self.is_dark = is_dark

        bg_col = "#0F172A" if is_dark else "#FFFFFF"
        text_col = "#F1F5F9" if is_dark else "#0F172A"
        card_bg = "#1E293B" if is_dark else "#F8FAFC"
        border_col = "#334155" if is_dark else "#E2E8F0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
            QFrame#info_card {{
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

        # ── HEADER ──
        header_row = QHBoxLayout()
        icon_lbl = QLabel("↩️")
        icon_lbl.setStyleSheet("font-size: 24px;")
        header_row.addWidget(icon_lbl)

        header_title = QLabel("Proses Retur Penjualan")
        header_title.setStyleSheet("font-size: 18px; font-weight: 800;")
        header_row.addWidget(header_title)
        header_row.addStretch()

        self.inv_badge = QLabel("")
        self.inv_badge.setStyleSheet("""
            background: #DC2626; color: #FFFFFF; font-weight: bold;
            padding: 4px 10px; border-radius: 6px; font-size: 12px;
        """)
        header_row.addWidget(self.inv_badge)
        layout.addLayout(header_row)

        # ── INFO TRANSAKSI CARD ──
        info_card = QFrame()
        info_card.setObjectName("info_card")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(14, 10, 14, 10)

        self.lbl_customer = QLabel("Pelanggan: -")
        self.lbl_customer.setStyleSheet("font-weight: 600; font-size: 12px;")
        info_layout.addWidget(self.lbl_customer)

        self.lbl_tanggal = QLabel("Tanggal: -")
        self.lbl_tanggal.setStyleSheet("color: #64748B; font-size: 12px;")
        info_layout.addWidget(self.lbl_tanggal)

        self.lbl_total_asal = QLabel("Total Faktur: Rp 0")
        self.lbl_total_asal.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(self.lbl_total_asal)

        layout.addWidget(info_card)

        # ── TABEL BARANG ──
        lbl_tbl = QLabel("Daftar Item Faktur (Tentukan Qty yang Diretur):")
        lbl_tbl.setStyleSheet("font-weight: 700; font-size: 12px; margin-top: 4px;")
        layout.addWidget(lbl_tbl)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Nama Produk", "Qty Beli", "Sudah Retur", "Sisa Bisa Retur", "Qty Retur", "Nilai Retur"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 110)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        # ── FORM ALASAN & REFUND METHOD ──
        form_card = QFrame()
        form_card.setObjectName("info_card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        row_inputs = QHBoxLayout()
        row_inputs.setSpacing(12)

        # Metode Pengembalian
        metode_box = QVBoxLayout()
        lbl_metode = QLabel("Metode Pengembalian Dana / Barang:")
        lbl_metode.setStyleSheet("font-size: 11px; font-weight: 600;")
        metode_box.addWidget(lbl_metode)

        self.combo_metode = QComboBox()
        self.combo_metode.setFixedHeight(36)
        self.combo_metode.addItem("💵 Refund Tunai / Kas (Cash)", "cash")
        self.combo_metode.addItem("💳 Potong Piutang (Jika Tempo)", "potong_piutang")
        self.combo_metode.addItem("🔄 Tukar Barang Sejenis", "tukar_barang")
        metode_box.addWidget(self.combo_metode)
        row_inputs.addLayout(metode_box, 1)

        # Alasan Retur
        alasan_box = QVBoxLayout()
        lbl_alasan = QLabel("Alasan Pengembalian / Kerusakan (Wajib):")
        lbl_alasan.setStyleSheet("font-size: 11px; font-weight: 600;")
        alasan_box.addWidget(lbl_alasan)

        self.input_alasan = QLineEdit()
        self.input_alasan.setPlaceholderText("Contoh: Barang cacat pabrik, kemasan rusak, salah beli...")
        self.input_alasan.setFixedHeight(36)
        alasan_box.addWidget(self.input_alasan)
        row_inputs.addLayout(alasan_box, 2)

        form_layout.addLayout(row_inputs)

        # Total Nilai Retur
        tot_row = QHBoxLayout()
        tot_lbl = QLabel("TOTAL NILAI REFUND / RETUR:")
        tot_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #DC2626;")
        tot_row.addWidget(tot_lbl)
        tot_row.addStretch()

        self.lbl_total_retur = QLabel("Rp 0")
        self.lbl_total_retur.setStyleSheet("font-size: 18px; font-weight: 800; color: #DC2626;")
        tot_row.addWidget(self.lbl_total_retur)
        form_layout.addLayout(tot_row)

        layout.addWidget(form_card)

        # ── ACTION BUTTONS ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton("↩️ Konfirmasi & Proses Retur")
        self.btn_submit.setObjectName("btn_danger")
        self.btn_submit.setFixedHeight(38)
        self.btn_submit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_submit.setStyleSheet("""
            QPushButton#btn_danger {
                background-color: #DC2626; color: white; font-weight: bold;
                border-radius: 6px; padding: 0 16px;
            }
            QPushButton#btn_danger:hover {
                background-color: #B91C1C;
            }
        """)
        self.btn_submit.clicked.connect(self._process_retur)
        btn_row.addWidget(self.btn_submit)

        layout.addLayout(btn_row)

    def _load_transaksi(self):
        with db.get_session() as session:
            t = session.query(Transaksi).filter_by(id=self.transaksi_id).first()
            if not t:
                QMessageBox.critical(self, "Error", "Data transaksi tidak ditemukan.")
                self.reject()
                return

            self.transaksi = t
            self.inv_badge.setText(f"Invoice #{t.no_invoice}")

            cust_name = t.nama_pelanggan or (t.pelanggan.nama if t.pelanggan else "Pelanggan Umum")
            self.lbl_customer.setText(f"Pelanggan: {cust_name}")
            self.lbl_tanggal.setText(f"Tanggal: {format_datetime(t.tanggal)}")
            self.lbl_total_asal.setText(f"Total Faktur: {format_rupiah(t.total)}")

            # Periksa riwayat retur sebelumnya untuk kalkulasi sisa yang belum diretur
            already_returned_map = {}  # {barang_id: total_qty}
            for ret in t.retur:
                for rd in ret.detail:
                    bid = rd.barang_id or rd.nama_barang
                    already_returned_map[bid] = already_returned_map.get(bid, 0) + rd.qty

            self.table.setRowCount(len(t.detail))
            has_returnable = False

            for row, d in enumerate(t.detail):
                bid = d.barang_id or d.nama_barang
                qty_ret = already_returned_map.get(bid, 0)
                remaining = max(0, d.qty - qty_ret)

                self.item_data[d.id] = {
                    "barang_id": d.barang_id,
                    "kode_barang": d.kode_barang,
                    "nama_barang": d.nama_barang,
                    "qty_beli": d.qty,
                    "qty_sudah_retur": qty_ret,
                    "remaining": remaining,
                    "harga_satuan": d.harga,
                }

                # Col 0: Nama Produk
                self.table.setItem(row, 0, QTableWidgetItem(d.nama_barang))

                # Col 1: Qty Beli
                qty_item = QTableWidgetItem(str(d.qty))
                qty_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, qty_item)

                # Col 2: Sudah Retur
                ret_item = QTableWidgetItem(str(qty_ret))
                ret_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, ret_item)

                # Col 3: Sisa Bisa Retur
                rem_item = QTableWidgetItem(str(remaining))
                rem_item.setTextAlignment(Qt.AlignCenter)
                if remaining == 0:
                    rem_item.setForeground(QColor("#94A3B8"))
                else:
                    rem_item.setForeground(QColor("#10B981"))
                    rem_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    has_returnable = True
                self.table.setItem(row, 3, rem_item)

                # Col 4: SpinBox Qty Retur
                spin = QSpinBox()
                spin.setRange(0, remaining)
                spin.setValue(0)
                spin.setEnabled(remaining > 0)
                spin.setFixedHeight(30)
                spin.setAlignment(Qt.AlignCenter)
                spin.valueChanged.connect(lambda val, iid=d.id: self._on_qty_changed(iid, val))
                self.spinboxes[d.id] = spin
                self.table.setCellWidget(row, 4, spin)

                # Col 5: Nilai Retur
                lbl_sub = QLabel("Rp 0")
                lbl_sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                lbl_sub.setStyleSheet("font-weight: 600; padding-right: 6px;")
                self.subtotal_labels[d.id] = lbl_sub
                self.table.setCellWidget(row, 5, lbl_sub)

            if not has_returnable:
                self.btn_submit.setEnabled(False)
                QMessageBox.information(
                    self, "Informasi Retur",
                    "Semua barang pada transaksi ini sudah diretur sebelumnya."
                )

    def _on_qty_changed(self, item_id: int, qty: int):
        data = self.item_data.get(item_id, {})
        harga = data.get("harga_satuan", 0)
        subtotal = qty * harga
        if item_id in self.subtotal_labels:
            self.subtotal_labels[item_id].setText(format_rupiah(subtotal))

        # Hitung grand total retur
        grand_total = 0
        for iid, spin in self.spinboxes.items():
            q = spin.value()
            h = self.item_data.get(iid, {}).get("harga_satuan", 0)
            grand_total += (q * h)

        self.lbl_total_retur.setText(format_rupiah(grand_total))

    def _process_retur(self):
        # 1. Validasi jumlah barang yang diretur
        items_to_return = []
        total_retur = 0

        for item_id, spin in self.spinboxes.items():
            qty = spin.value()
            if qty > 0:
                data = self.item_data[item_id]
                if qty > data["remaining"]:
                    QMessageBox.warning(
                        self, "Validasi Gagal",
                        f"Qty retur untuk '{data['nama_barang']}' ({qty}) melebihi sisa yang bisa diretur ({data['remaining']})."
                    )
                    return

                subtotal = qty * data["harga_satuan"]
                total_retur += subtotal
                items_to_return.append({
                    "barang_id": data["barang_id"],
                    "kode_barang": data["kode_barang"],
                    "nama_barang": data["nama_barang"],
                    "qty": qty,
                    "harga_satuan": data["harga_satuan"],
                    "subtotal": subtotal,
                })

        if not items_to_return:
            QMessageBox.warning(
                self, "Perhatian",
                "Silakan tentukan minimal 1 barang dengan jumlah retur > 0."
            )
            return

        alasan = self.input_alasan.text().strip()
        if not alasan:
            QMessageBox.warning(
                self, "Wajib Diisi",
                "Mohon masukkan alasan retur / pengembalian barang."
            )
            self.input_alasan.setFocus()
            return

        metode_kembali = self.combo_metode.currentData()

        # Konfirmasi pengguna
        confirm = QMessageBox.question(
            self, "Konfirmasi Proses Retur",
            f"Anda akan memproses retur untuk {len(items_to_return)} item produk senilai {format_rupiah(total_retur)}.\n\n"
            f"Metode: {self.combo_metode.currentText()}\n"
            f"Alasan: {alasan}\n\n"
            f"Stok barang akan otomatis dikembalikan ke gudang/toko.\nLanjutkan?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # Simpan ke Database
        created_retur = None
        try:
            with db.get_session() as session:
                t = session.query(Transaksi).filter_by(id=self.transaksi_id).first()
                if not t:
                    raise ValueError("Transaksi tidak ditemukan.")

                no_retur = generate_retur_penjualan_number(session)
                user_id = auth.current_user.id if auth.current_user else None

                retur_obj = ReturPenjualan(
                    no_retur=no_retur,
                    transaksi_id=t.id,
                    no_invoice=t.no_invoice,
                    total_retur=total_retur,
                    alasan=alasan,
                    metode_kembali=metode_kembali,
                    user_id=user_id,
                )
                session.add(retur_obj)
                session.flush()

                for item in items_to_return:
                    rd = ReturPenjualanDetail(
                        retur_id=retur_obj.id,
                        barang_id=item["barang_id"],
                        kode_barang=item["kode_barang"],
                        nama_barang=item["nama_barang"],
                        qty=item["qty"],
                        harga_satuan=item["harga_satuan"],
                        subtotal=item["subtotal"],
                    )
                    session.add(rd)

                    # Auto restock: kembalikan stok barang
                    if item["barang_id"]:
                        brg = session.query(Barang).filter_by(id=item["barang_id"]).first()
                        if brg:
                            brg.stok += item["qty"]

                # Jika refund cash, catat pengeluaran toko
                if metode_kembali == "cash":
                    session.add(Pengeluaran(
                        kategori="Retur Penjualan",
                        nominal=total_retur,
                        deskripsi=f"Refund tunai retur {no_retur} untuk invoice {t.no_invoice}: {alasan}",
                        user_id=user_id
                    ))

                session.commit()
                created_retur_id = retur_obj.id

            # Ambil objek fresh untuk dicetak
            with db.get_session() as session:
                created_retur = session.query(ReturPenjualan).filter_by(id=created_retur_id).first()

            QMessageBox.information(
                self, "Retur Berhasil",
                f"Retur Penjualan berhasil diproses!\nNomor Retur: {created_retur.no_retur}\n"
                f"Stok telah berhasil di-restock."
            )

            # Tawarkan cetak Nota Retur PDF
            cetak_confirm = QMessageBox.question(
                self, "Cetak Nota Retur",
                "Apakah Anda ingin mencetak / mengekspor Nota Retur (A4 PDF) sekarang?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if cetak_confirm == QMessageBox.Yes and created_retur:
                html = InvoicePdfService.generate_sales_return_html(created_retur)
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Simpan Nota Retur Penjualan (PDF)",
                    f"Nota_Retur_{created_retur.no_retur}.pdf",
                    "PDF Files (*.pdf)"
                )
                if file_path:
                    ok = InvoicePdfService.save_html_to_pdf(html, file_path)
                    if ok:
                        QMessageBox.information(self, "Sukses", f"Nota Retur berhasil disimpan ke:\n{file_path}")
                    else:
                        QMessageBox.warning(self, "Gagal", "Gagal mengekspor file PDF.")

            self.retur_processed.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Gagal Memproses", f"Terjadi kesalahan saat memproses retur:\n{str(e)}")
