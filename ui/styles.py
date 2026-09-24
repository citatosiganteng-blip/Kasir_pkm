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
    background-color: #F8FAFC;
    color: #1E293B;
    font-size: 13px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background: #F1F5F9;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #F1F5F9;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== LABELS ===== */
QLabel {
    background: transparent;
    color: #1E293B;
}
QLabel#label_muted {
    color: #64748B;
}
QLabel#label_secondary {
    color: #475569;
}

/* ===== LINE EDIT (INPUT) ===== */
QLineEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1E293B;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border-color: #2563EB;
    background-color: #FFFFFF;
}
QLineEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}
QLineEdit::placeholder {
    color: #94A3B8;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1E293B;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #2563EB;
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
    border-top: 5px solid #64748B;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    selection-background-color: #EFF6FF;
    selection-color: #2563EB;
    color: #1E293B;
    outline: none;
    padding: 4px;
}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1E293B;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2563EB;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #F1F5F9;
    border: none;
    width: 20px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #E2E8F0;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #E2E8F0;
}

/* ===== PUSH BUTTON ===== */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1D4ED8;
}
QPushButton:pressed {
    background-color: #1E40AF;
}
QPushButton:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
}

QPushButton#btn_secondary {
    background-color: #FFFFFF;
    color: #475569;
    border: 1.5px solid #E2E8F0;
}
QPushButton#btn_secondary:hover {
    background-color: #F8FAFC;
    color: #1E293B;
    border-color: #CBD5E1;
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
    color: #64748B;
    border: none;
    padding: 6px 12px;
}
QPushButton#btn_ghost:hover {
    color: #1E293B;
    background-color: #F1F5F9;
}

QPushButton#btn_primary {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #1D4ED8;
}

/* ===== TABLE WIDGET ===== */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    gridline-color: #F1F5F9;
    color: #1E293B;
    selection-background-color: #EFF6FF;
    selection-color: #1E293B;
    alternate-background-color: #F8FAFC;
}
QTableWidget::item {
    padding: 10px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E293B;
}
QTableWidget::item:hover {
    background-color: #F8FAFC;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #64748B;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
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
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: -1px;
}
QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    padding: 10px 20px;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 3px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #2563EB;
    color: #FFFFFF;
    border-color: #2563EB;
}
QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
    color: #1E293B;
}

/* ===== FRAME / CARD ===== */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

/* ===== CHECK BOX ===== */
QCheckBox {
    spacing: 8px;
    color: #1E293B;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #CBD5E1;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #2563EB;
    border-color: #2563EB;
}

/* ===== MESSAGE BOX ===== */
QMessageBox {
    background-color: #FFFFFF;
}
QMessageBox QLabel {
    color: #1E293B;
}

/* ===== DIALOG ===== */
QDialog {
    background-color: #FFFFFF;
}

/* ===== STATUS BAR ===== */
QStatusBar {
    background-color: #FFFFFF;
    color: #64748B;
    font-size: 12px;
    border-top: 1px solid #E2E8F0;
}

/* ===== SPLITTER ===== */
QSplitter::handle {
    background: #E2E8F0;
    width: 1px;
}

/* ===== DATE EDIT ===== */
QDateEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px 12px;
    color: #1E293B;
    font-size: 13px;
}
QDateEdit:focus {
    border-color: #2563EB;
}

/* ===== MENU ===== */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    color: #1E293B;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #EFF6FF;
    color: #2563EB;
}

/* ===== MAIN WINDOW (Light) ===== */
QWidget#main_central_widget {
    background-color: #F8FAFC;
}

/* ===== SIDEBAR (Light) ===== */
QFrame#sidebar {
    background-color: #1E293B;
    border-right: none;
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
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
}
QPushButton#nav_btn_sidebar:hover {
    background-color: rgba(255,255,255,0.08);
    color: #FFFFFF;
}
QPushButton#nav_btn_sidebar_active {
    background-color: #2563EB;
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
    border-bottom: 1px solid #E2E8F0;
}
QLabel#topbar_title {
    color: #0F172A;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}
QLabel#topbar_clock {
    color: #64748B;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QPushButton#btn_theme_toggle {
    background-color: #F1F5F9;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 17px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#btn_theme_toggle:hover {
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #94A3B8;
}
QLabel#user_avatar_lbl {
    background-color: #DBEAFE;
    color: #1D4ED8;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 700;
}
QLabel#user_name_lbl {
    color: #0F172A;
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
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}
QFrame#card QLabel {
    color: #1E293B;
}

