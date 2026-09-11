"""
KasirKu UI Styles
Modern dark theme stylesheet for PyQt5
"""

MAIN_STYLESHEET = """
/* ===== GLOBAL ===== */
* {
    font-family: 'Segoe UI', Arial, sans-serif;
    outline: none;
}

QWidget {
    background-color: #0F1117;
    color: #F1F5F9;
    font-size: 13px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background: #1A1D27;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3D4466;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #6C63FF;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #1A1D27;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #3D4466;
    border-radius: 4px;
}

/* ===== LABELS ===== */
QLabel {
    background: transparent;
    color: #F1F5F9;
}
QLabel#label_muted {
    color: #64748B;
}
QLabel#label_secondary {
    color: #94A3B8;
}

/* ===== LINE EDIT (INPUT) ===== */
QLineEdit {
    background-color: #21263A;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
    selection-background-color: #6C63FF;
}
QLineEdit:focus {
    border-color: #6C63FF;
    background-color: #252B40;
}
QLineEdit:disabled {
    background-color: #1A1D27;
    color: #64748B;
    border-color: #2D3250;
}
QLineEdit::placeholder {
    color: #64748B;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: #21263A;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #6C63FF;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #94A3B8;
}
QComboBox QAbstractItemView {
    background-color: #21263A;
    border: 1px solid #2D3250;
    border-radius: 8px;
    selection-background-color: #6C63FF;
    outline: none;
}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #21263A;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #6C63FF;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #2D3250;
    border: none;
    width: 20px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #6C63FF;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #6C63FF;
}

/* ===== PUSH BUTTON ===== */
QPushButton {
    background-color: #6C63FF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
}
QPushButton:hover {
    background-color: #8B84FF;
}
QPushButton:pressed {
    background-color: #4A44CC;
}
QPushButton:disabled {
    background-color: #2D3250;
    color: #64748B;
}

QPushButton#btn_secondary {
    background-color: #21263A;
    color: #94A3B8;
    border: 1.5px solid #2D3250;
}
QPushButton#btn_secondary:hover {
    background-color: #2A2F45;
    color: #F1F5F9;
    border-color: #6C63FF;
}

QPushButton#btn_success {
    background-color: #10B981;
}
QPushButton#btn_success:hover {
    background-color: #34D399;
}
QPushButton#btn_success:pressed {
    background-color: #059669;
}

QPushButton#btn_danger {
    background-color: #EF4444;
}
QPushButton#btn_danger:hover {
    background-color: #F87171;
}
QPushButton#btn_danger:pressed {
    background-color: #DC2626;
}

QPushButton#btn_warning {
    background-color: #F59E0B;
    color: #0F1117;
}
QPushButton#btn_warning:hover {
    background-color: #FBBF24;
}

QPushButton#btn_ghost {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    padding: 6px 12px;
}
QPushButton#btn_ghost:hover {
    color: #F1F5F9;
    background-color: #21263A;
}

QPushButton#btn_icon {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    padding: 6px;
    border-radius: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}
QPushButton#btn_icon:hover {
    background-color: #21263A;
    color: #F1F5F9;
}

/* ===== TABLE WIDGET ===== */
QTableWidget {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 10px;
    gridline-color: #2D3250;
    color: #F1F5F9;
    selection-background-color: #2A2F45;
    alternate-background-color: #1E2235;
}
QTableWidget::item {
    padding: 10px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #2A3050;
    color: #F1F5F9;
}
QTableWidget::item:hover {
    background-color: #21263A;
}
QHeaderView::section {
    background-color: #21263A;
    color: #94A3B8;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #2D3250;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}
QHeaderView::section:first {
    border-top-left-radius: 10px;
}
QHeaderView::section:last {
    border-top-right-radius: 10px;
}

/* ===== DATE EDIT ===== */
QDateEdit {
    background-color: #21263A;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
}
QDateEdit:focus {
    border-color: #6C63FF;
}
QDateEdit::drop-down {
    border: none;
    width: 20px;
}
QCalendarWidget {
    background-color: #1A1D27;
    color: #F1F5F9;
}

/* ===== TEXT EDIT ===== */
QTextEdit {
    background-color: #21263A;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
}
QTextEdit:focus {
    border-color: #6C63FF;
}

/* ===== TAB WIDGET ===== */
QTabWidget::pane {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 8px;
    margin-top: -1px;
}
QTabBar::tab {
    background-color: #21263A;
    color: #94A3B8;
    padding: 10px 20px;
    border: 1px solid #2D3250;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #6C63FF;
    color: #FFFFFF;
    border-color: #6C63FF;
}
QTabBar::tab:hover:!selected {
    background-color: #2A2F45;
    color: #F1F5F9;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background-color: #21263A;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6C63FF, stop:1 #8B84FF);
    border-radius: 4px;
}

/* ===== FRAME / CARD ===== */
QFrame#card {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 12px;
}
QFrame#card_accent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1A1D27, stop:1 #21263A);
    border: 1px solid #3D4466;
    border-radius: 12px;
}

/* ===== CHECK BOX ===== */
QCheckBox {
    spacing: 8px;
    color: #F1F5F9;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #3D4466;
    background: #21263A;
}
QCheckBox::indicator:checked {
    background: #6C63FF;
    border-color: #6C63FF;
}

/* ===== MESSAGE BOX ===== */
QMessageBox {
    background-color: #1A1D27;
}
QMessageBox QLabel {
    color: #F1F5F9;
}

/* ===== DIALOG ===== */
QDialog {
    background-color: #1A1D27;
}

/* ===== STATUS BAR ===== */
QStatusBar {
    background-color: #0F1117;
    color: #64748B;
    font-size: 12px;
    border-top: 1px solid #2D3250;
}

/* ===== TOOL TIP ===== */
QToolTip {
    background-color: #21263A;
    color: #F1F5F9;
    border: 1px solid #3D4466;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ===== SPLITTER ===== */
QSplitter::handle {
    background: #2D3250;
    width: 1px;
}
QSplitter::handle:hover {
    background: #6C63FF;
}
"""


# Sidebar styles
SIDEBAR_STYLE = """
QWidget#sidebar {
    background-color: #1A1D27;
    border-right: 1px solid #2D3250;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#sidebar_btn:hover {
    background-color: #21263A;
    color: #F1F5F9;
}
QPushButton#sidebar_btn_active {
    background-color: #21263A;
    color: #6C63FF;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    border-left: 3px solid #6C63FF;
}
"""

# Card styles
CARD_STYLE = """
QFrame {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 12px;
}
"""

# Badge styles
BADGE_LOW_STOCK = """
background-color: #7F1D1D;
color: #FCA5A5;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""

BADGE_SUCCESS = """
background-color: #064E3B;
color: #6EE7B7;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""

BADGE_WARNING = """
background-color: #78350F;
color: #FCD34D;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""
