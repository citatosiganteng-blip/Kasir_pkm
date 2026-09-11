"""
KasirKu Main Window
Jendela utama dengan sidebar navigasi dan content area
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSizePolicy,
    QStatusBar, QMessageBox, QAction, QToolBar, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon
from datetime import datetime

from auth.auth_manager import auth
from ui.styles import MAIN_STYLESHEET, SIDEBAR_STYLE
import config


class SidebarButton(QPushButton):
    """Tombol sidebar navigasi"""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}")
        self.setObjectName("sidebar_btn")
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._is_active = False

    def set_active(self, active: bool):
        self._is_active = active
        self.setObjectName("sidebar_btn_active" if active else "sidebar_btn")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    """Jendela utama aplikasi"""
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.showMaximized()
        self.setStyleSheet(MAIN_STYLESHEET + SIDEBAR_STYLE)
        self._sidebar_buttons = []
        self._pages = {}
        self._setup_ui()
        self._setup_status_bar()
        self._start_clock()
        self._start_backup_timer()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === SIDEBAR ===
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        # Logo / App name
        logo_frame = QFrame()
        logo_frame.setStyleSheet("""
            QFrame {
                background: rgba(108, 99, 255, 0.15);
                border-radius: 12px;
                border: 1px solid rgba(108, 99, 255, 0.3);
            }
        """)
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(14, 12, 14, 12)
        logo_layout.setSpacing(10)

        logo_icon = QLabel("🏪")
        logo_icon.setStyleSheet("font-size: 24px; background: transparent;")
        logo_layout.addWidget(logo_icon)

        logo_text_layout = QVBoxLayout()
        logo_text_layout.setSpacing(0)
        app_name_lbl = QLabel(config.APP_NAME)
        app_name_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #F1F5F9; background: transparent;")
        logo_text_layout.addWidget(app_name_lbl)
        ver_lbl = QLabel(f"v{config.APP_VERSION}")
        ver_lbl.setStyleSheet("font-size: 10px; color: #64748B; background: transparent;")
        logo_text_layout.addWidget(ver_lbl)
        logo_layout.addLayout(logo_text_layout)
        logo_layout.addStretch()

        sidebar_layout.addWidget(logo_frame)
        sidebar_layout.addSpacing(16)

        # Section label
        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("""
                color: #3D4466;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            """)
            return lbl

        sidebar_layout.addWidget(section_label("UTAMA"))
        sidebar_layout.addSpacing(4)

        # Navigation buttons
        nav_items = [
            ("🏠", "Dashboard", "dashboard"),
            ("💳", "Kasir (POS)", "kasir"),
            ("📋", "Riwayat Transaksi", "riwayat"),
        ]

        for icon, text, key in nav_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            sidebar_layout.addWidget(btn)
            self._sidebar_buttons.append((key, btn))

        sidebar_layout.addSpacing(12)
        sidebar_layout.addWidget(section_label("MANAJEMEN"))
        sidebar_layout.addSpacing(4)

        manage_items = [
            ("📦", "Barang & Stok", "barang"),
            ("💸", "Pengeluaran", "pengeluaran"),
            ("📊", "Laporan", "laporan"),
        ]

        for icon, text, key in manage_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            sidebar_layout.addWidget(btn)
            self._sidebar_buttons.append((key, btn))

        # Admin section
        if auth.is_admin:
            sidebar_layout.addSpacing(12)
            sidebar_layout.addWidget(section_label("ADMIN"))
            sidebar_layout.addSpacing(4)

            admin_items = [
                ("👥", "Manajemen User", "users"),
                ("⚙️", "Pengaturan", "settings"),
            ]
            for icon, text, key in admin_items:
                btn = SidebarButton(icon, text)
                btn.clicked.connect(lambda _, k=key: self._navigate(k))
                sidebar_layout.addWidget(btn)
                self._sidebar_buttons.append((key, btn))

        sidebar_layout.addStretch()

        # User info
        sidebar_layout.addWidget(section_label("SESSION"))
        sidebar_layout.addSpacing(4)

        user_frame = QFrame()
        user_frame.setStyleSheet("""
            QFrame {
                background: #21263A;
                border-radius: 10px;
                border: 1px solid #2D3250;
            }
        """)
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(12, 10, 12, 10)
        user_layout.setSpacing(10)

        user_icon = QLabel("👤")
        user_icon.setStyleSheet("font-size: 18px; background: transparent;")
        user_layout.addWidget(user_icon)

        user_text = QVBoxLayout()
        user_text.setSpacing(0)
        username = auth.current_user.nama_lengkap or auth.current_user.username if auth.current_user else ""
        user_name_lbl = QLabel(username)
        user_name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #F1F5F9; background: transparent;")
        user_name_lbl.setMaximumWidth(130)
        user_text.addWidget(user_name_lbl)

        role_lbl = QLabel(auth.current_user.role.upper() if auth.current_user else "")
        role_lbl.setStyleSheet("font-size: 10px; color: #6C63FF; font-weight: 600; background: transparent;")
        user_text.addWidget(role_lbl)
        user_layout.addLayout(user_text)
        user_layout.addStretch()
        sidebar_layout.addWidget(user_frame)

        # Logout button
        btn_logout = QPushButton("⬅️ Logout")
        btn_logout.setObjectName("sidebar_btn")
        btn_logout.setFixedHeight(40)
        btn_logout.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
                margin-top: 4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.1);
                border-color: #EF4444;
            }
        """)
        btn_logout.clicked.connect(self._logout)
        sidebar_layout.addWidget(btn_logout)

        main_layout.addWidget(self.sidebar)

        # === CONTENT AREA ===
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("QStackedWidget { background: #0F1117; }")
        main_layout.addWidget(self.content_stack)

        # Load semua pages
        self._load_pages()

        # Default: dashboard
        self._navigate("dashboard")

    def _load_pages(self):
        """Load semua halaman"""
        from ui.dashboard import DashboardPage
        from ui.barang.barang_page import BarangPage
        from ui.transaksi.kasir_page import KasirPage
        from ui.transaksi.riwayat_page import RiwayatTransaksiPage
        from ui.pengeluaran.pengeluaran_page import PengeluaranPage
        from ui.laporan.laporan_page import LaporanPage

        self._pages["dashboard"] = DashboardPage(on_navigate=self._navigate)
        self._pages["kasir"] = KasirPage()
        self._pages["riwayat"] = RiwayatTransaksiPage()
        self._pages["barang"] = BarangPage()
        self._pages["pengeluaran"] = PengeluaranPage()
        self._pages["laporan"] = LaporanPage()

        if auth.is_admin:
            from ui.admin.user_management import UserManagementPage
            self._pages["users"] = UserManagementPage()

            from ui.settings_page import SettingsPage
            self._pages["settings"] = SettingsPage()

        for page in self._pages.values():
            self.content_stack.addWidget(page)

        # Connect kasir transaction completed signal
        if "kasir" in self._pages:
            self._pages["kasir"].transaction_completed.connect(self._on_transaction_complete)

    def _navigate(self, key: str):
        """Navigasi ke halaman"""
        if key not in self._pages:
            return

        # Update sidebar buttons
        for btn_key, btn in self._sidebar_buttons:
            btn.set_active(btn_key == key)

        # Switch page
        self.content_stack.setCurrentWidget(self._pages[key])

        # Refresh halaman
        page = self._pages[key]
        if hasattr(page, "refresh"):
            page.refresh()

    def _on_transaction_complete(self):
        """Callback saat transaksi selesai"""
        # Refresh dashboard
        if "dashboard" in self._pages:
            self._pages["dashboard"]._load_data()

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #0F1117;
                color: #64748B;
                font-size: 12px;
                border-top: 1px solid #2D3250;
            }
        """)
        self.setStatusBar(self.status_bar)

        store_name = config.STORE_NAME
        self.status_bar.showMessage(f"  {config.APP_NAME} v{config.APP_VERSION}  ·  {store_name}")

        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet("color: #64748B; font-size: 12px; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.clock_lbl)

    def _start_clock(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%d/%m/%Y  %H:%M:%S"))

    def _start_backup_timer(self):
        """Timer backup otomatis harian"""
        from services.backup_service import BackupService
        self._backup_service = BackupService()

        # Backup setiap 8 jam (28800 detik)
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(self._do_backup)
        self._backup_timer.start(8 * 60 * 60 * 1000)

    def _do_backup(self):
        """Jalankan backup database"""
        result = self._backup_service.create_backup()
        if result:
            print(f"[MainWindow] Auto-backup: {result}")

    def _logout(self):
        reply = QMessageBox.question(
            self, "Konfirmasi Logout",
            "Yakin ingin keluar dari sistem?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            auth.logout()
            self.logout_requested.emit()
            self.close()

    def closeEvent(self, event):
        """Handle window close"""
        reply = QMessageBox.question(
            self, "Keluar",
            "Yakin ingin menutup aplikasi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Backup sebelum tutup
            try:
                from services.backup_service import BackupService
                BackupService().create_backup()
            except Exception:
                pass
            event.accept()
        else:
            event.ignore()
