"""
KasirKu Main Window
Jendela utama dengan Left Sidebar Navigation modern matching reference design
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSizePolicy,
    QStatusBar, QMessageBox, QSpacerItem, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QCursor
from datetime import datetime

from auth.auth_manager import auth
from database.db import db
from ui.styles import MAIN_STYLESHEET, BOTTOM_NAV_STYLE, get_theme_stylesheet
import config


class SidebarNavButton(QPushButton):
    """Tombol navigasi sidebar vertikal dengan ikon kiri + teks"""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}")
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setObjectName("nav_btn_sidebar")
        self._is_active = False

    def set_active(self, active: bool):
        self._is_active = active
        self.setObjectName("nav_btn_sidebar_active" if active else "nav_btn_sidebar")
        self.style().unpolish(self)
        self.style().polish(self)


# Compatibility alias
BottomNavButton = SidebarNavButton


class MainWindow(QMainWindow):
    """Jendela utama aplikasi dengan Left Sidebar Navigation modern"""
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_VERSION}")
        self.setMinimumSize(1100, 720)
        self.showMaximized()

        self._current_theme = db.get_setting("app_theme", "dark")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(self._current_theme))
        else:
            self.setStyleSheet(get_theme_stylesheet(self._current_theme))

        self._nav_buttons = []
        self._pages = {}

        self._setup_ui()
        self._start_clock()
        self._start_backup_timer()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("main_central_widget")
        self.setCentralWidget(central)

        # Outer horizontal layout: sidebar | content_area
        outer_layout = QHBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # =====================================================================
        # LEFT SIDEBAR
        # =====================================================================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(165)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        # Brand: logo + store name
        brand_widget = QWidget()
        brand_widget.setStyleSheet("background: transparent;")
        brand_layout = QHBoxLayout(brand_widget)
        brand_layout.setContentsMargins(4, 0, 4, 0)
        brand_layout.setSpacing(8)

        store_name = db.get_setting("store_name", config.APP_NAME)
        brand_icon_lbl = QLabel("🏪")
        brand_icon_lbl.setObjectName("sidebar_brand_icon")
        brand_icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        brand_layout.addWidget(brand_icon_lbl)

        brand_lbl = QLabel(store_name)
        brand_lbl.setObjectName("sidebar_brand_lbl")
        brand_layout.addWidget(brand_lbl)
        brand_layout.addStretch()

        sidebar_layout.addWidget(brand_widget)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.1); margin: 8px 0px;")
        sidebar_layout.addWidget(div)
        sidebar_layout.addSpacing(4)

        # Nav items
        nav_items = [
            ("🏠", "Beranda/Kasir", "kasir"),
            ("📋", "Transaksi", "riwayat"),
            ("📦", "Barang", "barang"),
            ("🧾", "Faktur/PO", "pembelian"),
            ("📊", "Laporan", "laporan"),
        ]

        if auth.is_admin:
            nav_items.append(("⚙️", "Pengaturan", "settings"))

        for icon, text, key in nav_items:
            btn = SidebarNavButton(icon, text)
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append((key, btn))

        sidebar_layout.addStretch()

        # Divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255,255,255,0.1); margin: 4px 0px;")
        sidebar_layout.addWidget(div2)

        # Logout button
        btn_logout = QPushButton("  🚪  Keluar")
        btn_logout.setObjectName("nav_btn_logout")
        btn_logout.setFixedHeight(44)
        btn_logout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_logout.setCursor(QCursor(Qt.PointingHandCursor))
        btn_logout.clicked.connect(self._logout)
        sidebar_layout.addWidget(btn_logout)

        outer_layout.addWidget(sidebar)

        # =====================================================================
        # RIGHT AREA: top bar + stacked content
        # =====================================================================
        right_area = QWidget()
        right_area.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # --- Top Bar ---
        top_bar = QFrame()
        top_bar.setObjectName("content_top_bar")
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(12)

        # App title
        topbar_title = QLabel("KasirKu POS")
        topbar_title.setObjectName("topbar_title")
        top_layout.addWidget(topbar_title)

        top_layout.addStretch()

        # Clock
        self.clock_lbl = QLabel()
        self.clock_lbl.setObjectName("topbar_clock")
        top_layout.addWidget(self.clock_lbl)

        # Theme toggle button (moon/sun icon)
        self.btn_theme_toggle = QPushButton(
            "🌙 Mode Gelap" if self._current_theme == "light" else "☀️ Mode Terang"
        )
        self.btn_theme_toggle.setObjectName("btn_theme_toggle")
        self.btn_theme_toggle.setFixedHeight(34)
        self.btn_theme_toggle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_theme_toggle.setToolTip("Ganti Mode Tampilan (Terang / Gelap)")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        top_layout.addWidget(self.btn_theme_toggle)

        # User avatar circle (initials)
        user_name = ""
        role_name = ""
        if auth.current_user:
            user_name = auth.current_user.nama_lengkap or auth.current_user.username
            role_name = auth.current_user.role.capitalize()

        initials = ""
        if user_name:
            parts = user_name.strip().split()
            initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()

        avatar_lbl = QLabel(initials or "👤")
        avatar_lbl.setObjectName("user_avatar_lbl")
        avatar_lbl.setFixedSize(32, 32)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(avatar_lbl)

        # User name + status
        user_info_widget = QWidget()
        user_info_widget.setStyleSheet("background: transparent;")
        user_info_layout = QVBoxLayout(user_info_widget)
        user_info_layout.setContentsMargins(0, 0, 0, 0)
        user_info_layout.setSpacing(1)

        user_name_lbl = QLabel(user_name)
        user_name_lbl.setObjectName("user_name_lbl")
        user_info_layout.addWidget(user_name_lbl)

        status_badge = QLabel("● Active")
        status_badge.setObjectName("user_status_badge")
        user_info_layout.addWidget(status_badge)

        top_layout.addWidget(user_info_widget)
        right_layout.addWidget(top_bar)

        # --- Stacked Content ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(
            "QStackedWidget { background: transparent; border: none; }"
        )
        right_layout.addWidget(self.content_stack, 1)

        outer_layout.addWidget(right_area, 1)

        # Load semua pages
        self._load_pages()

        # Default: Kasir POS
        self._navigate("kasir")

    def _load_pages(self):
        """Load semua halaman"""
        from ui.dashboard import DashboardPage
        from ui.barang.barang_page import BarangPage
        from ui.transaksi.kasir_page import KasirPage
        from ui.transaksi.riwayat_page import RiwayatTransaksiPage
        from ui.pengeluaran.pengeluaran_page import PengeluaranPage
        from ui.pembelian.pembelian_page import PembelianPage
        from ui.laporan.laporan_page import LaporanPage

        self._pages["dashboard"] = DashboardPage(on_navigate=self._navigate)
        self._pages["kasir"] = KasirPage()
        self._pages["riwayat"] = RiwayatTransaksiPage()
        self._pages["barang"] = BarangPage()
        self._pages["pembelian"] = PembelianPage()
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

        # Update status tombol navigasi
        for k, btn in self._nav_buttons:
            btn.set_active(k == key)

        # Ganti halaman
        page = self._pages[key]
        self.content_stack.setCurrentWidget(page)

        # Refresh page jika punya method refresh
        if hasattr(page, "refresh"):
            page.refresh()

    def _on_transaction_complete(self):
        """Callback saat transaksi selesai"""
        if "dashboard" in self._pages:
            self._pages["dashboard"]._load_data()

    def _toggle_theme(self):
        """Toggle antara Mode Terang dan Mode Gelap"""
        self._current_theme = "dark" if self._current_theme == "light" else "light"
        db.set_setting("app_theme", self._current_theme)

        new_style = get_theme_stylesheet(self._current_theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(new_style)
        else:
            self.setStyleSheet(new_style)

        self.btn_theme_toggle.setText(
            "🌙 Mode Gelap" if self._current_theme == "light" else "☀️ Mode Terang"
        )

        # Re-polish all nav buttons
        for _, btn in self._nav_buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Beritahu semua halaman yang memiliki hook on_theme_changed
        for page in self._pages.values():
            if hasattr(page, "on_theme_changed"):
                try:
                    page.on_theme_changed(self._current_theme)
                except Exception as e:
                    print(f"[MainWindow] Error updating page theme: {e}")

    def _start_clock(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%d/%m/%Y  %H:%M:%S"))

    def _start_backup_timer(self):
        """Timer backup otomatis harian (setiap 8 jam)"""
        from services.backup_service import BackupService
        self._backup_service = BackupService()

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
            try:
                from services.backup_service import BackupService
                BackupService().create_backup()
            except Exception:
                pass
            event.accept()
        else:
            event.ignore()
