"""
KasirKu Pengeluaran Page
Halaman pencatatan pengeluaran / biaya
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QDateEdit, QDoubleSpinBox,
    QTextEdit, QDialog, QFormLayout, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont, QDoubleValidator, QCursor

from database.db import db
from database.models import Pengeluaran
from auth.auth_manager import auth
from utils.helpers import format_rupiah, format_datetime
from datetime import datetime, date


KATEGORI_PENGELUARAN = [
    "Belanja Stok", "Gaji Karyawan", "Listrik", "Air",
    "Internet", "Sewa Tempat", "Operasional", "Lain-lain"
]


class PengeluaranFormDialog(QDialog):
    """Dialog tambah/edit pengeluaran"""

    def __init__(self, pengeluaran=None, parent=None):
        super().__init__(parent)
        self.pengeluaran = pengeluaran
        self.setWindowTitle("Tambah Pengeluaran" if not pengeluaran else "Edit Pengeluaran")
        self.setFixedSize(460, 420)
        self.setModal(True)
        self._setup_ui()
        if pengeluaran:
            self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("💸 " + ("Edit Pengeluaran" if self.pengeluaran else "Catat Pengeluaran Baru"))
        title.setStyleSheet("font-size: 18px; font-weight: 800; background: transparent;")
        layout.addWidget(title)

        def inp(placeholder="", height=38):
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setFixedHeight(height)
            return i

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
            return l

        form = QFormLayout()
        form.setSpacing(14)

        # Tanggal
        self.tanggal_input = QDateEdit()
        self.tanggal_input.setCalendarPopup(True)
        self.tanggal_input.setDate(QDate.currentDate())
        self.tanggal_input.setFixedHeight(38)
        form.addRow(lbl("Tanggal:"), self.tanggal_input)

        # Kategori
        self.kategori_combo = QComboBox()
        self.kategori_combo.addItems(KATEGORI_PENGELUARAN)
        self.kategori_combo.setEditable(True)
        self.kategori_combo.setFixedHeight(38)
        form.addRow(lbl("Kategori:"), self.kategori_combo)

        # Deskripsi
        self.deskripsi_input = inp("Keterangan pengeluaran...")
        form.addRow(lbl("Deskripsi:"), self.deskripsi_input)

        # Nominal
        self.nominal_input = QDoubleSpinBox()
        self.nominal_input.setPrefix("Rp ")
        self.nominal_input.setMaximum(999_999_999)
        self.nominal_input.setSingleStep(1000)
        self.nominal_input.setGroupSeparatorShown(True)
        self.nominal_input.setFixedHeight(38)
        form.addRow(lbl("Nominal:"), self.nominal_input)

        layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Simpan")
        btn_save.setFixedHeight(44)
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _populate(self):
        p = self.pengeluaran
        self.tanggal_input.setDate(QDate(p.tanggal.year, p.tanggal.month, p.tanggal.day))
        idx = self.kategori_combo.findText(p.kategori or "")
        if idx >= 0:
            self.kategori_combo.setCurrentIndex(idx)
        else:
            self.kategori_combo.setCurrentText(p.kategori or "")
        self.deskripsi_input.setText(p.deskripsi or "")
        self.nominal_input.setValue(p.nominal or 0)

    def _save(self):
        nominal = self.nominal_input.value()
        if nominal <= 0:
            self.error_lbl.setText("Nominal harus lebih dari 0!")
            self.error_lbl.show()
            return

        kategori = self.kategori_combo.currentText().strip()
        deskripsi = self.deskripsi_input.text().strip()
        q_date = self.tanggal_input.date()
        tanggal = datetime(q_date.year(), q_date.month(), q_date.day())

        with db.get_session() as session:
            if self.pengeluaran:
                p = session.query(Pengeluaran).filter_by(id=self.pengeluaran.id).first()
                if p:
                    p.tanggal = tanggal
                    p.kategori = kategori
                    p.deskripsi = deskripsi
                    p.nominal = nominal
            else:
                p = Pengeluaran(
                    tanggal=tanggal,
                    kategori=kategori,
                    deskripsi=deskripsi,
                    nominal=nominal,
                    user_id=auth.current_user.id if auth.current_user else None
                )
                session.add(p)
            session.commit()

        self.accept()


class PengeluaranPage(QWidget):
    """Halaman pengeluaran"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("💸 Pengeluaran")
        title.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        btn_add = QPushButton("+ Catat Pengeluaran")
        btn_add.setFixedHeight(40)
        btn_add.setCursor(QCursor(Qt.PointingHandCursor))
        btn_add.clicked.connect(self._open_add)
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Filters
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        date_lbl = QLabel("Dari:")
        date_lbl.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        fl.addWidget(date_lbl)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setFixedHeight(38)
        fl.addWidget(self.date_from)

        fl.addWidget(QLabel("s/d:"))

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedHeight(38)
        fl.addWidget(self.date_to)

        self.kat_filter = QComboBox()
        self.kat_filter.addItem("Semua Kategori")
        self.kat_filter.addItems(KATEGORI_PENGELUARAN)
        self.kat_filter.setFixedHeight(38)
        fl.addWidget(self.kat_filter)

        btn_filter = QPushButton("🔍 Filter")
        btn_filter.setFixedHeight(38)
        btn_filter.setCursor(QCursor(Qt.PointingHandCursor))
        btn_filter.clicked.connect(self._load_data)
        fl.addWidget(btn_filter)
        layout.addWidget(filter_frame)

        # Summary
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        layout.addWidget(self.summary_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Tanggal", "Kategori", "Deskripsi", "Nominal", "Dicatat oleh", "Aksi"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 90)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def on_theme_changed(self, theme: str):
        """Hook saat tema berubah"""
        self._load_data()

    def _load_data(self):
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        dt_from = datetime.combine(date_from, datetime.min.time())
        dt_to = datetime.combine(date_to, datetime.max.time())
        kat = self.kat_filter.currentText()

        with db.get_session() as session:
            q = session.query(Pengeluaran).filter(
                Pengeluaran.tanggal >= dt_from,
                Pengeluaran.tanggal <= dt_to
            )
            if kat != "Semua Kategori":
                q = q.filter(Pengeluaran.kategori == kat)
            pengeluaran = q.order_by(Pengeluaran.tanggal.desc()).all()
            self._data = [
                {
                    "id": p.id,
                    "tanggal": p.tanggal,
                    "kategori": p.kategori,
                    "deskripsi": p.deskripsi or "",
                    "nominal": p.nominal,
                    "user": p.user.username if p.user else "-",
                }
                for p in pengeluaran
            ]

        total = sum(d["nominal"] for d in self._data)
        self.summary_lbl.setText(
            f"{len(self._data)} catatan · Total: {format_rupiah(total)}"
        )
        self._render_table()

    def _render_table(self):
        self.table.setRowCount(len(self._data))
        is_dark = (db.get_setting("app_theme", "light") == "dark")
        text_primary = "#F1F5F9" if is_dark else "#1E293B"
        text_muted = "#94A3B8" if is_dark else "#64748B"

        for row, p in enumerate(self._data):
            self.table.setRowHeight(row, 44)
            items = [
                (format_datetime(p["tanggal"]), text_muted),
                (p["kategori"], "#2563EB" if not is_dark else "#60A5FA"),
                (p["deskripsi"], text_primary),
                (format_rupiah(p["nominal"]), "#EF4444"),
                (p["user"], text_muted),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                item.setData(Qt.UserRole, p["id"])
                self.table.setItem(row, col, item)

            # Action
            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 4, 4, 4)
            action_l.setSpacing(6)

            if auth.is_admin:
                btn_edit = QPushButton("✏️")
                btn_edit.setObjectName("btn_secondary")
                btn_edit.setFixedSize(30, 30)
                btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
                btn_edit.clicked.connect(lambda _, pid=p["id"]: self._open_edit(pid))
                action_l.addWidget(btn_edit)

                btn_del = QPushButton("🗑️")
                btn_del.setObjectName("btn_secondary")
                btn_del.setFixedSize(30, 30)
                btn_del.setCursor(QCursor(Qt.PointingHandCursor))
                btn_del.clicked.connect(lambda _, pid=p["id"]: self._delete(pid))
                action_l.addWidget(btn_del)

            self.table.setCellWidget(row, 5, action_w)

    def _open_add(self):
        dialog = PengeluaranFormDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _open_edit(self, pid: int):
        with db.get_session() as session:
            p = session.query(Pengeluaran).filter_by(id=pid).first()
            if not p:
                return
            session.expunge(p)
        dialog = PengeluaranFormDialog(pengeluaran=p, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _delete(self, pid: int):
        reply = QMessageBox.question(
            self, "Hapus Pengeluaran",
            "Yakin ingin menghapus catatan pengeluaran ini?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with db.get_session() as session:
                p = session.query(Pengeluaran).filter_by(id=pid).first()
                if p:
                    session.delete(p)
                    session.commit()
            self._load_data()

    def refresh(self):
        self._load_data()