/* ===== POS KASIR COMPONENTS (LIGHT) ===== */
QFrame#product_card {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 14px;
}
QFrame#product_card:hover {
    border-color: #2563EB;
    background-color: #FAFAFA;
}
QLabel#product_card_name {
    color: #1E293B;
    font-weight: 600;
    font-size: 13px;
}
QLabel#product_card_price {
    color: #2563EB;
    font-weight: 700;
    font-size: 13px;
}
QLabel#product_card_stock {
    background-color: #F1F5F9;
    color: #64748B;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#right_checkout_panel {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 16px;
}
QFrame#cart_item_row {
    background-color: #FFFFFF;
    border-bottom: 1px solid #F1F5F9;
    padding: 4px 0;
}
QLabel#cart_item_name {
    font-size: 13px;
    font-weight: 700;
    color: #1E293B;
}
QLabel#cart_item_subtotal {
    font-size: 13px;
    font-weight: 700;
    color: #1E293B;
}
QPushButton#cart_stepper {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 13px;
    font-size: 14px;
    font-weight: bold;
    padding: 0;
}
QPushButton#cart_stepper:hover {
    background-color: #E2E8F0;
    color: #1E293B;
}
QPushButton#category_pill {
    background-color: #FFFFFF;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#category_pill:hover {
    background-color: #F8FAFC;
    color: #1E293B;
    border-color: #CBD5E1;
}
QPushButton#category_pill_active {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #2563EB;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#payment_tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#payment_tab:hover {
    background-color: #E2E8F0;
    color: #1E293B;
}
QPushButton#payment_tab_active {
    background-color: #EFF6FF;
    color: #2563EB;
    border: 1.5px solid #2563EB;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#nominal_btn {
    background-color: #F8FAFC;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#nominal_btn:hover {
    background-color: #F1F5F9;
    color: #1E293B;
    border-color: #CBD5E1;
}
QPushButton#nominal_btn_active {
    background-color: #EFF6FF;
    color: #2563EB;
    border: 1.5px solid #2563EB;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PERIOD FILTER TABS (Light) ===== */
QPushButton#period_tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#period_tab:hover {
    background-color: #E2E8F0;
    color: #1E293B;
}
QPushButton#period_tab_active {
    background-color: #2563EB;
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
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    min-width: 32px;
}
QPushButton#page_btn:hover {
    background-color: #F1F5F9;
    color: #1E293B;
}
QPushButton#page_btn_active {
    background-color: #2563EB;
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
    background-color: #0F1117;
    color: #F1F5F9;
    font-size: 13px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    background: #1A1D27;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3D4466;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3B82F6;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #1A1D27;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #3D4466;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #3B82F6;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== LABELS ===== */
QLabel {
    background: transparent;
    color: #F1F5F9;
}
QLabel#label_muted {
    color: #94A3B8;
}
QLabel#label_secondary {
    color: #CBD5E1;
}

/* ===== LINE EDIT (INPUT) ===== */
QLineEdit {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border-color: #3B82F6;
    background-color: #21263A;
}
QLineEdit:disabled {
    background-color: #141721;
    color: #64748B;
    border-color: #2D3250;
}
QLineEdit::placeholder {
    color: #64748B;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border-color: #3B82F6;
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
    border-top: 5px solid #94A3B8;
}
QComboBox QAbstractItemView {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    color: #F1F5F9;
    outline: none;
    padding: 4px;
}

/* ===== SPIN BOX ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3B82F6;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #21263A;
    border: none;
    width: 20px;
    border-radius: 4px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background: #2D3250;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #2D3250;
}

/* ===== PUSH BUTTON ===== */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3B82F6;
}
QPushButton:pressed {
    background-color: #1D4ED8;
}
QPushButton:disabled {
    background-color: #21263A;
    color: #64748B;
}

QPushButton#btn_secondary {
    background-color: #1A1D27;
    color: #CBD5E1;
    border: 1.5px solid #2D3250;
}
QPushButton#btn_secondary:hover {
    background-color: #21263A;
    color: #FFFFFF;
    border-color: #3B82F6;
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
    color: #94A3B8;
    border: none;
    padding: 6px 12px;
}
QPushButton#btn_ghost:hover {
    color: #F1F5F9;
    background-color: #21263A;
}

QPushButton#btn_primary {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #3B82F6;
}

/* ===== TABLE WIDGET ===== */
QTableWidget {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 10px;
    gridline-color: #21263A;
    color: #F1F5F9;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    alternate-background-color: #151821;
}
QTableWidget::item {
    padding: 10px 12px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
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
    margin-right: 3px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #3B82F6;
    color: #FFFFFF;
    border-color: #3B82F6;
}
QTabBar::tab:hover:!selected {
    background-color: #2D3250;
    color: #F1F5F9;
}

/* ===== FRAME / CARD ===== */
QFrame#card {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
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
    border: 1.5px solid #3D4466;
    background: #1A1D27;
}
QCheckBox::indicator:checked {
    background: #3B82F6;
    border-color: #3B82F6;
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
    background-color: #1A1D27;
    color: #94A3B8;
    font-size: 12px;
    border-top: 1px solid #2D3250;
}

