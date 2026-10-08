"""Card visual untuk item menu custom."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor, QPixmap
from PyQt5.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QSizePolicy

import config
from database.db import db
from utils.helpers import format_rupiah


def get_product_icon_and_bg(nama: str, kategori: str = ""):
    name_lower = (nama or "").lower()
    cat_lower = (kategori or "").lower()
    if "nasi" in name_lower or "goreng" in name_lower:
        return "🍛", "#FEF3C7"
    if "teh" in name_lower or "es" in name_lower:
        return "🍹", "#ECFDF5"
    if "kopi" in name_lower:
        return "☕", "#FEF2F2"
    if "mie" in name_lower:
        return "🍜", "#FEF3C7"
    if "minuman" in cat_lower:
        return "🧋", "#DBE2EF"
    if "makanan" in cat_lower:
        return "🍱", "#FEF3C7"
    return "📦", "#F9FAFB"


class MenuCard(QFrame):
    """Kartu satu menu custom."""

    clicked = pyqtSignal(dict)
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, menu_item, parent=None):
        super().__init__(parent)
        self.menu_item = menu_item
        self._is_admin = False
        self.setObjectName("menu_card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(230)
        self.setStyleSheet("QFrame#menu_card { border-radius: 14px; border: 1px solid #E5E7EB; background: #FFFFFF; }")
        self._setup_ui()

    def set_admin_mode(self, enabled: bool):
        self._is_admin = enabled
        self.edit_btn.setVisible(enabled)
        self.delete_btn.setVisible(enabled)

    def _setup_ui(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_dark:
            self.setStyleSheet("QFrame#menu_card { border-radius: 14px; border: 1px solid #274568; background: #112D4E; }")
        else:
            self.setStyleSheet("QFrame#menu_card { border-radius: 14px; border: 1px solid #E5E7EB; background: #FFFFFF; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        banner = QLabel()
        banner.setFixedHeight(115)
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet("background: transparent; border-top-left-radius: 13px; border-top-right-radius: 13px;")

        if self.menu_item.foto:
            path = config.BASE_DIR / self.menu_item.foto if not os.path.isabs(self.menu_item.foto) else Path(self.menu_item.foto)
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    banner.setPixmap(pix.scaled(200, 115, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                else:
                    banner.setText("📷")
            else:
                banner.setText("📷")
        else:
            icon, bg = get_product_icon_and_bg(self.menu_item.nama, "")
            banner.setText(icon)
            banner.setStyleSheet(f"background-color: {bg}; font-size: 42px; border-top-left-radius: 13px; border-top-right-radius: 13px;")

        main_layout.addWidget(banner)

        body = QVBoxLayout()
        body.setContentsMargins(10, 8, 10, 8)
        body.setSpacing(2)
        name_lbl = QLabel(self.menu_item.nama)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setWordWrap(True)
        if is_dark:
            name_lbl.setStyleSheet("color: #F9FAFB; font-size: 13px; font-weight: 700; background: transparent;")
        else:
            name_lbl.setStyleSheet("color: #112D4E; font-size: 13px; font-weight: 700; background: transparent;")
        body.addWidget(name_lbl)

        price_lbl = QLabel(format_rupiah(float(self.menu_item.harga or 0)))
        price_lbl.setAlignment(Qt.AlignCenter)
        if is_dark:
            price_lbl.setStyleSheet("color: #93C5FD; font-size: 12px; font-weight: 700; background: transparent;")
        else:
            price_lbl.setStyleSheet("color: #3F72AF; font-size: 12px; font-weight: 700; background: transparent;")
        body.addWidget(price_lbl)

        if getattr(self.menu_item, "barang", None) and getattr(self.menu_item.barang, "stok", 0) == 0:
            sold_out = QLabel("Habis")
            sold_out.setAlignment(Qt.AlignCenter)
            sold_out.setStyleSheet("background: #FEE2E2; color: #DC2626; border-radius: 8px; padding: 3px; font-size: 10px; font-weight: 700;")
            body.addWidget(sold_out)

        main_layout.addLayout(body)

        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(8, 0, 8, 8)
        action_bar.setSpacing(8)

        self.edit_btn = QLabel("✏")
        self.edit_btn.setVisible(False)
        self.edit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.edit_btn.setAlignment(Qt.AlignCenter)
        self.edit_btn.setStyleSheet("background: #E0F2FE; color: #0F172A; border-radius: 12px; font-size: 13px; min-width: 26px; min-height: 26px;")
        self.edit_btn.mousePressEvent = self._edit_event

        self.delete_btn = QLabel("🗑")
        self.delete_btn.setVisible(False)
        self.delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.delete_btn.setAlignment(Qt.AlignCenter)
        self.delete_btn.setStyleSheet("background: #FEE2E2; color: #B91C1C; border-radius: 12px; font-size: 13px; min-width: 26px; min-height: 26px;")
        self.delete_btn.mousePressEvent = self._delete_event

        action_bar.addStretch()
        action_bar.addWidget(self.edit_btn)
        action_bar.addWidget(self.delete_btn)
        main_layout.addLayout(action_bar)

    def _edit_event(self, event):
        self.edit_clicked.emit(self.menu_item.id)
        event.accept()

    def _delete_event(self, event):
        self.delete_clicked.emit(self.menu_item.id)
        event.accept()

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._is_admin:
            self.edit_btn.setVisible(True)
            self.delete_btn.setVisible(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._is_admin:
            self.edit_btn.setVisible(False)
            self.delete_btn.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit({
                "id": self.menu_item.id,
                "nama": self.menu_item.nama,
                "harga": float(self.menu_item.harga or 0),
                "foto": self.menu_item.foto,
                "barang_id": getattr(self.menu_item, "barang_id", None),
            })
        super().mousePressEvent(event)
