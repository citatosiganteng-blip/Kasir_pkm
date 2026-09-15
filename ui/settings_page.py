"""
KasirKu Settings Page
Halaman pengaturan aplikasi (admin only)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox, QGroupBox,
    QFormLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QCursor

from database.db import db
from services.backup_service import BackupService
from services.drawer_service import DrawerService
from auth.auth_manager import auth
from utils.helpers import format_datetime


class SettingsPage(QWidget):
    """Halaman pengaturan"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("⚙️ Pengaturan")
        title.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()

        tabs.addTab(self._create_store_tab(), "🏪 Info Toko")
        tabs.addTab(self._create_printer_tab(), "🖨️ Printer")
        tabs.addTab(self._create_backup_tab(), "💾 Backup")
        tabs.addTab(self._create_drawer_tab(), "🗄️ Cash Drawer")

        layout.addWidget(tabs)

    def _input(self, placeholder=""):
        i = QLineEdit()
        i.setPlaceholderText(placeholder)
        i.setFixedHeight(40)
        return i

    def _label(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
        return l

    def _save_btn(self, on_click):
        btn = QPushButton("💾 Simpan Perubahan")
        btn.setFixedHeight(44)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.clicked.connect(on_click)
        return btn

    def _create_store_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.store_name_input = self._input("Nama toko")
        self.store_address_input = self._input("Alamat toko")
        self.store_phone_input = self._input("Nomor telepon")
        self.store_tagline_input = self._input("Ucapan terima kasih")

        form.addRow(self._label("Nama Toko:"), self.store_name_input)
        form.addRow(self._label("Alamat:"), self.store_address_input)
        form.addRow(self._label("Telepon:"), self.store_phone_input)
        form.addRow(self._label("Tagline Struk:"), self.store_tagline_input)

        # Upload QRIS
        qris_box = QHBoxLayout()
        self.qris_path_input = self._input("Belum ada file QRIS")
        self.qris_path_input.setReadOnly(True)
        btn_browse_qris = QPushButton("📁 Pilih Gambar QRIS")
        btn_browse_qris.setObjectName("btn_secondary")
        btn_browse_qris.setFixedHeight(40)
        btn_browse_qris.setCursor(QCursor(Qt.PointingHandCursor))
        btn_browse_qris.clicked.connect(self._browse_qris)
        qris_box.addWidget(self.qris_path_input)
        qris_box.addWidget(btn_browse_qris)

        form.addRow(self._label("Gambar QRIS Toko:"), qris_box)

        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self._save_btn(self._save_store))
        return w

    def _create_printer_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.printer_type_combo = QComboBox()
        self.printer_type_combo.addItems(["usb", "serial", "network"])
        self.printer_type_combo.setFixedHeight(40)
        form.addRow(self._label("Tipe Printer:"), self.printer_type_combo)

        self.printer_port_input = self._input("COM1, /dev/ttyUSB0, dll")
        form.addRow(self._label("Port Serial:"), self.printer_port_input)

        self.printer_host_input = self._input("192.168.1.100")
        form.addRow(self._label("IP Network:"), self.printer_host_input)

        self.printer_width_combo = QComboBox()
        self.printer_width_combo.addItems(["58", "80"])
        self.printer_width_combo.setFixedHeight(40)
        form.addRow(self._label("Lebar Kertas (mm):"), self.printer_width_combo)

        layout.addLayout(form)

        # Test print button
        btn_test = QPushButton("🖨️ Test Print")
        btn_test.setObjectName("btn_secondary")
        btn_test.setFixedHeight(44)
        btn_test.setCursor(QCursor(Qt.PointingHandCursor))
        btn_test.clicked.connect(self._test_print)
        layout.addWidget(btn_test)
        layout.addStretch()
        layout.addWidget(self._save_btn(self._save_printer))
        return w

    def _create_backup_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info_lbl = QLabel("Database backup disimpan otomatis setiap 8 jam dan saat aplikasi ditutup.")
        info_lbl.setStyleSheet("color: #64748B; font-size: 13px; background: transparent;")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        btn_backup = QPushButton("💾 Backup Sekarang")
        btn_backup.setObjectName("btn_success")
        btn_backup.setFixedHeight(44)
        btn_backup.setCursor(QCursor(Qt.PointingHandCursor))
        btn_backup.clicked.connect(self._do_backup_now)
        layout.addWidget(btn_backup)

        # Backup list
        backup_title = QLabel("Daftar Backup")
        backup_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 8px; background: transparent;")
        layout.addWidget(backup_title)

        restore_hint = QLabel("💡 Pilih baris backup lalu klik Restore untuk mengembalikan data.")
        restore_hint.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        layout.addWidget(restore_hint)

        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(["Nama File", "Ukuran", "Tanggal", "Aksi"])
        self.backup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.backup_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.backup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.backup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.backup_table.verticalHeader().setVisible(False)
        self.backup_table.setAlternatingRowColors(True)
        layout.addWidget(self.backup_table)
        self._load_backup_list()
        return w

    def _create_drawer_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info = QLabel("Cash drawer terhubung via kabel RJ11 ke printer thermal.")
        info.setStyleSheet("color: #64748B; font-size: 13px; background: transparent;")
        layout.addWidget(info)

        btn_open = QPushButton("🗄️ Buka Cash Drawer Sekarang")
        btn_open.setFixedHeight(50)
        btn_open.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open.clicked.connect(self._manual_open_drawer)
        layout.addWidget(btn_open)

        # Log drawer
        log_title = QLabel("Log Aktivitas Cash Drawer")
        log_title.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 8px; background: transparent;")
        layout.addWidget(log_title)

        self.drawer_log_table = QTableWidget()
        self.drawer_log_table.setColumnCount(4)
        self.drawer_log_table.setHorizontalHeaderLabels(["Waktu", "User", "Aksi", "Keterangan"])
        self.drawer_log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.drawer_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.drawer_log_table.verticalHeader().setVisible(False)
        self.drawer_log_table.setAlternatingRowColors(True)
        layout.addWidget(self.drawer_log_table)
        self._load_drawer_log()
        return w

    def _load_settings(self):
        """Load pengaturan dari database. DB adalah sumber kebenaran tunggal."""
        self.store_name_input.setText(db.get_setting("store_name", "Toko Kami"))
        self.store_address_input.setText(db.get_setting("store_address", ""))
        self.store_phone_input.setText(db.get_setting("store_phone", ""))
        self.store_tagline_input.setText(
            db.get_setting("store_tagline", "Terima kasih telah berbelanja!")
        )
        self.qris_path_input.setText(db.get_setting("qris_image_path", ""))

        printer_type = db.get_setting("printer_type", "usb")
        idx = self.printer_type_combo.findText(printer_type)
        if idx >= 0:
            self.printer_type_combo.setCurrentIndex(idx)

        self.printer_port_input.setText(db.get_setting("printer_port", "COM1"))
        self.printer_host_input.setText(db.get_setting("printer_host", "192.168.1.100"))

        width = db.get_setting("printer_width", "80")
        idx_w = self.printer_width_combo.findText(width)
        if idx_w >= 0:
            self.printer_width_combo.setCurrentIndex(idx_w)

    def _browse_qris(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Gambar QRIS Toko", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.qris_path_input.setText(file_path)

    def _save_store(self):
        db.set_setting("store_name", self.store_name_input.text().strip())
        db.set_setting("store_address", self.store_address_input.text().strip())
        db.set_setting("store_phone", self.store_phone_input.text().strip())
        db.set_setting("store_tagline", self.store_tagline_input.text().strip())
        db.set_setting("qris_image_path", self.qris_path_input.text().strip())
        QMessageBox.information(self, "Tersimpan", "Pengaturan toko & QRIS berhasil disimpan!")

    def _save_printer(self):
        db.set_setting("printer_type", self.printer_type_combo.currentText())
        db.set_setting("printer_port", self.printer_port_input.text().strip())
        db.set_setting("printer_host", self.printer_host_input.text().strip())
        db.set_setting("printer_width", self.printer_width_combo.currentText())
        QMessageBox.information(self, "Tersimpan", "Pengaturan printer berhasil disimpan!")

    def _test_print(self):
        QMessageBox.information(self, "Test Print",
                                "Kirim perintah test print ke printer...\n"
                                "Pastikan printer sudah terhubung dan menyala.")

    def _do_backup_now(self):
        backup_svc = BackupService()
        result = backup_svc.create_backup()
        if result:
            QMessageBox.information(self, "Backup Berhasil", f"Backup disimpan:\n{result}")
            self._load_backup_list()
        else:
            QMessageBox.warning(self, "Backup Gagal", "Gagal membuat backup database.")

    def _load_backup_list(self):
        backup_svc = BackupService()
        backups = backup_svc.get_backup_list()
        self.backup_table.setRowCount(len(backups))
        for row, b in enumerate(backups):
            self.backup_table.setItem(row, 0, QTableWidgetItem(b["name"]))
            size_kb = b["size"] / 1024
            self.backup_table.setItem(row, 1, QTableWidgetItem(f"{size_kb:.1f} KB"))
            self.backup_table.setItem(row, 2, QTableWidgetItem(
                format_datetime(b["created"])
            ))
            # Tombol restore per baris
            btn_restore = QPushButton("♻️ Restore")
            btn_restore.setObjectName("btn_warning")
            btn_restore.setFixedHeight(30)
            btn_restore.setCursor(QCursor(Qt.PointingHandCursor))
            btn_restore.clicked.connect(
                lambda _, path=b["path"], name=b["name"]: self._do_restore(path, name)
            )
            self.backup_table.setCellWidget(row, 3, btn_restore)

    def _do_restore(self, backup_path: str, backup_name: str):
        """Restore database dari file backup yang dipilih."""
        reply = QMessageBox.warning(
            self,
            "⚠️ Konfirmasi Restore",
            f"Restore dari:\n<b>{backup_name}</b>\n\n"
            "Data saat ini akan <b>diganti</b> dengan data dari backup tersebut.\n"
            "Backup otomatis dari kondisi saat ini akan dibuat terlebih dahulu.\n\n"
            "Lanjutkan?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        backup_svc = BackupService()
        success = backup_svc.restore_backup(backup_path)

        if success:
            QMessageBox.information(
                self,
                "Restore Berhasil",
                "Database berhasil di-restore.\n"
                "Koneksi database telah di-reload otomatis.\n\n"
                "Disarankan untuk logout dan login kembali agar semua data tampil dengan benar.",
            )
            # Refresh daftar backup dan pengaturan dari DB yang baru di-restore
            self._load_backup_list()
            self._load_settings()
        else:
            QMessageBox.critical(
                self,
                "Restore Gagal",
                "Gagal melakukan restore database.\nCek log konsol untuk detail error.",
            )

    def _manual_open_drawer(self):
        drawer = DrawerService()
        user_id = auth.current_user.id if auth.current_user else None
        result = drawer.manual_open(user_id=user_id)
        if result:
            QMessageBox.information(self, "Cash Drawer", "Cash drawer berhasil dibuka!")
            self._load_drawer_log()
        else:
            QMessageBox.warning(self, "Gagal", "Gagal membuka cash drawer.\nCek koneksi printer.")

    def _load_drawer_log(self):
        try:
            from database.models import LogDrawer
            with db.get_session() as session:
                logs = session.query(LogDrawer).order_by(
                    LogDrawer.timestamp.desc()
                ).limit(20).all()
                log_data = [
                    (l.timestamp, l.user.username if l.user else "-", l.aksi, l.keterangan or "")
                    for l in logs
                ]

            self.drawer_log_table.setRowCount(len(log_data))
            for row, (ts, user, aksi, ket) in enumerate(log_data):
                self.drawer_log_table.setItem(row, 0, QTableWidgetItem(format_datetime(ts)))
                self.drawer_log_table.setItem(row, 1, QTableWidgetItem(user))
                self.drawer_log_table.setItem(row, 2, QTableWidgetItem(aksi))
                self.drawer_log_table.setItem(row, 3, QTableWidgetItem(ket))
        except Exception as e:
            print(f"[Settings] Drawer log error: {e}")

    def refresh(self):
        self._load_settings()
        self._load_backup_list()
        self._load_drawer_log()
