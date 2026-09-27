"""
KasirKu UI Styles
Theme definitions for Light Mode (Clean Light) and Dark Mode (Modern Dark)
Reference: Left sidebar layout with professional dark UI
"""

# =============================================================================
# LIGHT THEME (Default)
# =============================================================================
LIGHT_STYLESHEET = """
/* ===== GLOBAL ===== */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    outline: none;
}

QWidget {
    background-color: #F9FAFB;
    color: #112D4E;
    font-size: 13px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background: #F9FAFB;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #E5E7EB;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #7C8CA6;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #F9FAFB;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #E5E7EB;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #7C8CA6;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== LABELS ===== */
QLabel {
    background: transparent;
    color: #112D4E;
}
QLabel#label_muted {
    color: #5B6B84;
}
QLabel#label_secondary {
    color: #3E4C63;
}

/* ===== LINE EDIT (INPUT) ===== */
QLineEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 8px;
    padding: 8px 12px;
    color: #112D4E;
    font-size: 13px;
    selection-background-color: #3F72AF;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border-color: #3F72AF;
    background-color: #FFFFFF;
}
QLineEdit:disabled {
    background-color: #F9FAFB;
    color: #7C8CA6;
    border-color: #E5E7EB;
}
QLineEdit::placeholder {
    color: #7C8CA6;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 8px;
    padding: 8px 12px;
    color: #112D4E;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #3F72AF;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #5B6B84;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    selection-background-color: #DBE2EF;
    selection-color: #3F72AF;
    color: #112D4E;
    outline: none;
    padding: 4px;
}
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0;
    color: #112D4E;
}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 8px;
    padding: 8px 12px;
    color: #112D4E;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3F72AF;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #F9FAFB;
    border: none;
    width: 20px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #E5E7EB;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #E5E7EB;
}

/* ===== PUSH BUTTON ===== */
QPushButton {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2F5A8C;
}
QPushButton:pressed {
    background-color: #1E40AF;
}
QPushButton:disabled {
    background-color: #E5E7EB;
    color: #7C8CA6;
}

QPushButton#btn_secondary {
    background-color: #FFFFFF;
    color: #3E4C63;
    border: 1.5px solid #E5E7EB;
}
QPushButton#btn_secondary:hover {
    background-color: #F9FAFB;
    color: #112D4E;
    border-color: #E5E7EB;
}

QPushButton#btn_success {
    background-color: #10B981;
    color: #FFFFFF;
}
QPushButton#btn_success:hover {
    background-color: #059669;
}
QPushButton#btn_success:pressed {
    background-color: #047857;
}

QPushButton#btn_danger {
    background-color: #EF4444;
    color: #FFFFFF;
}
QPushButton#btn_danger:hover {
    background-color: #DC2626;
}
QPushButton#btn_danger:pressed {
    background-color: #B91C1C;
}

QPushButton#btn_ghost {
    background-color: transparent;
    color: #5B6B84;
    border: none;
    padding: 6px 12px;
}
QPushButton#btn_ghost:hover {
    color: #112D4E;
    background-color: #F9FAFB;
}

QPushButton#btn_primary {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #2F5A8C;
}

/* ===== TABLE WIDGET ===== */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    gridline-color: #F9FAFB;
    color: #112D4E;
    selection-background-color: #DBE2EF;
    selection-color: #112D4E;
    alternate-background-color: #F9FAFB;
}
QTableWidget::item {
    padding: 10px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #DBE2EF;
    color: #112D4E;
}
QTableWidget::item:hover {
    background-color: #F9FAFB;
}
QHeaderView::section {
    background-color: #F9FAFB;
    color: #5B6B84;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #E5E7EB;
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

/* ===== TAB WIDGET ===== */
QTabWidget::pane {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    margin-top: -1px;
}
QTabBar::tab {
    background-color: #F9FAFB;
    color: #5B6B84;
    padding: 10px 20px;
    border: 1px solid #E5E7EB;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 3px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #3F72AF;
    color: #FFFFFF;
    border-color: #3F72AF;
}
QTabBar::tab:hover:!selected {
    background-color: #E5E7EB;
    color: #112D4E;
}

/* ===== FRAME / CARD ===== */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}

/* ===== CHECK BOX ===== */
QCheckBox {
    spacing: 8px;
    color: #112D4E;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #E5E7EB;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #3F72AF;
    border-color: #3F72AF;
}

/* ===== MESSAGE BOX ===== */
QMessageBox {
    background-color: #FFFFFF;
}
QMessageBox QLabel {
    color: #112D4E;
}

/* ===== DIALOG ===== */
QDialog {
    background-color: #FFFFFF;
}

/* ===== STATUS BAR ===== */
QStatusBar {
    background-color: #FFFFFF;
    color: #5B6B84;
    font-size: 12px;
    border-top: 1px solid #E5E7EB;
}

/* ===== SPLITTER ===== */
QSplitter::handle {
    background: #E5E7EB;
    width: 1px;
}

/* ===== DATE EDIT ===== */
QDateEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 8px;
    padding: 6px 12px;
    color: #112D4E;
    font-size: 13px;
}
QDateEdit:focus {
    border-color: #3F72AF;
}
QDateEdit QCalendarWidget {
    background-color: #FFFFFF;
    color: #112D4E;
}
QDateEdit QCalendarWidget QAbstractItemView {
    background-color: #FFFFFF;
    color: #112D4E;
    selection-background-color: #3F72AF;
    selection-color: #FFFFFF;
}

/* ===== MENU ===== */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    color: #112D4E;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #DBE2EF;
    color: #3F72AF;
}

/* ===== MAIN WINDOW (Light) ===== */
QWidget#main_central_widget {
    background-color: #F9FAFB;
}

/* ===== SIDEBAR (Light) ===== */
QFrame#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}
QFrame#sidebar_divider {
    background-color: #E5E7EB;
    margin: 8px 0px;
}
QLabel#sidebar_brand_lbl {
    color: #112D4E;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QLabel#sidebar_brand_icon {
    background: transparent;
}

QPushButton#nav_btn_sidebar {
    background-color: transparent;
    color: #5B6B84;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
QPushButton#nav_btn_sidebar:hover {
    background-color: #F0F3F7;
    color: #112D4E;
}
QPushButton#nav_btn_sidebar_active {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 700;
    text-align: left;
}

QPushButton#nav_btn_logout {
    background-color: transparent;
    color: #EF4444;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}
QPushButton#nav_btn_logout:hover {
    background-color: rgba(239,68,68,0.12);
    color: #F87171;
}

/* ===== TOP CONTENT BAR (Light) ===== */
QFrame#content_top_bar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
}
QLabel#topbar_title {
    color: #112D4E;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}
QLabel#topbar_clock {
    color: #5B6B84;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QPushButton#btn_theme_toggle {
    background-color: #F9FAFB;
    color: #112D4E;
    border: 1px solid #E5E7EB;
    border-radius: 17px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#btn_theme_toggle:hover {
    background-color: #E5E7EB;
    color: #112D4E;
    border-color: #7C8CA6;
}
QLabel#user_avatar_lbl {
    background-color: #DBE2EF;
    color: #2F5A8C;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 700;
}
QLabel#user_name_lbl {
    color: #112D4E;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QLabel#user_status_badge {
    color: #059669;
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}

/* ===== CARDS & STATS (Light) ===== */
QFrame#card, QFrame#stat_card, QFrame#stat_card_tx, QFrame#laporan_stat_card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#card QLabel {
    color: #112D4E;
}

/* ===== POS KASIR COMPONENTS (LIGHT) ===== */
QFrame#product_card {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 14px;
}
QFrame#product_card:hover {
    border-color: #3F72AF;
    background-color: #F9FAFB;
}
QLabel#product_card_name {
    color: #112D4E;
    font-weight: 600;
    font-size: 13px;
}
QLabel#product_card_price {
    color: #3F72AF;
    font-weight: 700;
    font-size: 13px;
}
QLabel#product_card_stock {
    background-color: #F9FAFB;
    color: #5B6B84;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#right_checkout_panel {
    background-color: #FFFFFF;
    border: 1.5px solid #E5E7EB;
    border-radius: 16px;
}
QFrame#cart_item_row {
    background-color: #FFFFFF;
    border-bottom: 1px solid #F9FAFB;
    padding: 4px 0;
}
QLabel#cart_item_name {
    font-size: 13px;
    font-weight: 700;
    color: #112D4E;
}
QLabel#cart_item_subtotal {
    font-size: 13px;
    font-weight: 700;
    color: #112D4E;
}
QPushButton#cart_stepper {
    background-color: #F9FAFB;
    color: #3E4C63;
    border: 1px solid #E5E7EB;
    border-radius: 13px;
    font-size: 14px;
    font-weight: bold;
    padding: 0;
}
QPushButton#cart_stepper:hover {
    background-color: #E5E7EB;
    color: #112D4E;
}
QPushButton#category_pill {
    background-color: #FFFFFF;
    color: #5B6B84;
    border: 1px solid #E5E7EB;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#category_pill:hover {
    background-color: #F9FAFB;
    color: #112D4E;
    border-color: #E5E7EB;
}
QPushButton#category_pill_active {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: 1px solid #3F72AF;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#payment_tab {
    background-color: #F9FAFB;
    color: #5B6B84;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#payment_tab:hover {
    background-color: #E5E7EB;
    color: #112D4E;
}
QPushButton#payment_tab_active {
    background-color: #DBE2EF;
    color: #3F72AF;
    border: 1.5px solid #3F72AF;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#nominal_btn {
    background-color: #F9FAFB;
    color: #3E4C63;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#nominal_btn:hover {
    background-color: #F9FAFB;
    color: #112D4E;
    border-color: #E5E7EB;
}
QPushButton#nominal_btn_active {
    background-color: #DBE2EF;
    color: #3F72AF;
    border: 1.5px solid #3F72AF;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PERIOD FILTER TABS (Light) ===== */
QPushButton#period_tab {
    background-color: #F9FAFB;
    color: #5B6B84;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#period_tab:hover {
    background-color: #E5E7EB;
    color: #112D4E;
}
QPushButton#period_tab_active {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PAGINATION (Light) ===== */
QPushButton#page_btn {
    background-color: #FFFFFF;
    color: #3E4C63;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    min-width: 32px;
}
QPushButton#page_btn:hover {
    background-color: #F9FAFB;
    color: #112D4E;
}
QPushButton#page_btn_active {
    background-color: #3F72AF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 700;
    min-width: 32px;
}
"""


