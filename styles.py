"""
QSS Stylesheet for GEM Intern PyQt6 app.
Notion-inspired design system with clean, modern aesthetics.
"""

# Notion-inspired Color Palette
# Base colors
BG_PRIMARY = "#FFFFFF"           # Pure white background
BG_SECONDARY = "#F7F6F3"         # Warm off-white (sidebar)
BG_TERTIARY = "#FAFAF9"          # Subtle gray for hover

# Border colors
BORDER_LIGHT = "#E9E9E7"         # Very light gray border
BORDER_MEDIUM = "#DBDBD9"        # Medium gray border
BORDER_DARK = "#D3D3D1"          # Darker border for emphasis

# Text colors
TEXT_PRIMARY = "#37352F"         # Dark gray for main text
TEXT_SECONDARY = "#787774"       # Medium gray for secondary text
TEXT_TERTIARY = "#9B9A97"        # Light gray for captions

# Accent colors (soft blue - Notion style)
PRIMARY = "#2383E2"              # Soft blue
PRIMARY_LIGHT = "#E8F3FC"        # Very light blue
PRIMARY_LIGHTER = "#F3F9FE"      # Ultra light blue for hover
PRIMARY_DARK = "#1F6FC1"         # Darker blue for press

# Semantic colors - Success
SUCCESS_BG = "#EDF8F0"           # Light green background
SUCCESS_BORDER = "#4CAF50"       # Green border
SUCCESS_TEXT = "#1E7D32"         # Dark green text

# Semantic colors - Active/Info
INFO_BG = "#F3F9FE"              # Light blue background
INFO_BORDER = "#2383E2"          # Blue border
INFO_TEXT = "#1F6FC1"            # Dark blue text

# Semantic colors - Pending/Neutral
NEUTRAL_BG = "#F7F6F3"           # Warm gray background
NEUTRAL_BORDER = "#E9E9E7"       # Light gray border
NEUTRAL_TEXT = "#787774"         # Medium gray text

# Semantic colors - Warning
WARNING_BG = "#FFF8E1"           # Light yellow background
WARNING_BORDER = "#FFA726"       # Orange border
WARNING_TEXT = "#E65100"         # Dark orange text

# Semantic colors - Error
ERROR_BG = "#FFEBEE"             # Light red background
ERROR_BORDER = "#EF5350"         # Red border
ERROR_TEXT = "#C62828"           # Dark red text

# Shadow
SHADOW_LIGHT = "rgba(15, 15, 15, 0.05)"  # Very subtle shadow
SHADOW_MEDIUM = "rgba(15, 15, 15, 0.1)"  # Medium shadow

