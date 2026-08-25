"""K-Audio theme and shared widget styles."""

# ─────────────────────────── Color Palette ───────────────────────────

THEME_COLORS = {
    "bg_primary": "#0f1011",
    "bg_secondary": "#151617",
    "bg_tertiary": "#1a1b1d",
    "bg_card": "#1d1e20",
    "bg_hover": "#232527",
    "bg_active": "#18332d",
    "border": "#303235",
    "border_active": "#43d9b0",
    "text_primary": "#f2f3f3",
    "text_secondary": "#a5a7a8",
    "text_muted": "#707274",
    "accent": "#43d9b0",
    "accent_hover": "#68e6c2",
    "accent_glow": "#43d9b026",
    "success": "#43d5a0",
    "warning": "#f3be62",
    "error": "#ff7d8d",
    "info": "#62c3ff",
    "sidebar_bg": "#121314",
    "sidebar_active": "#1b2724",
    "sidebar_accent": "#43d9b0",
}


# ─────────────────────────── QSS Stylesheet ─────────────────────────

DARK_QSS = f"""
/* ── Global ── */
QWidget {{
    background-color: {THEME_COLORS["bg_primary"]};
    color: {THEME_COLORS["text_primary"]};
    font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    font-size: 14px;
}}

QMainWindow {{
    background-color: {THEME_COLORS["bg_primary"]};
}}
QWidget#appRoot, QStackedWidget#mainStack, QWidget#dashboardBody,
QWidget#toolShell {{
    background-color: #101112;
}}
QFrame#appBar {{
    background-color: #171819;
    border: none;
    border-bottom: 1px solid {THEME_COLORS["border"]};
}}
QPushButton#brandMark {{
    color: #07110e;
    background-color: {THEME_COLORS["accent"]};
    border: none;
    border-radius: 9px;
    padding: 0;
    font-size: 16px;
    font-weight: 900;
}}
QLabel#appBrand {{ color: #f5f5f5; font-size: 14px; font-weight: 900; }}
QLabel#appEdition {{ color: {THEME_COLORS["accent"]}; font-size: 9px; font-weight: 800; letter-spacing: 1px; }}
QLabel#appVersion {{ color: {THEME_COLORS["text_muted"]}; font-size: 9px; }}
QComboBox#toolPicker {{ min-height: 20px; padding: 5px 10px; border-radius: 8px; }}
QPushButton#topIconBtn {{ padding: 0; border: none; background: transparent; font-size: 16px; }}
QPushButton#topIconBtn:hover {{ color: {THEME_COLORS["accent"]}; background: {THEME_COLORS["bg_hover"]}; }}
QScrollArea#dashboardScroll {{ background: #101112; border: none; }}
QLabel#eyebrow {{ color: {THEME_COLORS["accent"]}; font-size: 10px; font-weight: 900; letter-spacing: 2px; }}
QLabel#heroTitle {{ color: #f5f5f5; font-size: 30px; font-weight: 900; padding: 8px 0 2px 0; }}
QLabel#heroSubtitle {{ color: {THEME_COLORS["text_muted"]}; font-size: 12px; }}
QLabel#sectionTitle {{ color: {THEME_COLORS["text_muted"]}; font-size: 10px; font-weight: 900; letter-spacing: 1px; }}
QFrame#sectionDivider {{ color: {THEME_COLORS["border"]}; margin-left: 12px; }}
QPushButton#toolCard {{
    background-color: #18191a;
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 14px;
    padding: 0;
    min-height: 158px;
    text-align: left;
}}
QPushButton#toolCard:hover {{
    background-color: #1b211f;
    border-color: #31584d;
}}
QPushButton#toolCard:pressed {{ background-color: #15231f; }}
QPushButton#toolCard QLabel {{ background: transparent; }}
QLabel#cardIcon {{
    color: {THEME_COLORS["accent"]};
    background-color: #16332b;
    border-radius: 11px;
    font-size: 18px;
}}
QLabel#cardBadge {{
    color: #75d9bd;
    background-color: #14251f;
    border: 1px solid #285043;
    border-radius: 9px;
    padding: 4px 8px;
    font-size: 8px;
    font-weight: 800;
}}
QLabel#cardTitle {{ color: #f3f3f3; font-size: 15px; font-weight: 800; padding-top: 3px; }}
QLabel#cardDescription {{ color: {THEME_COLORS["text_secondary"]}; font-size: 11px; }}
QLabel#cardAction {{ color: {THEME_COLORS["accent"]}; font-size: 10px; font-weight: 800; }}
QPushButton#backBtn {{
    background: transparent;
    border: none;
    color: {THEME_COLORS["text_secondary"]};
    padding: 5px 2px;
}}
QPushButton#backBtn:hover {{ color: {THEME_COLORS["accent"]}; background: transparent; }}
QFrame#toolHero {{
    background-color: #171918;
    border: 1px solid #2b3431;
    border-radius: 14px;
}}
QLabel#toolHeroIcon {{
    color: {THEME_COLORS["accent"]};
    background-color: #15362d;
    border: 1px solid #235444;
    border-radius: 12px;
    font-size: 19px;
}}
QLabel#toolHeroGroup {{ color: {THEME_COLORS["accent"]}; font-size: 8px; font-weight: 900; letter-spacing: 2px; }}
QLabel#toolHeroTitle {{ color: #f5f5f5; font-size: 20px; font-weight: 900; }}
QLabel#toolHeroDescription {{ color: {THEME_COLORS["text_muted"]}; font-size: 11px; }}
QWidget[modernTool="true"] {{ background: transparent; }}
QWidget[modernTool="true"] QGroupBox[modernCard="true"] {{
    background-color: #171819;
    border: 1px solid #303335;
    border-radius: 14px;
    margin-top: 16px;
    padding: 22px 16px 16px 16px;
    color: #e8e9e9;
    font-size: 11px;
    font-weight: 800;
}}
QWidget[modernTool="true"] QGroupBox[modernCard="true"]::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 8px;
    color: #d7d8d8;
    background-color: #171819;
}}
QWidget[modernTool="true"] QLineEdit,
QWidget[modernTool="true"] QComboBox,
QWidget[modernTool="true"] QSpinBox,
QWidget[modernTool="true"] QDoubleSpinBox {{
    min-height: 24px;
    padding: 6px 10px;
    background-color: #1d1f20;
    border-color: #35383a;
}}
QWidget[modernTool="true"] QTextEdit,
QWidget[modernTool="true"] QPlainTextEdit,
QWidget[modernTool="true"] QListWidget,
QWidget[modernTool="true"] QTableWidget {{
    background-color: #1a1c1d;
    border-color: #333638;
}}
QWidget[modernTool="true"] QPushButton {{ min-height: 22px; padding: 7px 14px; }}
QWidget[modernTool="true"] QPushButton#primaryBtn {{ min-height: 26px; }}
QWidget[modernTool="true"] QSplitter::handle {{ background: transparent; }}
QWidget[modernTool="true"] QSplitter::handle:horizontal {{ width: 8px; }}
QWidget[modernTool="true"] QSplitter::handle:vertical {{ height: 8px; }}
QWidget#contentShell {{ background-color: #101112; }}
QStackedWidget#workspace {{
    background-color: #111213;
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 16px;
}}
QScrollArea#toolPage {{
    background: transparent;
    border: none;
}}
QScrollArea#toolPage > QWidget > QWidget {{ background: transparent; }}
QFrame#topBar {{
    background-color: #171819;
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 14px;
}}
QLabel#pageTitle {{ font-size: 23px; font-weight: 800; color: #f5f5f5; }}
QLabel#pageSubtitle {{ font-size: 11px; color: {THEME_COLORS["text_muted"]}; }}
QLabel#studioBadge {{
    color: {THEME_COLORS["accent"]}; background: #14251f;
    border: 1px solid #245143; border-radius: 10px;
    padding: 6px 10px; font-size: 9px; font-weight: 800;
}}
QPushButton#menuBtn {{ padding: 0; font-size: 17px; border-radius: 10px; }}

/* ── Labels ── */
QLabel {{
    color: {THEME_COLORS["text_primary"]};
    background: transparent;
}}
QLabel[heading="true"] {{
    color: {THEME_COLORS["accent"]};
    font-weight: 700;
    font-size: 20px;
    padding: 2px 0px 8px 0px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {THEME_COLORS["bg_card"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 18px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {THEME_COLORS["bg_hover"]};
    border-color: {THEME_COLORS["accent"]};
    color: {THEME_COLORS["accent"]};
}}
QPushButton:pressed {{
    background-color: {THEME_COLORS["bg_active"]};
}}
QPushButton:disabled {{
    background-color: {THEME_COLORS["bg_secondary"]};
    color: {THEME_COLORS["text_muted"]};
    border-color: {THEME_COLORS["border"]};
}}
QPushButton#primaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #238f73, stop:1 #43d9b0);
    color: #07110e;
    border: none;
    font-weight: 700;
}}
QPushButton#primaryBtn:hover {{
    background-color: {THEME_COLORS["accent_hover"]};
}}

/* ── Inputs ── */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {THEME_COLORS["accent"]};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {THEME_COLORS["accent"]};
    background-color: {THEME_COLORS["bg_card"]};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
    color: {THEME_COLORS["text_muted"]};
    background-color: {THEME_COLORS["bg_secondary"]};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: {THEME_COLORS["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {THEME_COLORS["bg_card"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    selection-background-color: {THEME_COLORS["bg_active"]};
    selection-color: {THEME_COLORS["accent"]};
}}

/* ── Sliders ── */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {THEME_COLORS["bg_active"]};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {THEME_COLORS["accent"]};
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {THEME_COLORS["accent_hover"]};
}}

/* ── SpinBox ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 8px;
    padding: 6px 8px;
    min-height: 22px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {THEME_COLORS["accent"]}; }}

/* ── GroupBox ── */
QGroupBox {{
    background-color: {THEME_COLORS["bg_secondary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 13px;
    margin-top: 16px;
    padding: 18px 12px 12px 12px;
    font-weight: 700;
    font-size: 12px;
    color: {THEME_COLORS["accent"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: {THEME_COLORS["text_primary"]};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {THEME_COLORS["border"]};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {THEME_COLORS["bg_secondary"]};
    width: 8px;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {THEME_COLORS["bg_active"]};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {THEME_COLORS["accent"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {THEME_COLORS["bg_secondary"]};
    height: 8px;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {THEME_COLORS["bg_active"]};
    min-width: 30px;
    border-radius: 4px;
}}

/* ── ListWidget ── */
QListWidget {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 7px;
}}
QListWidget::item:selected {{
    background-color: {THEME_COLORS["bg_active"]};
    color: {THEME_COLORS["accent"]};
}}
QListWidget::item:hover {{
    background-color: {THEME_COLORS["bg_hover"]};
}}

/* ── TabWidget ── */
QTabWidget::pane {{
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 10px;
    background-color: {THEME_COLORS["bg_secondary"]};
}}
QTabBar::tab {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_secondary"]};
    border: 1px solid {THEME_COLORS["border"]};
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: {THEME_COLORS["bg_secondary"]};
    color: {THEME_COLORS["accent"]};
    border-bottom: 2px solid {THEME_COLORS["accent"]};
}}
QTabBar::tab:hover {{
    color: {THEME_COLORS["accent"]};
}}

/* ── ProgressBar ── */
QProgressBar {{
    background-color: {THEME_COLORS["bg_tertiary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 7px;
    height: 20px;
    text-align: center;
    color: {THEME_COLORS["text_primary"]};
    font-weight: 700;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #238f73, stop:1 #43d9b0);
    border-radius: 6px;
}}

/* ── Tables ── */
QTableWidget, QTableView, QTreeWidget {{
    background-color: {THEME_COLORS["bg_secondary"]};
    alternate-background-color: {THEME_COLORS["bg_tertiary"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 10px;
    gridline-color: {THEME_COLORS["border"]};
    selection-background-color: {THEME_COLORS["bg_active"]};
    selection-color: {THEME_COLORS["text_primary"]};
    outline: none;
}}
QHeaderView::section {{
    background-color: {THEME_COLORS["bg_card"]};
    color: {THEME_COLORS["text_secondary"]};
    border: none;
    border-bottom: 1px solid {THEME_COLORS["border"]};
    padding: 9px 10px;
    font-weight: 700;
}}

/* ── Checkboxes ── */
QCheckBox {{ spacing: 8px; color: {THEME_COLORS["text_secondary"]}; }}
QCheckBox:hover {{ color: {THEME_COLORS["text_primary"]}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 5px;
    background: {THEME_COLORS["bg_tertiary"]};
}}
QCheckBox::indicator:checked {{
    background: {THEME_COLORS["accent"]};
    border-color: {THEME_COLORS["accent"]};
}}

QMenu {{
    background-color: {THEME_COLORS["bg_card"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 5px; }}
QMenu::item:selected {{ background-color: {THEME_COLORS["bg_active"]}; }}

/* ── StatusBar ── */
QStatusBar {{
    background-color: {THEME_COLORS["sidebar_bg"]};
    color: {THEME_COLORS["text_secondary"]};
    border-top: 1px solid {THEME_COLORS["border"]};
    font-size: 11px;
    padding: 2px 8px;
}}

/* ── ToolTip ── */
QToolTip {{
    background-color: {THEME_COLORS["bg_card"]};
    color: {THEME_COLORS["text_primary"]};
    border: 1px solid {THEME_COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Readability & interaction overrides ── */
QLabel#toolHeroDescription {{ color: {THEME_COLORS["text_secondary"]}; font-size: 12px; }}
QLabel#logTitle {{
    color: {THEME_COLORS["text_secondary"]};
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1px;
    padding: 5px 2px 1px 2px;
}}
QPlainTextEdit#processLog {{
    background-color: #11191a;
    border: 1px solid #2d4540;
    border-left: 3px solid {THEME_COLORS["accent"]};
    border-radius: 10px;
    color: #d2dcda;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    padding: 10px;
}}
QPushButton {{ font-size: 13px; }}
QPushButton:focus {{ border: 2px solid {THEME_COLORS["accent"]}; }}
QPushButton:disabled {{
    color: #8f9493;
    background-color: #202223;
    border-color: #343738;
}}
QPushButton#primaryBtn:disabled {{
    color: #c0c6c4;
    background: #26312e;
    border: 1px solid #465650;
}}
QPushButton#backBtn {{
    min-height: 34px;
    padding: 7px 14px;
    color: #e1e5e4;
    background-color: #1b1d1e;
    border: 1px solid #3a3d3f;
    border-radius: 9px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#backBtn:hover {{
    color: {THEME_COLORS["accent"]};
    background-color: #1c2925;
    border-color: #356356;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox,
QSpinBox, QDoubleSpinBox {{ font-size: 14px; }}
QComboBox::drop-down {{
    border: none;
    border-left: 1px solid {THEME_COLORS["border"]};
    width: 28px;
}}
QSpinBox, QDoubleSpinBox {{ min-height: 28px; padding-right: 28px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: #292b2d;
    border-left: 1px solid #414447;
    width: 24px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background-color: #315047; }}
QCheckBox {{ spacing: 10px; color: {THEME_COLORS["text_primary"]}; font-size: 13px; }}
QCheckBox::indicator {{
    width: 19px; height: 19px;
    border: 2px solid #5b6062;
    border-radius: 5px;
    background: #17191a;
}}
QCheckBox::indicator:checked {{
    background: {THEME_COLORS["accent"]};
    border: 4px solid #1b5f4e;
}}
QWidget[modernTool="true"] QGroupBox[modernCard="true"] {{ font-size: 13px; }}
QWidget[modernTool="true"] QLineEdit,
QWidget[modernTool="true"] QComboBox,
QWidget[modernTool="true"] QSpinBox,
QWidget[modernTool="true"] QDoubleSpinBox {{ min-height: 28px; padding-top: 7px; padding-bottom: 7px; }}
QWidget[modernTool="true"] QPushButton {{ min-height: 26px; padding: 8px 15px; }}
QWidget[modernTool="true"] QPushButton#primaryBtn {{ min-height: 30px; }}
"""


