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
from PyQt5.QtGui import QColor, QCursor

import bcrypt
from database.db import db
from database.models import User
from auth.auth_manager import auth


class UserFormDialog(QDialog):
    """Dialog form tambah/edit user"""

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Tambah User" if not user else "Edit User")
        self.setFixedSize(420, 400)
        self.setModal(True)
        self._setup_ui()
        if user:
            self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("👤 " + ("Edit User" if self.user else "Tambah User Baru"))
        title.setStyleSheet("font-size: 18px; font-weight: 800; background: transparent;")
        layout.addWidget(title)

        def inp(placeholder=""):
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setFixedHeight(40)
            return i

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
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
        form.addRow(lbl("Role:"), self.role_combo)

        self.aktif_check = QCheckBox("Akun Aktif")
        self.aktif_check.setChecked(True)
        form.addRow(lbl("Status:"), self.aktif_check)

        layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Simpan")
        btn_save.setObjectName("btn_primary")
        btn_save.setFixedHeight(44)
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
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
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        header.addWidget(title)
        header.addStretch()

        btn_add = QPushButton("+ Tambah User")
        btn_add.setFixedHeight(40)
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._open_add)
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: rgba(108, 99, 255, 0.08);
                border: 1px solid rgba(108, 99, 255, 0.25);
                border-radius: 8px;
            }
        """)
        info_l = QHBoxLayout(info_frame)
        info_l.setContentsMargins(12, 8, 12, 8)
        info_lbl = QLabel("ℹ️ Perubahan password akan berlaku saat user login berikutnya")
        info_lbl.setStyleSheet("color: #6C63FF; font-size: 12px; font-weight: 500; background: transparent;")
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
        layout.addWidget(self.table)

    def on_theme_changed(self, theme: str):
        self._load_data()

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

        is_dark = db.get_setting("app_theme", "light") == "dark"
        user_color = "#F1F5F9" if is_dark else "#0F172A"
        muted_color = "#94A3B8" if is_dark else "#64748B"

        self.table.setRowCount(len(self._users))
        for row, u in enumerate(self._users):
            self.table.setRowHeight(row, 44)

            items = [
                (str(u["id"]), muted_color),
                (u["username"], user_color),
                (u["nama"], muted_color),
                (u["role"].upper(), "#6C63FF" if u["role"] == "admin" else muted_color),
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
            action_l.setSpacing(6)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(32, 30)
            btn_edit.setObjectName("btn_secondary")
            btn_edit.setToolTip("Edit User")
            btn_edit.clicked.connect(lambda _, uid=u["id"]: self._open_edit(uid))
            action_l.addWidget(btn_edit)

            # Jangan tampilkan tombol hapus untuk user yang sedang login
            if u["id"] != (auth.current_user.id if auth.current_user else None):
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(32, 30)
                if is_dark:
                    btn_del.setStyleSheet("""
                        QPushButton {
                            background: #2D1A1A; color: #EF4444; border: 1px solid #4D2020; border-radius: 6px; font-size: 12px;
                        }
                        QPushButton:hover { background: #EF4444; color: white; }
                    """)
                else:
                    btn_del.setStyleSheet("""
                        QPushButton {
                            background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; border-radius: 6px; font-size: 12px;
                        }
                        QPushButton:hover { background: #FCA5A5; }
                    """)
                btn_del.setToolTip("Hapus / Nonaktifkan User")
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
