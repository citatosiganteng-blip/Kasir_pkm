"""
KasirKu Payment Dialog
Dialog konfirmasi pembayaran
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QFont, QColor, QPixmap

from database.db import db
from utils.helpers import format_rupiah


class PaymentDialog(QDialog):
    """Dialog pembayaran dan konfirmasi"""
    payment_confirmed = pyqtSignal(float, str)  # (jumlah_bayar, metode)

    def __init__(self, total: float, parent=None):
        super().__init__(parent)
        self.total = total
        self.setWindowTitle("Pembayaran")
        self.setFixedWidth(460)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
                border-radius: 16px;
            }
        """)
        self._setup_ui()
        self.bayar_input.setFocus()
        # Set default cash to exact amount
        self.bayar_input.setText(str(int(total)))
        self._update_change()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        # Header
        header_lbl = QLabel("💳 Proses Pembayaran")
        header_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E293B;")
        layout.addWidget(header_lbl)

        # Total
        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background: #EFF6FF;
                border: 1.5px solid #BFDBFE;
                border-radius: 12px;
            }
        """)
        total_layout = QVBoxLayout(total_frame)
        total_layout.setContentsMargins(20, 14, 20, 14)

        total_title = QLabel("Total Pembayaran")
        total_title.setStyleSheet("color: #1E40AF; font-size: 12px; font-weight: 600; background: transparent;")
        total_layout.addWidget(total_title)

        self.total_lbl = QLabel(format_rupiah(self.total))
        self.total_lbl.setStyleSheet("color: #1D4ED8; font-size: 28px; font-weight: 900; background: transparent;")
        total_layout.addWidget(self.total_lbl)
        layout.addWidget(total_frame)

        # Metode bayar
        metode_lbl = QLabel("Metode Pembayaran")
        metode_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        layout.addWidget(metode_lbl)

        self.metode_combo = QComboBox()
        self.metode_combo.addItems(["Cash", "QRIS", "Transfer"])
        self.metode_combo.setFixedHeight(44)
        self.metode_combo.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                padding: 0 14px;
                color: #1E293B;
                font-size: 14px;
            }
            QComboBox:focus { border-color: #2563EB; }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                selection-background-color: #EFF6FF;
                selection-color: #2563EB;
            }
        """)
        self.metode_combo.currentTextChanged.connect(self._on_metode_changed)
        layout.addWidget(self.metode_combo)

        # QRIS Container (Hidden by default)
        self.qris_frame = QFrame()
        self.qris_frame.setStyleSheet("""
            QFrame {
                background: #F8FAFC;
                border: 1.5px solid #2563EB;
                border-radius: 12px;
            }
        """)
        qris_layout = QVBoxLayout(self.qris_frame)
        qris_layout.setContentsMargins(16, 16, 16, 16)
        qris_layout.setAlignment(Qt.AlignCenter)

        qris_header = QLabel("📲 Scan QRIS Pembayaran")
        qris_header.setStyleSheet("color: #2563EB; font-size: 13px; font-weight: 700; background: transparent;")
        qris_header.setAlignment(Qt.AlignCenter)
        qris_layout.addWidget(qris_header)

        self.qris_img_lbl = QLabel()
        self.qris_img_lbl.setAlignment(Qt.AlignCenter)
        self.qris_img_lbl.setStyleSheet("background: white; border-radius: 8px; padding: 10px;")
        qris_layout.addWidget(self.qris_img_lbl)

        self.qris_info_lbl = QLabel("Bisa di-scan via BCA, GoPay, OVO, DANA, ShopeePay, LinkAja, dll.")
        self.qris_info_lbl.setWordWrap(True)
        self.qris_info_lbl.setAlignment(Qt.AlignCenter)
        self.qris_info_lbl.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        qris_layout.addWidget(self.qris_info_lbl)

        layout.addWidget(self.qris_frame)
        self.qris_frame.hide()

        # Jumlah bayar
        self.bayar_lbl = QLabel("Jumlah Diterima")
        self.bayar_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.bayar_lbl)

        self.bayar_input = QLineEdit()
        self.bayar_input.setPlaceholderText("0")
        self.bayar_input.setFixedHeight(54)
        self.bayar_input.setValidator(QDoubleValidator(0, 999_999_999, 0))
        self.bayar_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                padding: 0 14px;
                color: #1E293B;
                font-size: 22px;
                font-weight: 700;
            }
            QLineEdit:focus { border-color: #2563EB; }
        """)
        self.bayar_input.textChanged.connect(self._update_change)
        layout.addWidget(self.bayar_input)

        # Quick cash buttons
        self.quick_widget = QWidget()
        quick_layout = QHBoxLayout(self.quick_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_amounts = [10000, 20000, 50000, 100000]
        for amt in quick_amounts:
            btn = QPushButton(f"{amt//1000}rb")
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9;
                    color: #475569;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #EFF6FF; color: #2563EB; border-color: #BFDBFE; }
            """)
            btn.clicked.connect(lambda _, a=amt: self._add_amount(a))
            quick_layout.addWidget(btn)
        layout.addWidget(self.quick_widget)

        # Kembalian
        self.change_frame = QFrame()
        self.change_frame.setStyleSheet("""
            QFrame {
                background: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 10px;
            }
        """)
        change_layout = QHBoxLayout(self.change_frame)
        change_layout.setContentsMargins(16, 12, 16, 12)

        change_title = QLabel("Kembalian:")
        change_title.setStyleSheet("color: #065F46; font-size: 13px; font-weight: 600; background: transparent;")
        change_layout.addWidget(change_title)
        change_layout.addStretch()

        self.change_lbl = QLabel("Rp 0")
        self.change_lbl.setStyleSheet("color: #059669; font-size: 18px; font-weight: 800; background: transparent;")
        change_layout.addWidget(self.change_lbl)
        layout.addWidget(self.change_frame)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setFixedHeight(48)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #E2E8F0; color: #1E293B; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_confirm = QPushButton("✅ Konfirmasi Bayar")
        self.btn_confirm.setFixedHeight(48)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton:pressed { background: #1E40AF; }
            QPushButton:disabled { background: #E2E8F0; color: #94A3B8; }
        """)
        self.btn_confirm.clicked.connect(self._confirm)
        btn_row.addWidget(self.btn_confirm)
        layout.addLayout(btn_row)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 12px; text-align: center;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

    def _add_amount(self, amount: float):
        """Tambah jumlah ke input bayar"""
        try:
            current = float(self.bayar_input.text() or 0)
            self.bayar_input.setText(str(int(current + amount)))
        except ValueError:
            self.bayar_input.setText(str(int(amount)))

    def _on_metode_changed(self, metode: str):
        """Ubah perilaku saat metode berubah"""
        is_cash = metode == "Cash"
        is_qris = metode == "QRIS"

        self.bayar_input.setEnabled(is_cash)
        self.quick_widget.setVisible(is_cash)
        self.change_frame.setVisible(is_cash)

        if is_qris:
            self.bayar_input.setText(str(int(self.total)))
            self._load_qris_image()
            self.qris_frame.show()
        else:
            self.qris_frame.hide()
            if not is_cash:
                self.bayar_input.setText(str(int(self.total)))

        self.adjustSize()
        self._update_change()

    def _load_qris_image(self):
        """Load gambar QRIS dari setting"""
        qris_path = db.get_setting("qris_image_path", "")
        if qris_path and os.path.exists(qris_path):
            pixmap = QPixmap(qris_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.qris_img_lbl.setPixmap(scaled)
                self.qris_img_lbl.setText("")
                self.qris_info_lbl.setText("Scan QRIS di atas untuk melakukan pembayaran.")
                return

        # Fallback jika belum upload gambar QRIS
        self.qris_img_lbl.setPixmap(QPixmap())
        self.qris_img_lbl.setText(
            "⚠️ Belum Ada Gambar QRIS Toko\n\n"
            "Silakan upload gambar QRIS toko Anda di:\n"
            "Pengaturan ⚙️ ➔ Info Toko ➔ Gambar QRIS Toko"
        )
        self.qris_img_lbl.setStyleSheet("""
            background: #2D3250;
            color: #F59E0B;
            border-radius: 8px;
            padding: 16px;
            font-weight: 600;
            font-size: 12px;
        """)

    def _update_change(self):
        """Hitung dan tampilkan kembalian"""
        try:
            bayar = float(self.bayar_input.text() or 0)
            kembalian = bayar - self.total

            if self.metode_combo.currentText() != "Cash":
                self.btn_confirm.setEnabled(True)
                return

            if kembalian < 0:
                self.change_lbl.setText(f"Kurang {format_rupiah(abs(kembalian))}")
                self.change_lbl.setStyleSheet("color: #EF4444; font-size: 16px; font-weight: 800; background: transparent;")
                self.btn_confirm.setEnabled(False)
            else:
                self.change_lbl.setText(format_rupiah(kembalian))
                self.change_lbl.setStyleSheet("color: #F59E0B; font-size: 18px; font-weight: 800; background: transparent;")
                self.btn_confirm.setEnabled(True)
        except ValueError:
            self.change_lbl.setText("Rp 0")
            self.btn_confirm.setEnabled(False)

    def _confirm(self):
        try:
            bayar = float(self.bayar_input.text() or 0)
        except ValueError:
            self.error_lbl.setText("Jumlah bayar tidak valid!")
            self.error_lbl.show()
            return

        if bayar < self.total:
            self.error_lbl.setText("Jumlah bayar kurang dari total!")
            self.error_lbl.show()
            return

        metode = self.metode_combo.currentText().lower()
        self.payment_confirmed.emit(bayar, metode)
        self.accept()
