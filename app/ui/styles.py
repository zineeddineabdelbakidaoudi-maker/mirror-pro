"""QSS stylesheet generator based on current theme."""
from app.ui.theme import Theme


def get_stylesheet() -> str:
    """Generate the full application stylesheet."""
    t = Theme.instance().colors
    return f"""
    /* ── Global ───────────────────────────────────── */
    QMainWindow, QWidget#central {{
        background-color: {t.bg_primary};
        color: {t.text_primary};
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}
    QWidget {{
        color: {t.text_primary};
    }}

    /* ── Sidebar ──────────────────────────────────── */
    QWidget#sidebar {{
        background-color: {t.sidebar_bg};
        border-right: 1px solid {t.border};
    }}
    QLabel#sidebar_title {{
        color: {t.accent};
        font-size: 16px;
        font-weight: bold;
        padding: 16px 20px;
    }}
    QPushButton.sidebar_btn {{
        background-color: transparent;
        color: {t.text_secondary};
        border: none;
        text-align: left;
        padding: 12px 20px;
        font-size: 13px;
        border-radius: 0px;
    }}
    QPushButton.sidebar_btn:hover {{
        background-color: {t.sidebar_hover};
        color: {t.text_primary};
    }}
    QPushButton.sidebar_btn[active="true"] {{
        background-color: {t.sidebar_active};
        color: {t.accent};
        border-left: 3px solid {t.accent};
        font-weight: 600;
    }}

    /* ── Header ───────────────────────────────────── */
    QWidget#header {{
        background-color: {t.header_bg};
        border-bottom: 1px solid {t.border};
    }}
    QLabel#page_title {{
        color: {t.text_primary};
        font-size: 20px;
        font-weight: bold;
    }}
    QLabel#datetime_label {{
        color: {t.text_secondary};
        font-size: 12px;
    }}

    /* ── Cards ────────────────────────────────────── */
    QFrame.card {{
        background-color: {t.bg_card};
        border: 1px solid {t.border};
        border-radius: 10px;
        padding: 16px;
    }}
    QFrame.stat_card {{
        background-color: {t.bg_card};
        border: 1px solid {t.border};
        border-radius: 10px;
        padding: 20px;
    }}
    QLabel.stat_value {{
        color: {t.text_primary};
        font-size: 24px;
        font-weight: bold;
    }}
    QLabel.stat_label {{
        color: {t.text_secondary};
        font-size: 12px;
    }}

    /* ── Buttons ──────────────────────────────────── */
    QPushButton {{
        background-color: {t.bg_tertiary};
        color: {t.text_primary};
        border: 1px solid {t.border};
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {t.bg_hover};
        border-color: {t.border_light};
    }}
    QPushButton:pressed {{
        background-color: {t.border};
    }}
    QPushButton[class="primary"] {{
        background-color: {t.accent};
        color: white;
        border: none;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: {t.accent_hover};
    }}
    QPushButton[class="success"] {{
        background-color: {t.success};
        color: white;
        border: none;
    }}
    QPushButton[class="danger"] {{
        background-color: {t.danger};
        color: white;
        border: none;
    }}
    QPushButton[class="ghost"] {{
        background-color: transparent;
        border: none;
        color: {t.text_secondary};
    }}
    QPushButton[class="ghost"]:hover {{
        color: {t.text_primary};
        background-color: {t.bg_hover};
    }}

    /* ── Inputs ───────────────────────────────────── */
    QLineEdit, QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {t.bg_input};
        color: {t.text_primary};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {t.accent};
    }}
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {t.accent};
    }}
    QLineEdit:disabled {{
        background-color: {t.bg_tertiary};
        color: {t.text_muted};
    }}
    QComboBox {{
        background-color: {t.bg_input};
        color: {t.text_primary};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QComboBox:hover {{
        border-color: {t.border_light};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t.bg_secondary};
        color: {t.text_primary};
        border: 1px solid {t.border};
        selection-background-color: {t.accent};
    }}

    /* ── Tables ───────────────────────────────────── */
    QTableWidget {{
        background-color: {t.bg_secondary};
        color: {t.text_primary};
        border: 1px solid {t.border};
        border-radius: 8px;
        gridline-color: {t.border};
        font-size: 12px;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border-bottom: 1px solid {t.border};
    }}
    QTableWidget::item:selected {{
        background-color: {t.accent_bg};
        color: {t.text_primary};
    }}
    QTableWidget::item:hover {{
        background-color: {t.bg_hover};
    }}
    QHeaderView::section {{
        background-color: {t.bg_tertiary};
        color: {t.text_secondary};
        padding: 8px 10px;
        border: none;
        border-bottom: 2px solid {t.border};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }}

    /* ── Scrollbars ───────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t.scrollbar};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t.scrollbar_hover};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t.scrollbar};
        border-radius: 4px;
    }}

    /* ── Tabs ─────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {t.border};
        background-color: {t.bg_secondary};
        border-radius: 8px;
    }}
    QTabBar::tab {{
        background-color: {t.bg_tertiary};
        color: {t.text_secondary};
        padding: 10px 20px;
        border: none;
        font-size: 13px;
    }}
    QTabBar::tab:selected {{
        background-color: {t.bg_secondary};
        color: {t.accent};
        border-bottom: 2px solid {t.accent};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        color: {t.text_primary};
    }}

    /* ── Labels ───────────────────────────────────── */
    QLabel {{
        color: {t.text_primary};
    }}
    QLabel.section_title {{
        font-size: 16px;
        font-weight: 600;
        color: {t.text_primary};
    }}
    QLabel.field_label {{
        color: {t.text_secondary};
        font-size: 12px;
        font-weight: 500;
    }}
    QLabel.error_label {{
        color: {t.danger};
        font-size: 11px;
    }}

    /* ── Dialogs ──────────────────────────────────── */
    QDialog {{
        background-color: {t.bg_secondary};
        color: {t.text_primary};
    }}
    QMessageBox {{
        background-color: {t.bg_secondary};
    }}

    /* ── Tooltips ─────────────────────────────────── */
    QToolTip {{
        background-color: {t.bg_tertiary};
        color: {t.text_primary};
        border: 1px solid {t.border};
        padding: 6px;
        border-radius: 4px;
        font-size: 12px;
    }}

    /* ── Group Boxes ──────────────────────────────── */
    QGroupBox {{
        color: {t.text_primary};
        border: 1px solid {t.border};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    """