MAIN_STYLESHEET = f"""
/* ========================================
   NOTION-INSPIRED DESIGN SYSTEM
   Clean, modern, and minimalist
   ======================================== */

QMainWindow {{
    background-color: {BG_PRIMARY};
}}

QWidget {{
    color: {TEXT_PRIMARY};
}}

/* ========================================
   SIDEBAR NAVIGATION
   ======================================== */

#sidebar {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER_LIGHT};
}}

#sidebar QPushButton {{
    text-align: left;
    padding: 8px 12px;
    border: none;
    background-color: transparent;
    font-size: 14px;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    margin: 2px 8px;
}}

#sidebar QPushButton:hover {{
    background-color: {BG_TERTIARY};
}}

#sidebar QPushButton[active="true"] {{
    background-color: {PRIMARY_LIGHTER};
    color: {PRIMARY};
    font-weight: 500;
}}

/* Section headers in sidebar */
#sectionHeader {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
    font-weight: 600;
    padding: 12px 16px 6px 16px;
}}

/* ========================================
   BUTTONS
   ======================================== */

/* Primary button - Notion style */
QPushButton[cssClass="primary"] {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    padding: 10px 18px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
}}

QPushButton[cssClass="primary"]:hover {{
    background-color: {PRIMARY_DARK};
}}

QPushButton[cssClass="primary"]:pressed {{
    background-color: {PRIMARY_DARK};
}}

/* Secondary button */
QPushButton[cssClass="secondary"] {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
}}

QPushButton[cssClass="secondary"]:hover {{
    background-color: {BG_TERTIARY};
}}

/* Ghost button (minimal) */
QPushButton[cssClass="ghost"] {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 14px;
}}

QPushButton[cssClass="ghost"]:hover {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
}}

/* ========================================
   CARDS & CONTAINERS
   ======================================== */

/* Standard card with subtle shadow */
QFrame[cssClass="card"] {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 10px;
    padding: 20px;
}}

QFrame[cssClass="card"]:hover {{
    border-color: {BORDER_MEDIUM};
}}

/* Card with left accent border */
QFrame[cssClass="card-done"] {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-left: 4px solid {SUCCESS_BORDER};
    border-radius: 10px;
    padding: 20px;
}}

QFrame[cssClass="card-active"] {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-left: 4px solid {PRIMARY};
    border-radius: 10px;
    padding: 20px;
}}

/* Clickable card */
QFrame[cssClass="card-clickable"] {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 10px;
    padding: 16px;
}}

QFrame[cssClass="card-clickable"]:hover {{
    background-color: {BG_TERTIARY};
    border-color: {BORDER_MEDIUM};
}}

/* ========================================
   STEP INDICATORS
   ======================================== */

QFrame[cssClass="step-done"] {{
    background-color: {SUCCESS_BG};
    border: 1px solid {SUCCESS_BORDER};
    border-radius: 8px;
    padding: 12px 16px;
}}

QFrame[cssClass="step-active"] {{
    background-color: {INFO_BG};
    border: 1px solid {INFO_BORDER};
    border-radius: 8px;
    padding: 12px 16px;
}}

QFrame[cssClass="step-pending"] {{
    background-color: {NEUTRAL_BG};
    border: 1px solid {NEUTRAL_BORDER};
    border-radius: 8px;
    padding: 12px 16px;
}}

/* ========================================
   CALLOUT BOXES (Info/Warning/Success/Error)
   ======================================== */

QFrame[cssClass="info"] {{
    background-color: {INFO_BG};
    border: 1px solid {INFO_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    color: {INFO_TEXT};
}}

QFrame[cssClass="success"] {{
    background-color: {SUCCESS_BG};
    border: 1px solid {SUCCESS_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    color: {SUCCESS_TEXT};
}}

QFrame[cssClass="warning"] {{
    background-color: {WARNING_BG};
    border: 1px solid {WARNING_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    color: {WARNING_TEXT};
}}

QFrame[cssClass="error"] {{
    background-color: {ERROR_BG};
    border: 1px solid {ERROR_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    color: {ERROR_TEXT};
}}

/* ========================================
   PROJECT BANNER
   ======================================== */

QFrame[cssClass="project-banner"] {{
    background-color: {PRIMARY_LIGHTER};
    border: 1px solid {PRIMARY_LIGHT};
    border-left: 3px solid {PRIMARY};
    border-radius: 6px;
    padding: 10px 16px;
}}

/* ========================================
   INPUT FIELDS
   ======================================== */

/* Text areas */
QTextEdit, QPlainTextEdit {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    selection-background-color: {PRIMARY_LIGHT};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {PRIMARY};
    background-color: {BG_PRIMARY};
}}

QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {BORDER_MEDIUM};
}}

/* Line edit */
QLineEdit {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    selection-background-color: {PRIMARY_LIGHT};
}}

QLineEdit:focus {{
    border-color: {PRIMARY};
}}

QLineEdit:hover {{
    border-color: {BORDER_MEDIUM};
}}

/* Combo box - Notion style dropdown */
QComboBox {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    min-height: 28px;
}}

QComboBox:hover {{
    border-color: {BORDER_MEDIUM};
    background-color: {BG_TERTIARY};
}}

QComboBox:focus {{
    border-color: {PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    background-color: {BG_PRIMARY};
    selection-background-color: {BG_TERTIARY};
    padding: 4px;
}}

/* ========================================
   TABS
   ======================================== */

QTabWidget::pane {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    background-color: {BG_PRIMARY};
    padding: 12px;
}}

QTabBar::tab {{
    padding: 10px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
    font-size: 14px;
    color: {TEXT_SECONDARY};
    background-color: transparent;
}}

QTabBar::tab:hover {{
    background-color: {BG_TERTIARY};
    border-radius: 6px 6px 0 0;
}}

QTabBar::tab:selected {{
    background-color: transparent;
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
    color: {PRIMARY};
}}

/* ========================================
   PROGRESS BAR
   ======================================== */

QProgressBar {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 6px;
    text-align: center;
    height: 24px;
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
}}

QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 5px;
}}

/* ========================================
   SCROLL AREAS & SCROLLBARS
   ======================================== */

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_MEDIUM};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_TERTIARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_MEDIUM};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {TEXT_TERTIARY};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ========================================
   SLIDER
   ======================================== */

QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    border-radius: 3px;
    background: {BORDER_LIGHT};
}}

QSlider::handle:horizontal {{
    background: {PRIMARY};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 2px solid {BG_PRIMARY};
}}

QSlider::handle:horizontal:hover {{
    background: {PRIMARY_DARK};
}}

/* ========================================
   SPLITTER
   ======================================== */

QSplitter::handle {{
    background-color: {BORDER_LIGHT};
    width: 1px;
}}

QSplitter::handle:hover {{
    background-color: {BORDER_MEDIUM};
}}

/* ========================================
   GROUP BOX
   ======================================== */

QGroupBox {{
    font-weight: 600;
    font-size: 14px;
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {TEXT_PRIMARY};
}}

/* ========================================
   TABLE WIDGET
   ======================================== */

QTableWidget {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    gridline-color: {BORDER_LIGHT};
    background-color: {BG_PRIMARY};
    alternate-background-color: {BG_TERTIARY};
}}

QTableWidget::item {{
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
}}

QTableWidget::item:selected {{
    background-color: {PRIMARY_LIGHTER};
    color: {PRIMARY};
}}

QTableWidget::item:hover {{
    background-color: {BG_TERTIARY};
}}

QHeaderView::section {{
    background-color: {BG_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER_LIGHT};
    border-right: 1px solid {BORDER_LIGHT};
    padding: 10px 12px;
    font-weight: 600;
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QHeaderView::section:first {{
    border-top-left-radius: 8px;
}}

QHeaderView::section:last {{
    border-top-right-radius: 8px;
    border-right: none;
}}

/* ========================================
   LABELS & TYPOGRAPHY
   ======================================== */

/* Make all labels text-selectable by default */
QLabel {{
    selection-background-color: {PRIMARY_LIGHT};
}}

QLabel[cssClass="title"] {{
    font-size: 26px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel[cssClass="heading1"] {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel[cssClass="heading2"] {{
    font-size: 18px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel[cssClass="heading3"] {{
    font-size: 16px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel[cssClass="subtitle"] {{
    font-size: 14px;
    color: {TEXT_SECONDARY};
}}

QLabel[cssClass="caption"] {{
    font-size: 13px;
    color: {TEXT_TERTIARY};
}}

QLabel[cssClass="small"] {{
    font-size: 12px;
    color: {TEXT_TERTIARY};
}}

/* Badges */
QLabel[cssClass="badge"] {{
    background-color: {NEUTRAL_BG};
    color: {TEXT_PRIMARY};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid {BORDER_LIGHT};
}}

QLabel[cssClass="badge-blue"] {{
    background-color: {PRIMARY_LIGHTER};
    color: {PRIMARY};
    border: 1px solid {PRIMARY_LIGHT};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}}

QLabel[cssClass="badge-green"] {{
    background-color: {SUCCESS_BG};
    color: {SUCCESS_TEXT};
    border: 1px solid {SUCCESS_BORDER};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}}

QLabel[cssClass="badge-orange"] {{
    background-color: {WARNING_BG};
    color: {WARNING_TEXT};
    border: 1px solid {WARNING_BORDER};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}}

QLabel[cssClass="badge-red"] {{
    background-color: {ERROR_BG};
    color: {ERROR_TEXT};
    border: 1px solid {ERROR_BORDER};
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}}

/* ========================================
   LIST WIDGETS
   ======================================== */

QListWidget {{
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    background-color: {BG_PRIMARY};
    padding: 4px;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
}}

QListWidget::item:hover {{
    background-color: {BG_TERTIARY};
}}

QListWidget::item:selected {{
    background-color: {PRIMARY_LIGHTER};
    color: {PRIMARY};
}}

/* ========================================
   CHECKBOXES & RADIO BUTTONS
   ======================================== */

QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {BORDER_MEDIUM};
    background-color: {BG_PRIMARY};
}}

QCheckBox::indicator:hover {{
    border-color: {PRIMARY};
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
}}

QRadioButton {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid {BORDER_MEDIUM};
    background-color: {BG_PRIMARY};
}}

QRadioButton::indicator:hover {{
    border-color: {PRIMARY};
}}

QRadioButton::indicator:checked {{
    background-color: {PRIMARY};
    border: 5px solid {PRIMARY};
}}

/* ========================================
   TOOLTIPS
   ======================================== */

QToolTip {{
    background-color: {TEXT_PRIMARY};
    color: {BG_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}

/* ========================================
   MENU & CONTEXT MENUS
   ======================================== */

QMenu {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
}}

QMenu::item:selected {{
    background-color: {BG_TERTIARY};
}}

QMenu::separator {{
    height: 1px;
    background: {BORDER_LIGHT};
    margin: 6px 8px;
}}
"""