# =============================================================================
# DARK THEME (Modern Dark POS)
# =============================================================================
DARK_STYLESHEET = """
/* ===== GLOBAL ===== */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    outline: none;
}

QWidget {
    background-color: #0B2036;
    color: #F9FAFB;
    font-size: 13px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background: #112D4E;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #35507A;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #2572AF;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #112D4E;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #35507A;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #2572AF;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== LABELS ===== */
QLabel {
    background: transparent;
    color: #F9FAFB;
}
QLabel#label_muted {
    color: #B9C4D6;
}
QLabel#label_secondary {
    color: #274568;
}

/* ===== LINE EDIT (INPUT) ===== */
QLineEdit {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F9FAFB;
    font-size: 13px;
    selection-background-color: #2572AF;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border-color: #2572AF;
    background-color: #17324F;
}
QLineEdit:disabled {
    background-color: #141721;
    color: #8CA0BC;
    border-color: #274568;
}
QLineEdit::placeholder {
    color: #8CA0BC;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F9FAFB;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #2572AF;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #B9C4D6;
}
QComboBox QAbstractItemView {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 8px;
    selection-background-color: #2572AF;
    selection-color: #FFFFFF;
    color: #F9FAFB;
    outline: none;
    padding: 4px;
}
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0;
    color: #F9FAFB;
}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F9FAFB;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2572AF;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #17324F;
    border: none;
    width: 20px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #274568;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #274568;
}

/* ===== PUSH BUTTON ===== */
QPushButton {
    background-color: #2572AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2572AF;
}
QPushButton:pressed {
    background-color: #194B7D;
}
QPushButton:disabled {
    background-color: #17324F;
    color: #8CA0BC;
}

QPushButton#btn_secondary {
    background-color: #112D4E;
    color: #B9C4D6;
    border: 1.5px solid #274568;
}
QPushButton#btn_secondary:hover {
    background-color: #17324F;
    color: #FFFFFF;
    border-color: #2572AF;
}

QPushButton#btn_success {
    background-color: #10B981;
    color: #FFFFFF;
}
QPushButton#btn_success:hover {
    background-color: #34D399;
}
QPushButton#btn_success:pressed {
    background-color: #059669;
}

QPushButton#btn_danger {
    background-color: #EF4444;
    color: #FFFFFF;
}
QPushButton#btn_danger:hover {
    background-color: #F87171;
}
QPushButton#btn_danger:pressed {
    background-color: #DC2626;
}

QPushButton#btn_ghost {
    background-color: transparent;
    color: #B9C4D6;
    border: none;
    padding: 6px 12px;
}
QPushButton#btn_ghost:hover {
    color: #F9FAFB;
    background-color: #17324F;
}

QPushButton#btn_primary {
    background-color: #2572AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #2572AF;
}

/* ===== TABLE WIDGET ===== */
QTableWidget {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 10px;
    gridline-color: #17324F;
    color: #F9FAFB;
    selection-background-color: #2572AF;
    selection-color: #FFFFFF;
    alternate-background-color: #151821;
}
QTableWidget::item {
    padding: 10px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #2572AF;
    color: #FFFFFF;
}
QTableWidget::item:hover {
    background-color: #17324F;
}
QHeaderView::section {
    background-color: #17324F;
    color: #B9C4D6;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #274568;
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

/* ===== TAB WIDGET ===== */
QTabWidget::pane {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 8px;
    margin-top: -1px;
}
QTabBar::tab {
    background-color: #17324F;
    color: #B9C4D6;
    padding: 10px 20px;
    border: 1px solid #274568;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 3px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #2572AF;
    color: #FFFFFF;
    border-color: #2572AF;
}
QTabBar::tab:hover:!selected {
    background-color: #274568;
    color: #F9FAFB;
}

/* ===== FRAME / CARD ===== */
QFrame#card {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 12px;
}

/* ===== CHECK BOX ===== */
QCheckBox {
    spacing: 8px;
    color: #F9FAFB;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #35507A;
    background: #112D4E;
}
QCheckBox::indicator:checked {
    background: #2572AF;
    border-color: #2572AF;
}

/* ===== MESSAGE BOX ===== */
QMessageBox {
    background-color: #112D4E;
}
QMessageBox QLabel {
    color: #F9FAFB;
}

/* ===== DIALOG ===== */
QDialog {
    background-color: #112D4E;
}

/* ===== STATUS BAR ===== */
QStatusBar {
    background-color: #112D4E;
    color: #B9C4D6;
    font-size: 12px;
    border-top: 1px solid #274568;
}

/* ===== SPLITTER ===== */
QSplitter::handle {
    background: #274568;
    width: 1px;
}

/* ===== DATE EDIT ===== */
QDateEdit {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 8px;
    padding: 6px 12px;
    color: #F9FAFB;
    font-size: 13px;
}
QDateEdit:focus {
    border-color: #2572AF;
}
QDateEdit QCalendarWidget {
    background-color: #112D4E;
    color: #F9FAFB;
}
QDateEdit QCalendarWidget QAbstractItemView {
    background-color: #112D4E;
    color: #F9FAFB;
    selection-background-color: #2572AF;
    selection-color: #FFFFFF;
}

/* ===== MENU ===== */
QMenu {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    color: #F9FAFB;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #2572AF;
    color: #FFFFFF;
}

/* ===== MAIN WINDOW (Dark) ===== */
QWidget#main_central_widget {
    background-color: #0B2036;
}

/* ===== SIDEBAR (Dark) ===== */
QFrame#sidebar {
    background-color: #112D4E;
    border-right: 1px solid #274568;
}
QFrame#sidebar_divider {
    background-color: rgba(255,255,255,0.1);
    margin: 8px 0px;
}
QLabel#sidebar_brand_lbl {
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QLabel#sidebar_brand_icon {
    background: transparent;
}

QPushButton#nav_btn_sidebar {
    background-color: transparent;
    color: #9CA3AF;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
QPushButton#nav_btn_sidebar:hover {
    background-color: rgba(255,255,255,0.06);
    color: #FFFFFF;
}
QPushButton#nav_btn_sidebar_active {
    background-color: #2572AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 700;
    text-align: left;
}

QPushButton#nav_btn_logout {
    background-color: transparent;
    color: #EF4444;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}
QPushButton#nav_btn_logout:hover {
    background-color: rgba(239,68,68,0.12);
    color: #F87171;
}

/* ===== TOP CONTENT BAR (Dark) ===== */
QFrame#content_top_bar {
    background-color: #0B2036;
    border-bottom: 1px solid #1E2333;
}
QLabel#topbar_title {
    color: #F8FAFC;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}
QLabel#topbar_clock {
    color: #B9C4D6;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QPushButton#btn_theme_toggle {
    background-color: #112D4E;
    color: #F9FAFB;
    border: 1px solid #274568;
    border-radius: 17px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#btn_theme_toggle:hover {
    background-color: #274568;
    color: #FFFFFF;
    border-color: #2572AF;
}
QLabel#user_avatar_lbl {
    background-color: #274568;
    color: #93C5FD;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 700;
}
QLabel#user_name_lbl {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QLabel#user_status_badge {
    color: #10B981;
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}

/* ===== CARDS & STATS (Dark) ===== */
QFrame#card, QFrame#stat_card, QFrame#stat_card_tx, QFrame#laporan_stat_card {
    background-color: #112D4E;
    border: 1px solid #274568;
    border-radius: 12px;
}
QFrame#card QLabel {
    color: #F9FAFB;
}

/* ===== POS KASIR COMPONENTS (DARK) ===== */
QFrame#product_card {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 14px;
}
QFrame#product_card:hover {
    border-color: #2572AF;
    background-color: #17324F;
}
QLabel#product_card_name {
    color: #F9FAFB;
    font-weight: 600;
    font-size: 13px;
}
QLabel#product_card_price {
    color: #A9B5EF;
    font-weight: 700;
    font-size: 13px;
}
QLabel#product_card_stock {
    background-color: #17324F;
    color: #B9C4D6;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#right_checkout_panel {
    background-color: #112D4E;
    border: 1.5px solid #274568;
    border-radius: 16px;
}
QFrame#cart_item_row {
    background-color: #112D4E;
    border-bottom: 1px solid #17324F;
    padding: 4px 0;
}
QLabel#cart_item_name {
    font-size: 13px;
    font-weight: 700;
    color: #F9FAFB;
}
QLabel#cart_item_subtotal {
    font-size: 13px;
    font-weight: 700;
    color: #A9B5EF;
}
QPushButton#cart_stepper {
    background-color: #17324F;
    color: #274568;
    border: 1px solid #274568;
    border-radius: 13px;
    font-size: 14px;
    font-weight: bold;
    padding: 0;
}
QPushButton#cart_stepper:hover {
    background-color: #274568;
    color: #F9FAFB;
}
QPushButton#category_pill {
    background-color: #112D4E;
    color: #B9C4D6;
    border: 1px solid #274568;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#category_pill:hover {
    background-color: #17324F;
    color: #F9FAFB;
    border-color: #2E4868;
}
QPushButton#category_pill_active {
    background-color: #2572AF;
    color: #FFFFFF;
    border: 1px solid #2572AF;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#payment_tab {
    background-color: #17324F;
    color: #B9C4D6;
    border: 1px solid #274568;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#payment_tab:hover {
    background-color: #274568;
    color: #F9FAFB;
}
QPushButton#payment_tab_active {
    background-color: rgba(59, 130, 246, 0.2);
    color: #A9B5EF;
    border: 1.5px solid #2572AF;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#nominal_btn {
    background-color: #17324F;
    color: #B9C4D6;
    border: 1px solid #274568;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#nominal_btn:hover {
    background-color: #274568;
    color: #F9FAFB;
    border-color: #2E4868;
}
QPushButton#nominal_btn_active {
    background-color: rgba(59, 130, 246, 0.2);
    color: #A9B5EF;
    border: 1.5px solid #2572AF;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PERIOD FILTER TABS (Dark) ===== */
QPushButton#period_tab {
    background-color: #112D4E;
    color: #B9C4D6;
    border: 1px solid #274568;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#period_tab:hover {
    background-color: #17324F;
    color: #F9FAFB;
}
QPushButton#period_tab_active {
    background-color: #2572AF;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PAGINATION (Dark) ===== */
QPushButton#page_btn {
    background-color: #112D4E;
    color: #B9C4D6;
    border: 1px solid #274568;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    min-width: 32px;
}
QPushButton#page_btn:hover {
    background-color: #17324F;
    color: #FFFFFF;
}
QPushButton#page_btn_active {
    background-color: #2572AF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 700;
    min-width: 32px;
}
"""


# =============================================================================
# SIDEBAR STYLES embedded in themes above
# For backward compat only - not separately applied
# =============================================================================
BOTTOM_NAV_STYLE_LIGHT = ""
BOTTOM_NAV_STYLE_DARK = ""


def get_theme_stylesheet(mode: str = "light") -> str:
    """Mengambil stylesheet lengkap berdasarkan mode ('light' atau 'dark')"""
    if (mode or "").lower() == "dark":
        return DARK_STYLESHEET
    return LIGHT_STYLESHEET


# Defaults for backward compatibility
MAIN_STYLESHEET = LIGHT_STYLESHEET
BOTTOM_NAV_STYLE = BOTTOM_NAV_STYLE_LIGHT
SIDEBAR_STYLE = BOTTOM_NAV_STYLE_LIGHT

# Badges
BADGE_LOW_STOCK = """
background-color: #FEE2E2;
color: #DC2626;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""

BADGE_SUCCESS = """
background-color: #D1FAE5;
color: #059669;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""

BADGE_WARNING = """
background-color: #FEF3C7;
color: #D97706;
border-radius: 4px;
padding: 2px 8px;
font-size: 11px;
font-weight: 600;
"""
