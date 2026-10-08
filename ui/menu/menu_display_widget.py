"""Widget tampilan grid menu custom untuk kasir."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QGridLayout, QMessageBox
)

from auth.auth_manager import auth
from database.db import db
from database.models import MenuItem
from ui.menu.menu_card import MenuCard


class MenuDisplayWidget(QWidget):
    """Widget utama menampilkan menu grid custom."""

    item_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items = []
        self._filtered_items = []
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari menu...")
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input)

        self.add_btn = QPushButton("+ Tambah Menu")
        self.add_btn.clicked.connect(self._add_new_menu)
        toolbar.addWidget(self.add_btn)

        self.delete_all_btn = QPushButton("🗑 Hapus Semua")
        self.delete_all_btn.clicked.connect(self._delete_all)
        toolbar.addWidget(self.delete_all_btn)

        layout.addLayout(toolbar)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_scroll.setWidget(self.grid_container)
        layout.addWidget(self.grid_scroll, 1)

        self.empty_label = QLabel("Tidak ada menu yang cocok dengan pencarian")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setHidden(True)
        self.empty_label.setStyleSheet("color: #94A3B8; font-size: 12px; padding-top: 30px;")
        self.grid_layout.addWidget(self.empty_label, 0, 0)

        self._apply_admin_visibility()

    def _apply_admin_visibility(self):
        is_admin = auth.is_admin if auth else False
        self.add_btn.setVisible(is_admin)
        self.delete_all_btn.setVisible(is_admin)

    def _on_search_changed(self, text):
        self._search_timer.start(300)

    def _apply_search(self):
        query = (self.search_input.text() or "").strip().lower()
        if query:
            self._filtered_items = [item for item in self._all_items if query in (item.nama or "").lower()]
        else:
            self._filtered_items = list(self._all_items)
        self._render_grid()

    def _render_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        if not self._filtered_items:
            self.empty_label.setVisible(True)
            return

        self.empty_label.setVisible(False)
        columns = 4 if self.width() > 1100 else 3
        for index, item in enumerate(self._filtered_items):
            card = MenuCard(item)
            card.set_admin_mode(auth.is_admin if auth else False)
            card.clicked.connect(self._on_card_clicked)
            card.edit_clicked.connect(self._on_edit_clicked)
            card.delete_clicked.connect(self._on_delete_clicked)
            row = index // columns
            col = index % columns
            self.grid_layout.addWidget(card, row, col)

    def _on_card_clicked(self, payload):
        self.item_selected.emit(payload)

    def _on_edit_clicked(self, menu_id: int):
        from ui.menu.menu_form_dialog import MenuFormDialog
        item = self._get_item_by_id(menu_id)
        if not item:
            return
        dialog = MenuFormDialog(item, self)
        dialog.saved.connect(self.refresh)
        dialog.exec_()

    def _on_delete_clicked(self, menu_id: int):
        item = self._get_item_by_id(menu_id)
        if not item:
            return
        confirm = QMessageBox.question(self, "Hapus Menu", f"Apakah Anda yakin ingin menghapus '{item.nama}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            with db.get_session() as session:
                target = session.query(MenuItem).filter_by(id=item.id).first()
                if target:
                    target.aktif = False
            self.refresh()

    def _delete_all(self):
        if not self._all_items:
            return
        confirm = QMessageBox.question(
            self,
            "Hapus Semua Menu",
            f"Apakah Anda yakin ingin menonaktifkan semua {len(self._all_items)} menu?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            with db.get_session() as session:
                session.query(MenuItem).filter(MenuItem.aktif.is_(True)).update({MenuItem.aktif: False})
            self.refresh()

    def _add_new_menu(self):
        from ui.menu.menu_form_dialog import MenuFormDialog
        dialog = MenuFormDialog(None, self)
        dialog.saved.connect(self.refresh)
        dialog.exec_()

    def _get_item_by_id(self, menu_id):
        for item in self._all_items:
            if item.id == menu_id:
                return item
        return None

    def refresh(self):
        with db.get_session() as session:
            self._all_items = session.query(MenuItem).filter(MenuItem.aktif.is_(True)).order_by(MenuItem.urutan.asc(), MenuItem.id.asc()).all()
        self._apply_search()
        self._apply_admin_visibility()

    def on_theme_changed(self, theme: str):
        """Dipanggil saat tema aplikasi berubah."""
        self._render_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._filtered_items:
            self._render_grid()