/* ===== SPLITTER ===== */
QSplitter::handle {
    background: #2D3250;
    width: 1px;
}

/* ===== DATE EDIT ===== */
QDateEdit {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 8px;
    padding: 6px 12px;
    color: #F1F5F9;
    font-size: 13px;
}
QDateEdit:focus {
    border-color: #3B82F6;
}

/* ===== MENU ===== */
QMenu {
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    color: #F1F5F9;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #3B82F6;
    color: #FFFFFF;
}

/* ===== MAIN WINDOW (Dark) ===== */
QWidget#main_central_widget {
    background-color: #0F1117;
}

/* ===== SIDEBAR (Dark) ===== */
QFrame#sidebar {
    background-color: #111827;
    border-right: 1px solid #1F2937;
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
    background-color: #2563EB;
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
    background-color: #0F1117;
    border-bottom: 1px solid #1E2333;
}
QLabel#topbar_title {
    color: #F8FAFC;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}
QLabel#topbar_clock {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}
QPushButton#btn_theme_toggle {
    background-color: #1A1D27;
    color: #F1F5F9;
    border: 1px solid #2D3250;
    border-radius: 17px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#btn_theme_toggle:hover {
    background-color: #2D3250;
    color: #FFFFFF;
    border-color: #3B82F6;
}
QLabel#user_avatar_lbl {
    background-color: #2D3250;
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
    background-color: #1A1D27;
    border: 1px solid #2D3250;
    border-radius: 12px;
}
QFrame#card QLabel {
    color: #F1F5F9;
}

/* ===== POS KASIR COMPONENTS (DARK) ===== */
QFrame#product_card {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 14px;
}
QFrame#product_card:hover {
    border-color: #3B82F6;
    background-color: #21263A;
}
QLabel#product_card_name {
    color: #F1F5F9;
    font-weight: 600;
    font-size: 13px;
}
QLabel#product_card_price {
    color: #60A5FA;
    font-weight: 700;
    font-size: 13px;
}
QLabel#product_card_stock {
    background-color: #21263A;
    color: #94A3B8;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#right_checkout_panel {
    background-color: #1A1D27;
    border: 1.5px solid #2D3250;
    border-radius: 16px;
}
QFrame#cart_item_row {
    background-color: #1A1D27;
    border-bottom: 1px solid #21263A;
    padding: 4px 0;
}
QLabel#cart_item_name {
    font-size: 13px;
    font-weight: 700;
    color: #F1F5F9;
}
QLabel#cart_item_subtotal {
    font-size: 13px;
    font-weight: 700;
    color: #60A5FA;
}
QPushButton#cart_stepper {
    background-color: #21263A;
    color: #CBD5E1;
    border: 1px solid #2D3250;
    border-radius: 13px;
    font-size: 14px;
    font-weight: bold;
    padding: 0;
}
QPushButton#cart_stepper:hover {
    background-color: #2D3250;
    color: #F1F5F9;
}
QPushButton#category_pill {
    background-color: #1A1D27;
    color: #94A3B8;
    border: 1px solid #2D3250;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#category_pill:hover {
    background-color: #21263A;
    color: #F1F5F9;
    border-color: #3B4261;
}
QPushButton#category_pill_active {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: 1px solid #3B82F6;
    border-radius: 18px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#payment_tab {
    background-color: #21263A;
    color: #94A3B8;
    border: 1px solid #2D3250;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#payment_tab:hover {
    background-color: #2D3250;
    color: #F1F5F9;
}
QPushButton#payment_tab_active {
    background-color: rgba(59, 130, 246, 0.2);
    color: #60A5FA;
    border: 1.5px solid #3B82F6;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#nominal_btn {
    background-color: #21263A;
    color: #94A3B8;
    border: 1px solid #2D3250;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#nominal_btn:hover {
    background-color: #2D3250;
    color: #F1F5F9;
    border-color: #3B4261;
}
QPushButton#nominal_btn_active {
    background-color: rgba(59, 130, 246, 0.2);
    color: #60A5FA;
    border: 1.5px solid #3B82F6;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PERIOD FILTER TABS (Dark) ===== */
QPushButton#period_tab {
    background-color: #1A1D27;
    color: #94A3B8;
    border: 1px solid #2D3250;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#period_tab:hover {
    background-color: #21263A;
    color: #F1F5F9;
}
QPushButton#period_tab_active {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
}

/* ===== PAGINATION (Dark) ===== */
QPushButton#page_btn {
    background-color: #1A1D27;
    color: #94A3B8;
    border: 1px solid #2D3250;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    min-width: 32px;
}
QPushButton#page_btn:hover {
    background-color: #21263A;
    color: #FFFFFF;
}
QPushButton#page_btn_active {
    background-color: #2563EB;
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