# ─────────────────────────── Sidebar Style ───────────────────────────

SIDEBAR_QSS = f"""
QWidget#sidebar {{
    background-color: {THEME_COLORS["sidebar_bg"]};
    border-right: 1px solid {THEME_COLORS["border"]};
}}
QLabel#logo {{
    color: #ffffff;
    font-size: 21px;
    font-weight: 900;
    padding: 0;
    letter-spacing: 1px;
}}
QLabel#logoMark {{
    color: #07110e;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2ab892, stop:1 #58e4bd);
    border-radius: 12px;
    font-size: 22px;
    font-weight: 900;
}}
QLabel#subtitle {{
    color: {THEME_COLORS["text_muted"]};
    font-size: 10px;
    padding: 0;
    letter-spacing: 2px;
}}
QLabel[navSection="true"] {{
    color: {THEME_COLORS["text_muted"]}; background: transparent;
    font-size: 9px; font-weight: 800; letter-spacing: 1px;
    padding: 16px 10px 6px 10px;
}}
QPushButton#navBtn {{
    background-color: transparent;
    color: {THEME_COLORS["text_secondary"]};
    border: none;
    border-radius: 9px;
    padding: 10px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#navBtn:hover {{
    background-color: {THEME_COLORS["sidebar_active"]};
    color: {THEME_COLORS["accent"]};
}}
QPushButton#navBtn:checked {{
    background-color: {THEME_COLORS["sidebar_active"]};
    color: {THEME_COLORS["accent"]};
    border-left: 3px solid {THEME_COLORS["sidebar_accent"]};
    border-radius: 4px 9px 9px 4px;
}}
QLabel#versionLabel {{
    color: {THEME_COLORS["text_muted"]}; font-size: 10px;
    padding: 10px; border-top: 1px solid {THEME_COLORS["border"]};
}}
QFrame#separator {{
    background-color: {THEME_COLORS["border"]};
    max-height: 1px;
    min-height: 1px;
    margin: 6px 10px;
}}
"""


class ThemeManager:
    """Singleton to manage application theme."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_app_stylesheet():
        return DARK_QSS

    @staticmethod
    def get_sidebar_stylesheet():
        return SIDEBAR_QSS

    @staticmethod
    def color(key: str) -> str:
        return THEME_COLORS.get(key, "#ffffff")
