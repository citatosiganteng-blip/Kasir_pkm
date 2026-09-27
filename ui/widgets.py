"""
KasirKu - Widget kustom yang dipakai ulang di banyak halaman.

ThemedComboBox
--------------
Di beberapa kombinasi Windows, popup dropdown QComboBox TIDAK otomatis
mewarisi stylesheet aplikasi (dia dirender sebagai window terpisah), jadi
walau QSS global sudah benar, popup-nya bisa tampil sebagai kotak HITAM
SOLID -- terutama kentara saat mode terang aktif (di mode gelap kebetulan
tidak terlalu kelihatan karena sama-sama gelap).

ThemedComboBox mengatasi ini dengan memaksa ulang style + palette persis
sebelum popup ditampilkan (override showPopup), membaca setting tema saat
itu juga -- jadi otomatis ikut tema tanpa perlu di-hook manual ke
on_theme_changed di tiap halaman.
"""

from PyQt5.QtWidgets import QComboBox
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from database.db import db


def apply_dialog_theme(dialog):
    """
    Pasang ulang stylesheet tema (terang/gelap) LANGSUNG ke instance dialog.

    Kenapa perlu: QDialog secara normal mewarisi stylesheet dari
    QApplication, tapi di beberapa kombinasi Windows, dialog (window
    top-level terpisah) TIDAK ikut ter-cascade sama sekali -- bukan cuma
    warna background, tapi semua rule termasuk yang berbasis objectName
    (#btn_primary, dll). Akibatnya dialog fallback ke rendering native
    Windows, yang warnanya ikut preferensi dark/light OS -- bukan
    preferensi tema di dalam aplikasi KasirKu sendiri. Panggil fungsi ini
    di akhir __init__/_setup_ui tiap QDialog supaya dialog itu selalu
    membawa salinan stylesheet-nya sendiri dan tidak bergantung pada
    cascade yang tidak bisa diandalkan tersebut.
    """
    from ui.styles import get_theme_stylesheet
    theme = db.get_setting("app_theme", "light")
    dialog.setStyleSheet(get_theme_stylesheet(theme))


class ThemedComboBox(QComboBox):
    """QComboBox yang popup dropdown-nya selalu ikut tema terang/gelap aplikasi."""

    def showPopup(self):
        is_dark = db.get_setting("app_theme", "light") == "dark"
        if is_dark:
            bg, border, sel_bg, sel_fg, text = "#112D4E", "#274568", "#17324F", "#F9FAFB", "#F9FAFB"
        else:
            bg, border, sel_bg, sel_fg, text = "#FFFFFF", "#E5E7EB", "#DBE2EF", "#3F72AF", "#112D4E"

        view = self.view()
        popup = view.window()

        # Palette eksplisit dulu (bukan cuma stylesheet) -- di beberapa versi
        # Windows, popup window butuh palette solid supaya tidak sempat
        # kelihatan hitam sebelum stylesheet ke-apply.
        popup.setAttribute(Qt.WA_TranslucentBackground, False)
        pal = popup.palette()
        pal.setColor(QPalette.Base, QColor(bg))
        pal.setColor(QPalette.Window, QColor(bg))
        popup.setPalette(pal)
        popup.setAutoFillBackground(True)

        view.setStyleSheet(f"""
            QAbstractItemView {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                outline: none;
                padding: 4px;
                selection-background-color: {sel_bg};
                selection-color: {sel_fg};
            }}
        """)

        super().showPopup()
