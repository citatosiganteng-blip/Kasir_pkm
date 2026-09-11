"""
KasirKu User Management
Halaman manajemen pengguna (admin only)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QComboBox, QMessageBox, QDialog, QFormLayout,
    QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import bcrypt
from database.db import db
from database.models import User
from auth.auth_manager import auth


class UserFormDialog(QDialog):
    """Dialog form tambah/edit user"""

    def __init__(self, user: User = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Tambah User" if not user else "Edit User")
        self.setFixedSize(420, 400)
        self.setModal(True)
        self.setStyleSheet("QDialog { background: #1A1D27; }")
        self._setup_ui()
        if user:
            self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("👤 " + ("Edit User" if self.user else "Tambah User Baru"))
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F1F5F9;")
        layout.addWidget(title)

        def inp(placeholder=""):
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setFixedHeight(40)
            i.setStyleSheet("""
                QLineEdit {
                    background: #21263A; border: 1px solid #2D3250;
                    border-radius: 8px; padding: 0 12px; color: #F1F5F9; font-size: 13px;
                }
                QLineEdit:focus { border-color: #6C63FF; }
            """)
            return i

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        lbl_s = "color: #94A3B8; font-size: 12px; font-weight: 600;"

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(lbl_s)
            return l

        self.nama_input = inp("Nama lengkap user")
        form.addRow(lbl("Nama Lengkap:"), self.nama_input)

        self.username_input = inp("username (huruf kecil, tanpa spasi)")
        form.addRow(lbl("Username *:"), self.username_input)

        self.password_input = inp("Password baru (minimal 6 karakter)")
        self.password_input.setEchoMode(QLineEdit.Password)
        hint = "" if not self.user else "(kosongkan jika tidak ingin ubah)"
        self.password_input.setPlaceholderText(
            f"Password baru {hint}"
        )
        form.addRow(lbl("Password *:"), self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["kasir", "admin"])
        self.role_combo.setFixedHeight(40)
        self.role_combo.setStyleSheet("""
            QComboBox {
                background: #21263A; border: 1px solid #2D3250;
                border-radius: 8px; padding: 0 12px; color: #F1F5F9; font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background: #21263A; selection-background-color: #6C63FF;
            }
        """)
        form.addRow(lbl("Role:"), self.role_combo)

        self.aktif_check = QCheckBox("Akun Aktif")
        self.aktif_check.setChecked(True)
        self.aktif_check.setStyleSheet("color: #F1F5F9; font-size: 13px;")
        form.addRow(lbl("Status:"), self.aktif_check)

        layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #21263A; color: #94A3B8;
                border: 1px solid #2D3250; border-radius: 8px; font-size: 13px;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Simpan")
        btn_save.setFixedHeight(44)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #6C63FF; color: white;
                border: none; border-radius: 8px; font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #8B84FF; }
        """)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _populate(self):
        u = self.user
        self.nama_input.setText(u.nama_lengkap or "")
        self.username_input.setText(u.username)
        idx = self.role_combo.findText(u.role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        self.aktif_check.setChecked(u.aktif)

    def _save(self):
        nama = self.nama_input.text().strip()
        username = self.username_input.text().strip().lower().replace(" ", "")
        password = self.password_input.text()
        role = self.role_combo.currentText()
        aktif = self.aktif_check.isChecked()

        if not username:
            self.error_lbl.setText("Username harus diisi!")
            self.error_lbl.show()
            return

        if not self.user and not password:
            self.error_lbl.setText("Password harus diisi untuk user baru!")
            self.error_lbl.show()
            return

        if password and len(password) < 6:
            self.error_lbl.setText("Password minimal 6 karakter!")
            self.error_lbl.show()
            return

        with db.get_session() as session:
            # Cek duplikat username
            dup = session.query(User).filter(User.username == username)
            if self.user:
                dup = dup.filter(User.id != self.user.id)
            if dup.first():
                self.error_lbl.setText(f"Username '{username}' sudah digunakan!")
                self.error_lbl.show()
                return

            if self.user:
                u = session.query(User).filter_by(id=self.user.id).first()
                if u:
                    u.nama_lengkap = nama
                    u.username = username
                    u.role = role
                    u.aktif = aktif
                    if password:
                        u.password_hash = bcrypt.hashpw(
                            password.encode(), bcrypt.gensalt()
                        ).decode()
            else:
                pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                u = User(
                    username=username,
                    password_hash=pw_hash,
                    role=role,
                    nama_lengkap=nama,
                    aktif=aktif
                )
                session.add(u)

            session.commit()

        self.accept()


class UserManagementPage(QWidget):
    """Halaman manajemen user"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("👥 Manajemen User")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #F1F5F9;")
        header.addWidget(title)
        header.addStretch()

        btn_add = QPushButton("+ Tambah User")
        btn_add.setFixedHeight(40)
        btn_add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C63FF, stop:1 #8B84FF);
                color: white; border: none; border-radius: 8px;
                padding: 0 20px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #8B84FF; }
        """)
        btn_add.clicked.connect(self._open_add)
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: rgba(108, 99, 255, 0.1);
                border: 1px solid rgba(108, 99, 255, 0.3);
                border-radius: 8px;
            }
        """)
        info_l = QHBoxLayout(info_frame)
        info_l.setContentsMargins(12, 8, 12, 8)
        info_lbl = QLabel("ℹ️ Perubahan password akan berlaku saat user login berikutnya")
        info_lbl.setStyleSheet("color: #8B84FF; font-size: 12px; background: transparent;")
        info_l.addWidget(info_lbl)
        layout.addWidget(info_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Username", "Nama Lengkap", "Role", "Status", "Aksi"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 120)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
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
        layout.addWidget(self.table)

    def _load_data(self):
        with db.get_session() as session:
            users = session.query(User).order_by(User.role, User.username).all()
            self._users = [
                {
                    "id": u.id,
                    "username": u.username,
                    "nama": u.nama_lengkap or "-",
                    "role": u.role,
                    "aktif": u.aktif,
                }
                for u in users
            ]

        self.table.setRowCount(len(self._users))
        for row, u in enumerate(self._users):
            self.table.setRowHeight(row, 44)

            items = [
                (str(u["id"]), "#64748B"),
                (u["username"], "#F1F5F9"),
                (u["nama"], "#94A3B8"),
                (u["role"].upper(), "#6C63FF" if u["role"] == "admin" else "#94A3B8"),
            ]
            for col, (val, color) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                self.table.setItem(row, col, item)

            # Status
            status_text = "✅ Aktif" if u["aktif"] else "❌ Nonaktif"
            status_color = "#10B981" if u["aktif"] else "#EF4444"
            s_item = QTableWidgetItem(status_text)
            s_item.setForeground(QColor(status_color))
            self.table.setItem(row, 4, s_item)

            # Actions
            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 4, 4, 4)
            action_l.setSpacing(4)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(30, 30)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background: #21263A; border: 1px solid #2D3250; border-radius: 6px; font-size: 13px;
                }
                QPushButton:hover { background: #6C63FF; border-color: #6C63FF; }
            """)
            btn_edit.clicked.connect(lambda _, uid=u["id"]: self._open_edit(uid))
            action_l.addWidget(btn_edit)

            # Jangan tampilkan tombol hapus untuk user yang sedang login
            if u["id"] != (auth.current_user.id if auth.current_user else None):
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(30, 30)
                btn_del.setStyleSheet("""
                    QPushButton {
                        background: #21263A; border: 1px solid #2D3250; border-radius: 6px; font-size: 13px;
                    }
                    QPushButton:hover { background: #EF4444; border-color: #EF4444; }
                """)
                btn_del.clicked.connect(lambda _, uid=u["id"]: self._delete_user(uid))
                action_l.addWidget(btn_del)

            self.table.setCellWidget(row, 5, action_w)

    def _open_add(self):
        dialog = UserFormDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _open_edit(self, uid: int):
        with db.get_session() as session:
            u = session.query(User).filter_by(id=uid).first()
            if not u:
                return
            session.expunge(u)
        dialog = UserFormDialog(user=u, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_data()

    def _delete_user(self, uid: int):
        reply = QMessageBox.question(
            self, "Hapus User",
            "Yakin ingin menghapus user ini?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with db.get_session() as session:
                u = session.query(User).filter_by(id=uid).first()
                if u:
                    u.aktif = False
                    session.commit()
            self._load_data()

    def refresh(self):
        self._load_data()
