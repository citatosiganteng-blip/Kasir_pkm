"""
KasirKu - Register Dialog
Dialog pendaftaran akun mandiri, dibuka dari layar login.
Role tetap disimpan sebagai "admin" / "kasir" di database,
tetapi label yang tampil ke pengguna bisa dikustomisasi lewat
config.ROLE_LABELS (misal "Guru" / "Murid").
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QSize

import bcrypt
import config
from database.db import db
from database.models import User
from utils.icons import eye_icon


EYE_BTN_STYLE = """
    QPushButton {
        background-color: #1A1D27;
        border: 1.5px solid #2D3250;
        border-left: none;
        border-radius: 0 8px 8px 0;
    }
    QPushButton:hover {
        background-color: #21263A;
    }
"""


class RegisterDialog(QDialog):
    """Dialog pendaftaran akun baru (admin atau kasir) dari layar login."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.created_username = None
        self.setWindowTitle(f"Daftar Akun - {config.APP_NAME}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        # Ukuran dihitung dari kebutuhan konten sesungguhnya (bukan angka
        # tebakan) supaya tidak ada teks yang terpotong/klip di layar manapun.
        self.setFixedWidth(440)
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(10)

        title = QLabel("📝 Buat Akun Baru")
        title.setStyleSheet("font-size: 18px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Isi data di bawah ini untuk membuat akun login baru.")
        desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(4)

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet("font-size: 12px; font-weight: 600;")
            layout.addWidget(l)
            return l

        def inp(placeholder=""):
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setFixedHeight(42)
            layout.addWidget(i)
            return i

        def password_field(placeholder=""):
            """Input password + tombol ikon mata (bukan emoji) untuk
            menampilkan/menyembunyikan isian."""
            row = QHBoxLayout()
            row.setSpacing(0)

            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(42)
            edit.setEchoMode(QLineEdit.Password)
            row.addWidget(edit)

            btn = QPushButton()
            btn.setIcon(eye_icon(False))
            btn.setIconSize(QSize(16, 16))
            btn.setFixedSize(42, 42)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(EYE_BTN_STYLE)
            btn.toggled.connect(lambda checked, e=edit, b=btn: (
                e.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password),
                b.setIcon(eye_icon(checked)),
            ))
            row.addWidget(btn)

            layout.addLayout(row)
            return edit

        lbl("Nama Lengkap:")
        self.nama_input = inp("Nama lengkap Anda")

        lbl("Username:")
        self.username_input = inp("Username (huruf kecil, tanpa spasi)")

        lbl("Password (min. 6 karakter):")
        self.password_input = password_field("Buat password")

        lbl("Konfirmasi Password:")
        self.confirm_input = password_field("Ulangi password")

        role_admin_label = config.get_role_label("admin")
        role_kasir_label = config.get_role_label("kasir")

        lbl("Daftar sebagai:")
        self.role_combo = QComboBox()
        self.role_combo.setFixedHeight(42)
        # data disimpan tetap "kasir"/"admin", hanya label tampilan yang custom
        self.role_combo.addItem(role_kasir_label, "kasir")
        self.role_combo.addItem(role_admin_label, "admin")
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        layout.addWidget(self.role_combo)

        # Kolom kode admin SELALU ditampilkan (tidak disembunyikan secara
        # dinamis) agar tinggi dialog tetap konsisten dan tidak ada
        # elemen yang terpotong saat role diganti.
        self.admin_code_label = QLabel(f"Kode Pendaftaran {role_admin_label} (isi jika mendaftar sebagai {role_admin_label}):")
        self.admin_code_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
        self.admin_code_label.setWordWrap(True)
        layout.addWidget(self.admin_code_label)
        self.admin_code_input = QLineEdit()
        self.admin_code_input.setPlaceholderText(f"Kosongkan jika daftar sebagai {role_kasir_label}")
        self.admin_code_input.setEchoMode(QLineEdit.Password)
        self.admin_code_input.setFixedHeight(42)
        layout.addWidget(self.admin_code_input)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("""
            color: #EF4444;
            font-size: 11px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 6px 10px;
        """)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setFixedHeight(44)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Daftar")
        btn_save.setObjectName("btn_primary")
        btn_save.setFixedHeight(44)
        btn_save.clicked.connect(self._do_register)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _on_role_changed(self, _index):
        role_label = config.get_role_label(self.role_combo.currentData())
        self.admin_code_input.setPlaceholderText(
            f"Wajib diisi untuk mendaftar sebagai {config.get_role_label('admin')}"
            if self.role_combo.currentData() == "admin"
            else f"Kosongkan jika daftar sebagai {role_label}"
        )

    def _show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _do_register(self):
        nama = self.nama_input.text().strip()
        username = self.username_input.text().strip().lower().replace(" ", "")
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        role = self.role_combo.currentData()
        admin_code = self.admin_code_input.text().strip()

        if not nama or not username or not password or not confirm:
            self._show_error("Semua kolom wajib diisi!")
            return

        if len(password) < 6:
            self._show_error("Password minimal 6 karakter!")
            return

        if password != confirm:
            self._show_error("Konfirmasi password tidak cocok!")
            return

        if role == "admin":
            if not config.ADMIN_REGISTER_CODE:
                self._show_error(f"Pendaftaran {config.get_role_label('admin')} baru dinonaktifkan.")
                return
            if admin_code != config.ADMIN_REGISTER_CODE:
                self._show_error(f"Kode pendaftaran {config.get_role_label('admin')} salah!")
                return

        with db.get_session() as session:
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                self._show_error(f"Username '{username}' sudah digunakan!")
                return

            pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = User(
                username=username,
                password_hash=pw_hash,
                role=role,
                nama_lengkap=nama,
                aktif=True,
                must_change_password=False,
            )
            session.add(user)

        self.created_username = username
        QMessageBox.information(
            self, "Berhasil ✅",
            f"Akun '{username}' sebagai {config.get_role_label(role)} berhasil dibuat.\n"
            "Silakan login dengan akun tersebut."
        )
        self.accept()
