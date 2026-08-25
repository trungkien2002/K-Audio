"""K-Audio application shell.

The shell owns navigation and responsive presentation only. Every existing tool
widget is mounted unchanged so its signals, state and processing logic remain
intact.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox, QBoxLayout, QComboBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLayout, QMainWindow,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QStatusBar,
    QVBoxLayout, QWidget,
)


TOOLS = [
    {"icon": "", "label": "Crawl", "description": "Tải và quản lý nội dung truyện từ website", "group": "TRUYỆN"},
    {"icon": "", "label": "Tách Chương", "description": "Tách văn bản thành các chương riêng biệt", "group": "TRUYỆN"},
    {"icon": "", "label": "Làm Sạch", "description": "Lọc spam, URL và các ký tự không cần thiết", "group": "TRUYỆN"},
    {"icon": "", "label": "TTS Cơ Bản", "description": "Chuyển văn bản thành giọng nói nhanh chóng", "group": "ÂM THANH"},
    {"icon": "", "label": "OmniVoice", "description": "Không gian tổng hợp giọng nói chuyên sâu", "group": "GIỌNG NÓI"},
    {"icon": "", "label": "Voice Clone", "description": "Tạo và quản lý giọng nói từ audio mẫu", "group": "GIỌNG NÓI"},
    {"icon": "", "label": "Multi-Speaker", "description": "Nhận diện và xử lý nhiều người nói", "group": "GIỌNG NÓI"},
    {"icon": "", "label": "Style Sub", "description": "Thiết kế và xuất phụ đề nghệ thuật", "group": "VIDEO"},
    {"icon": "", "label": "Story Maker", "description": "Tạo nội dung truyện và dựng video", "group": "VIDEO"},
]

SETTINGS = {"icon": "", "label": "Settings", "description": "Cấu hình chung của K-Audio", "group": "HỆ THỐNG"}


class MainWindow(QMainWindow):
    """Responsive home-first shell for all K-Audio modules."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("K-Audio")
        self.setMinimumSize(760, 560)
        self.resize(1440, 880)
        self._cards = []
        self._dashboard_columns = 0
        self._build_ui()
        self._show_home()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_app_bar())

        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")
        self.dashboard = self._build_dashboard()
        self.stack.addWidget(self.dashboard)
        self._create_tool_pages()
        root.addWidget(self.stack, 1)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.status_tool = QLabel("Trang chủ")
        self.status.addWidget(self.status_tool)
        self.status.addPermanentWidget(QLabel("K-Audio"))
        self.setStatusBar(self.status)

    def _build_app_bar(self):
        bar = QFrame()
        bar.setObjectName("appBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 9, 18, 9)
        layout.setSpacing(10)

        self.home_btn = QPushButton("K")
        self.home_btn.setObjectName("brandMark")
        self.home_btn.setFixedSize(34, 34)
        self.home_btn.setToolTip("Về trang chủ")
        self.home_btn.clicked.connect(self._show_home)
        layout.addWidget(self.home_btn)
        brand = QLabel("K-AUDIO")
        brand.setObjectName("appBrand")
        layout.addWidget(brand)
        layout.addStretch()

        self.tool_picker = QComboBox()
        self.tool_picker.setObjectName("toolPicker")
        self.tool_picker.setMinimumWidth(210)
        self.tool_picker.addItem("Chọn công cụ…", -1)
        for index, tool in enumerate(TOOLS):
            self.tool_picker.addItem(tool["label"], index)
        self.tool_picker.currentIndexChanged.connect(self._picker_changed)
        layout.addWidget(self.tool_picker)
        settings_btn = QPushButton("Cài đặt")
        settings_btn.setObjectName("topIconBtn")
        settings_btn.setMinimumHeight(34)
        settings_btn.setToolTip("Cài đặt")
        settings_btn.clicked.connect(lambda: self._select_tool(len(TOOLS)))
        layout.addWidget(settings_btn)
        return bar

    def _build_dashboard(self):
        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("dashboardBody")
        outer = QVBoxLayout(body)
        outer.setContentsMargins(48, 38, 48, 48)
        outer.setSpacing(0)

        eyebrow = QLabel("K-AUDIO")
        eyebrow.setObjectName("eyebrow")
        outer.addWidget(eyebrow)
        title = QLabel("Bạn muốn làm gì hôm nay?")
        title.setObjectName("heroTitle")
        outer.addWidget(title)
        subtitle = QLabel("Chọn một công cụ để bắt đầu. Mọi dự án và thiết lập hiện tại vẫn được giữ nguyên.")
        subtitle.setObjectName("heroSubtitle")
        outer.addWidget(subtitle)
        outer.addSpacing(30)
        section_row = QHBoxLayout()
        section = QLabel("CÔNG CỤ CỦA BẠN")
        section.setObjectName("sectionTitle")
        section_row.addWidget(section)
        divider = QFrame()
        divider.setObjectName("sectionDivider")
        divider.setFrameShape(QFrame.HLine)
        section_row.addWidget(divider, 1)
        outer.addLayout(section_row)
        outer.addSpacing(14)

        self.card_grid = QGridLayout()
        self.card_grid.setContentsMargins(0, 0, 0, 0)
        self.card_grid.setHorizontalSpacing(14)
        self.card_grid.setVerticalSpacing(14)
        for index, tool in enumerate(TOOLS):
            card = self._make_tool_card(tool, index)
            self._cards.append(card)
        outer.addLayout(self.card_grid)
        outer.addStretch()
        scroll.setWidget(body)
        return scroll

    def _make_tool_card(self, tool, index):
        card = QPushButton()
        card.setObjectName("toolCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(158)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.clicked.connect(lambda checked=False, i=index: self._select_tool(i))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        top = QHBoxLayout()
        group = QLabel(tool["group"])
        group.setObjectName("cardBadge")
        top.addWidget(group)
        top.addStretch()
        layout.addLayout(top)
        title = QLabel(tool["label"])
        title.setObjectName("cardTitle")
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        description = QLabel(tool["description"])
        description.setObjectName("cardDescription")
        description.setWordWrap(True)
        description.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(description)
        layout.addStretch()
        action = QLabel("Mở công cụ")
        action.setObjectName("cardAction")
        action.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(action)
        return card

    def _create_tool_pages(self):
        from app.tabs.tab_crawl import TabCrawl
        from app.tabs.tab_split import TabSplit
        from app.tabs.tab_clean import TabClean
        from app.tabs.tab_tts import TabTTS
        from app.tabs.tab_omnivoice import TabOmniVoice
        from app.tabs.tab_voice_clone import TabVoiceClone
        from app.tabs.tab_multispeaker import TabMultiSpeaker
        from app.tabs.tab_style_sub import TabStyleSub
        from app.tabs.tab_story import TabStory
        from app.tabs.tab_settings import TabSettings
        widgets = (
            TabCrawl(), TabSplit(), TabClean(), TabTTS(), TabOmniVoice(),
            TabVoiceClone(), TabMultiSpeaker(), TabStyleSub(), TabStory(), TabSettings(),
        )
        for widget, tool in zip(widgets, TOOLS + [SETTINGS]):
            self._add_tool_page(widget, tool)

    def _add_tool_page(self, widget, tool):
        self._modernize_tool_widget(widget)
        shell = QWidget()
        shell.setObjectName("toolShell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(12)
        header = QHBoxLayout()
        back = QPushButton("Trở về Trang chủ")
        back.setObjectName("backBtn")
        back.clicked.connect(self._show_home)
        header.addWidget(back)
        header.addStretch()
        layout.addLayout(header)

        hero = QFrame()
        hero.setObjectName("toolHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 14, 18, 14)
        hero_layout.setSpacing(14)
        text = QVBoxLayout()
        text.setSpacing(2)
        group = QLabel(tool["group"])
        group.setObjectName("toolHeroGroup")
        title = QLabel(tool["label"])
        title.setObjectName("toolHeroTitle")
        description = QLabel(tool["description"])
        description.setObjectName("toolHeroDescription")
        text.addWidget(group)
        text.addWidget(title)
        text.addWidget(description)
        hero_layout.addLayout(text, 1)
        layout.addWidget(hero)
        page = QScrollArea()
        page.setObjectName("toolPage")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page.setWidget(widget)
        layout.addWidget(page, 1)
        self.stack.addWidget(shell)

    def _modernize_tool_widget(self, widget):
        """Normalize legacy layouts visually without replacing functional controls."""
        widget.setProperty("modernTool", True)
        if widget.layout():
            widget.layout().setContentsMargins(0, 0, 0, 0)
            widget.layout().setSpacing(14)
        for label in widget.findChildren(QLabel):
            inline_style = label.styleSheet()
            if label.property("heading") or "font-size: 18px" in inline_style:
                label.hide()
        for group in widget.findChildren(QGroupBox):
            group.setProperty("modernCard", True)
        for button in widget.findChildren(QPushButton):
            label = button.text().strip()
            if label and not button.toolTip():
                button.setToolTip(label)
            if label and not button.accessibleName():
                button.setAccessibleName(label)
        for spinbox in widget.findChildren(QAbstractSpinBox):
            spinbox.setButtonSymbols(QAbstractSpinBox.PlusMinus)
            spinbox.setAccelerated(True)
        for child_layout in widget.findChildren(QLayout):
            if child_layout.spacing() < 8:
                child_layout.setSpacing(8)
        self._label_log_views(widget)

    def _label_log_views(self, widget):
        """Give every generic log panel an explicit purpose and empty state."""
        from app.widgets.log_viewer import LogViewer
        for log in widget.findChildren(LogViewer):
            log.setObjectName("processLog")
            log.setAccessibleName("Nhật ký xử lý")
            log.setPlaceholderText("Nhật ký tiến trình, cảnh báo và lỗi sẽ hiển thị tại đây.")
            parent = log.parentWidget()
            parent_layout = parent.layout() if parent else None
            if not isinstance(parent_layout, QBoxLayout):
                continue
            index = parent_layout.indexOf(log)
            if index < 0:
                continue
            title = QLabel("NHẬT KÝ XỬ LÝ")
            title.setObjectName("logTitle")
            title.setToolTip("Hiển thị tiến trình, cảnh báo và lỗi của tác vụ hiện tại")
            parent_layout.insertWidget(index, title)

    def _show_home(self):
        self.stack.setCurrentIndex(0)
        self.tool_picker.blockSignals(True)
        self.tool_picker.setCurrentIndex(0)
        self.tool_picker.blockSignals(False)
        self.status_tool.setText("Trang chủ")

    def _picker_changed(self, picker_index):
        tool_index = self.tool_picker.itemData(picker_index)
        if isinstance(tool_index, int) and tool_index >= 0:
            self._select_tool(tool_index)

    def _select_tool(self, index):
        all_tools = TOOLS + [SETTINGS]
        if not 0 <= index < len(all_tools):
            return
        self.stack.setCurrentIndex(index + 1)
        self.status_tool.setText(all_tools[index]["label"])
        self.tool_picker.blockSignals(True)
        self.tool_picker.setCurrentIndex(index + 1 if index < len(TOOLS) else 0)
        self.tool_picker.blockSignals(False)

    def _relayout_dashboard(self, columns):
        if columns == self._dashboard_columns:
            return
        self._dashboard_columns = columns
        while self.card_grid.count():
            self.card_grid.takeAt(0)
        for index, card in enumerate(self._cards):
            self.card_grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        columns = 1 if width < 760 else 2 if width < 1120 else 3
        self._relayout_dashboard(columns)
        margin = 24 if width < 900 else 48
        self.dashboard.widget().layout().setContentsMargins(margin, 28, margin, 40)
