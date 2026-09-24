"""
KasirKu Login Window
Halaman login dengan animasi dan validasi
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QFont, QColor, QLinearGradient, QPainter, QPixmap, QPainterPath

import config
from auth.auth_manager import auth
from utils.icons import eye_icon


class LoginWindow(QWidget):
    """Window login utama"""
    login_success = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} - Login")
        self.setFixedSize(900, 640)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        # Main container
        main_frame = QFrame(self)
        main_frame.setGeometry(0, 0, 900, 640)
        main_frame.setStyleSheet("""
            QFrame {
                background-color: #0F1117;
                border-radius: 16px;
                border: 1px solid #2D3250;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        main_frame.setGraphicsEffect(shadow)

        layout = QHBoxLayout(main_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left panel - branding
        self.left_panel = self._create_left_panel()
        layout.addWidget(self.left_panel)

        # Right panel - login form
        self.right_panel = self._create_right_panel()
        layout.addWidget(self.right_panel)

    def _create_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(400)
        panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1A1D4E,
                    stop:0.4 #2D1B69,
                    stop:1 #4A1A6E);
                border-radius: 16px 0 0 16px;
                border: none;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # Logo/Icon area
        logo_frame = QFrame()
        logo_frame.setFixedSize(80, 80)
        logo_frame.setStyleSheet("""
            QFrame {
                background: rgba(108, 99, 255, 0.3);
                border-radius: 20px;
                border: 2px solid rgba(108, 99, 255, 0.5);
            }
        """)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel("🏪")
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        logo_layout.addWidget(logo_icon)
        layout.addWidget(logo_frame)
        layout.addSpacing(32)

        # App name
        app_name = QLabel(config.APP_NAME)
        app_name.setStyleSheet("""
            font-size: 36px;
            font-weight: 800;
            color: #FFFFFF;
            background: transparent;
        """)
        layout.addWidget(app_name)

        # Tagline
        tagline = QLabel("Sistem Kasir Modern\nuntuk UMKM Indonesia")
        tagline.setStyleSheet("""
            font-size: 15px;
            color: rgba(255,255,255,0.7);
            background: transparent;
            line-height: 1.6;
        """)
        tagline.setWordWrap(True)
        layout.addSpacing(12)
        layout.addWidget(tagline)

        layout.addStretch()

        # Feature list
        features = [
            ("⚡", "Transaksi Cepat"),
            ("📦", "Manajemen Stok"),
            ("🖨️", "Cetak Struk"),
            ("📊", "Laporan Lengkap"),
        ]
        for icon, text in features:
            feat_layout = QHBoxLayout()
            feat_layout.setSpacing(12)
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedWidth(24)
            icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
            text_lbl = QLabel(text)
            text_lbl.setStyleSheet("""
                color: rgba(255,255,255,0.75);
                font-size: 13px;
                background: transparent;
            """)
            feat_layout.addWidget(icon_lbl)
            feat_layout.addWidget(text_lbl)
            feat_layout.addStretch()
            layout.addLayout(feat_layout)
            layout.addSpacing(8)

        layout.addStretch()

        # Version
        ver = QLabel(f"v{config.APP_VERSION} — PKM UMKM")
        ver.setStyleSheet("""
            color: rgba(255,255,255,0.4);
            font-size: 11px;
            background: transparent;
        """)
        layout.addWidget(ver)

        return panel

    def _create_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #0F1117;
                border-radius: 0 16px 16px 0;
                border: none;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 60, 60, 60)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setObjectName("btn_icon")
        btn_close.setFixedSize(32, 32)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #EF4444;
                color: white;
            }
        """)
        btn_close.clicked.connect(self.close)
        close_layout.addWidget(btn_close)
        layout.addLayout(close_layout)

        layout.addStretch()

        # Welcome text
        welcome_lbl = QLabel("Selamat Datang 👋")
        welcome_lbl.setStyleSheet("""
            font-size: 26px;
            font-weight: 800;
            color: #F1F5F9;
        """)
        layout.addWidget(welcome_lbl)

        sub_lbl = QLabel("Masukkan kredensial Anda untuk melanjutkan")
        sub_lbl.setStyleSheet("""
            font-size: 13px;
            color: #64748B;
            margin-bottom: 8px;
        """)
        layout.addWidget(sub_lbl)
        layout.addSpacing(32)

        # Username field
        user_lbl = QLabel("Username")
        user_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        layout.addWidget(user_lbl)
        layout.addSpacing(6)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Masukkan username Anda")
        self.username_input.setFixedHeight(46)
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1D27;
                border: 1.5px solid #2D3250;
                border-radius: 10px;
                padding: 0 14px;
                color: #F1F5F9;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #6C63FF;
                background-color: #1E2235;
            }
        """)
        self.username_input.returnPressed.connect(self._do_login)
        layout.addWidget(self.username_input)
        layout.addSpacing(16)

        # Password field
        pass_lbl = QLabel("Password")
        pass_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        layout.addWidget(pass_lbl)
        layout.addSpacing(6)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Masukkan password Anda")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(46)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1D27;
                border: 1.5px solid #2D3250;
                border-radius: 10px 0 0 10px;
                padding: 0 14px;
                color: #F1F5F9;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #6C63FF;
                background-color: #1E2235;
            }
        """)
        self.password_input.returnPressed.connect(self._do_login)
        pass_row.addWidget(self.password_input)

        self.btn_show_pass = QPushButton()
        self.btn_show_pass.setIcon(eye_icon(False))
        self.btn_show_pass.setIconSize(QSize(18, 18))
        self.btn_show_pass.setFixedSize(46, 46)
        self.btn_show_pass.setCheckable(True)
        self.btn_show_pass.setCursor(Qt.PointingHandCursor)
        self.btn_show_pass.setStyleSheet("""
            QPushButton {
                background-color: #1A1D27;
                border: 1.5px solid #2D3250;
                border-left: none;
                border-radius: 0 10px 10px 0;
            }
            QPushButton:hover {
                background-color: #21263A;
            }
        """)
        self.btn_show_pass.toggled.connect(self._toggle_password)
        pass_row.addWidget(self.btn_show_pass)
        layout.addLayout(pass_row)

        # Error message
        layout.addSpacing(12)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            color: #EF4444;
            font-size: 12px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 8px 12px;
        """)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Login button
        layout.addSpacing(20)
        self.btn_login = QPushButton("Masuk")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C63FF, stop:1 #8B84FF);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B84FF, stop:1 #A09CFF);
            }
            QPushButton:pressed {
                background: #4A44CC;
            }
            QPushButton:disabled {
                background: #2D3250;
                color: #64748B;
            }
        """)
        self.btn_login.clicked.connect(self._do_login)
        layout.addWidget(self.btn_login)

        # Link daftar akun
        if config.SELF_REGISTRATION_ENABLED:
            layout.addSpacing(14)
            btn_register = QPushButton("Belum punya akun? Daftar di sini")
            btn_register.setCursor(Qt.PointingHandCursor)
            btn_register.setFlat(True)
            btn_register.setFixedHeight(30)
            btn_register.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8B84FF;
                    border: none;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #A09CFF;
                    text-decoration: underline;
                }
            """)
            btn_register.clicked.connect(self._open_register)
            layout.addWidget(btn_register)

        layout.addStretch()

        # Hint
        hint_lbl = QLabel("Default: admin / admin123  ·  kasir / kasir123")
        hint_lbl.setAlignment(Qt.AlignCenter)
        hint_lbl.setStyleSheet("""
            color: #3D4466;
            font-size: 11px;
        """)
        layout.addWidget(hint_lbl)

        return panel

    def _open_register(self):
        from ui.register_dialog import RegisterDialog
        dialog = RegisterDialog(self)
        if dialog.exec_() == RegisterDialog.Accepted and dialog.created_username:
            self.username_input.setText(dialog.created_username)
            self.password_input.clear()
            self.password_input.setFocus()
            self.error_label.hide()

    def _toggle_password(self, checked: bool):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.btn_show_pass.setIcon(eye_icon(True))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.btn_show_pass.setIcon(eye_icon(False))

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error("Username dan password harus diisi!")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Memverifikasi...")

        success, message = auth.login(username, password)

        if success:
            self.error_label.hide()

            # Cek apakah user wajib ganti password (misal password default pada first login)
            if auth.current_user and getattr(auth.current_user, "must_change_password", False):
                from ui.change_password_dialog import ChangePasswordDialog
                dlg = ChangePasswordDialog(auth.current_user.id, auth.current_user.username, self)
                if dlg.exec_() != ChangePasswordDialog.Accepted:
                    # User membatalkan ganti password -> batalkan sesi login
                    auth.logout()
                    self.btn_login.setEnabled(True)
                    self.btn_login.setText("Masuk")
                    self._show_error("Anda harus mengganti password default terlebih dahulu untuk masuk.")
                    return

            self.login_success.emit()
        else:
            self._show_error(message)
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Masuk")
            # Shake animation
            self._shake()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _shake(self):
        """Animasi shake saat login gagal"""
        self._anim = QPropertyAnimation(self.right_panel, b"geometry")
        rect = self.right_panel.geometry()
        self._anim.setDuration(300)
        self._anim.setKeyValueAt(0, rect)
        self._anim.setKeyValueAt(0.25, rect.translated(10, 0))
        self._anim.setKeyValueAt(0.5, rect.translated(-10, 0))
        self._anim.setKeyValueAt(0.75, rect.translated(5, 0))
        self._anim.setKeyValueAt(1, rect)
        self._anim.start()

    def _setup_animations(self):
        pass

    # Enable window dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
