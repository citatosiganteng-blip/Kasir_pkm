"""
KasirKu - Icon Helpers
Ikon digambar langsung dengan QPainter (bukan karakter emoji), supaya
selalu tampil konsisten di semua sistem operasi. Emoji seperti "👁" atau
"🙈" kadang tidak punya glyph di font sistem tertentu (terutama Windows
dengan beberapa versi Qt, atau Linux tanpa font emoji terpasang) sehingga
tombol terlihat kosong walau fungsinya tetap berjalan.
"""

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor


def eye_icon(visible: bool, color: str = "#64748B", size: int = 22) -> QIcon:
    """Ikon mata untuk tombol lihat/sembunyikan password.

    visible=True  -> mata terbuka (password sedang terlihat)
    visible=False -> mata terbuka + coretan diagonal (password disembunyikan)
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    margin = size * 0.16
    w = size - margin * 2
    h = w * 0.58
    top = (size - h) / 2
    eye_rect = QRectF(margin, top, w, h)

    pen = QPen(QColor(color))
    pen.setWidthF(max(1.4, size * 0.08))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(eye_rect)

    pupil_r = h * 0.32
    painter.setBrush(QColor(color))
    painter.drawEllipse(eye_rect.center(), pupil_r, pupil_r)

    if not visible:
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(
            QPointF(margin * 0.4, size - margin * 0.4),
            QPointF(size - margin * 0.4, margin * 0.4),
        )

    painter.end()
    return QIcon(pixmap)
