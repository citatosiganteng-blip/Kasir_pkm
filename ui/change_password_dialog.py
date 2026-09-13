"""
KasirKu - Change Password Dialog
Dialog modal untuk mewajibkan penggantian password default pada first login
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt

from auth.auth_manager import auth


class ChangePasswordDialog(QDialog):
    """Modal dialog untuk ganti password wajib"""

    def __init__(self, user_id: int, username: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("Ganti Password Wajib 🔐")
        self.setFixedSize(440, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        # Header Icon + Title
        title_lbl = QLabel("🔐 Ganti Password Wajib")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            f"Halo, <b>{self.username}</b>! Akun Anda masih menggunakan password default.<br>"
            "Demi keamanan, silakan buat password baru sebelum melanjutkan."
        )
        desc_lbl.setStyleSheet("font-size: 12px; line-height: 1.4;")
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addSpacing(6)

        # Input Helper
        def create_input_field(label_text: str, placeholder: str):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
            layout.addWidget(lbl)

            row = QHBoxLayout()
            row.setSpacing(4)

            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.Password)
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(40)

            btn_toggle = QPushButton("👁")
            btn_toggle.setFixedSize(40, 40)
            btn_toggle.setCheckable(True)
            btn_toggle.setObjectName("btn_secondary")
            btn_toggle.toggled.connect(
                lambda chk, field=inp, btn=btn_toggle: (
                    field.setEchoMode(QLineEdit.Normal if chk else QLineEdit.Password),
                    btn.setText("🙈" if chk else "👁")
                )
            )

            row.addWidget(inp)
            row.addWidget(btn_toggle)
            layout.addLayout(row)
            return inp

        self.old_pass_input = create_input_field("Password Lama / Default:", "Masukkan password saat ini")
        self.new_pass_input = create_input_field("Password Baru (min. 6 karakter):", "Masukkan password baru")
        self.confirm_pass_input = create_input_field("Konfirmasi Password Baru:", "Ulangi password baru")

        # Error label
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

        layout.addSpacing(8)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.setObjectName("btn_secondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton("Simpan Password")
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.setObjectName("btn_primary")
        self.btn_submit.clicked.connect(self._do_change_password)
        btn_layout.addWidget(self.btn_submit)

        layout.addLayout(btn_layout)

    def _show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _do_change_password(self):
        old_pass = self.old_pass_input.text()
        new_pass = self.new_pass_input.text()
        confirm_pass = self.confirm_pass_input.text()

        if not old_pass or not new_pass or not confirm_pass:
            self._show_error("Semua kolom harus diisi!")
            return

        if len(new_pass) < 6:
            self._show_error("Password baru minimal 6 karakter!")
            return

        if new_pass != confirm_pass:
            self._show_error("Konfirmasi password baru tidak cocok!")
            return

        if new_pass == old_pass:
            self._show_error("Password baru tidak boleh sama dengan password lama!")
            return

        success, msg = auth.change_password(self.user_id, old_pass, new_pass)
        if success:
            QMessageBox.information(
                self, "Berhasil ✅",
                "Password berhasil diperbarui! Anda sekarang dapat masuk ke aplikasi."
            )
            self.accept()
        else:
            self._show_error(msg)
