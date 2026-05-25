"""Main application shell for the PySide6 prototype."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


DEFAULT_PRESET_TABS: tuple[str, ...] = (
    "차량 거동",
    "GPS / LapTime",
    "냉각 효율",
    "엔진 안전",
    "DBW / ETC",
    "전기 / 전압",
    "서스펜션",
    "데이터 분석",
    "문서",
    "사용자 프리셋",
)

DEFAULT_ANALYSIS_ITEMS: tuple[str, ...] = (
    "Time-Series Graph",
    "GPS Map",
    "G-G Diagram",
    "3D Vehicle Model",
    "Current Values Table",
    "Benchmark Summary",
)


class MainWindow(QtWidgets.QMainWindow):
    """Korean-first shell that mirrors the SRS and root UI storyboard."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("MF-LOG-ANALYZER v2 Prototype")
        self.setFont(QtGui.QFont("Malgun Gothic", 9))
        self.resize(1400, 900)

        self._all_analysis_items = list(DEFAULT_ANALYSIS_ITEMS)

        self._build_menu_bar()
        self._build_central_workspace()
        self._build_left_sidebar()
        self._build_right_properties_panel()
        self._build_bottom_timeline()
        self._apply_theme()

        self.add_analysis_window("Time-Series Graph")

    def set_playback_position(self, sample_index: int, seconds: float) -> None:
        self.timeline_status.setText(f"시간 {seconds:.3f} s | 샘플 {sample_index}")

    def add_analysis_window(self, title: str) -> QtWidgets.QMdiSubWindow:
        widget = QtWidgets.QFrame()
        widget.setObjectName("analysisWindowFrame")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(14, 12, 14, 12)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("analysisWindowTitle")
        status_label = QtWidgets.QLabel("데이터를 불러오면 이 창에 분석 결과가 표시됩니다.")
        status_label.setObjectName("analysisWindowPlaceholder")
        status_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(status_label)
        layout.addStretch(1)

        sub_window = self.workspace.addSubWindow(widget)
        sub_window.setWindowTitle(title)
        sub_window.resize(460, 260)
        sub_window.show()
        return sub_window

    def _build_menu_bar(self) -> None:
        menus = {
            "파일": ("Open CSV", "Open Project", "Save Project", "Export Report", "Exit"),
            "편집": ("Undo", "Redo", "Copy", "Delete", "Rename"),
            "도구": (
                "Log Health Check",
                "Column Mapping",
                "Derived Channel Editor",
                "Capture Workspace Snapshot",
            ),
            "설정": ("General", "Vehicle Profiles", "Language", "Units", "Performance"),
            "도움말": ("User Guide", "Sensor Naming Guide", "Calibration Guide", "About"),
        }
        for menu_title, action_titles in menus.items():
            menu = self.menuBar().addMenu(menu_title)
            for action_title in action_titles:
                action = menu.addAction(action_title)
                action.setObjectName(_object_name(action_title, suffix="Action"))

    def _build_central_workspace(self) -> None:
        central = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.preset_tabs = QtWidgets.QTabBar()
        self.preset_tabs.setObjectName("presetTabs")
        self.preset_tabs.setExpanding(False)
        self.preset_tabs.setMovable(True)
        for tab_title in DEFAULT_PRESET_TABS:
            self.preset_tabs.addTab(tab_title)

        self.workspace = QtWidgets.QMdiArea()
        self.workspace.setObjectName("workspace")
        self.workspace.setViewMode(QtWidgets.QMdiArea.ViewMode.SubWindowView)
        self.workspace.setBackground(QtGui.QBrush(QtGui.QColor("#202326")))

        central_layout.addWidget(self.preset_tabs)
        central_layout.addWidget(self.workspace, 1)
        self.setCentralWidget(central)

    def _build_left_sidebar(self) -> None:
        sidebar = QtWidgets.QDockWidget("분석 / 문서", self)
        sidebar.setObjectName("leftSidebar")
        sidebar.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.sidebar_search = QtWidgets.QLineEdit()
        self.sidebar_search.setObjectName("sidebarSearch")
        self.sidebar_search.setPlaceholderText("분석/문서 검색")
        self.sidebar_search.textChanged.connect(self._filter_analysis_items)

        self.analysis_list = QtWidgets.QListWidget()
        self.analysis_list.setObjectName("analysisList")
        self.analysis_list.itemDoubleClicked.connect(
            lambda item: self.add_analysis_window(item.text())
        )

        self.add_window_button = QtWidgets.QPushButton("추가")
        self.add_window_button.setObjectName("addWindowButton")
        self.add_window_button.clicked.connect(self._add_selected_analysis_window)

        layout.addWidget(self.sidebar_search)
        layout.addWidget(self.analysis_list, 1)
        layout.addWidget(self.add_window_button)
        sidebar.setWidget(content)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, sidebar)
        self.left_sidebar = sidebar

        self._filter_analysis_items("")

    def _build_right_properties_panel(self) -> None:
        self.properties_panel = QtWidgets.QDockWidget("속성", self)
        self.properties_panel.setObjectName("propertiesPanel")
        self.properties_panel.setAllowedAreas(QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addRow("선택 창", QtWidgets.QLabel("Time-Series Graph"))
        layout.addRow("그래프 모드", QtWidgets.QLabel("Overlay"))
        layout.addRow("단위", QtWidgets.QLabel("프로필 기본값"))
        self.properties_panel.setWidget(content)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.properties_panel)

    def _build_bottom_timeline(self) -> None:
        self.timeline_status = QtWidgets.QLabel("시간 0.000 s | 샘플 0")
        self.timeline_status.setObjectName("timelineStatus")
        self.statusBar().addPermanentWidget(self.timeline_status, 1)
        self.statusBar().showMessage("CSV를 열어 분석을 시작하세요.")

    def _filter_analysis_items(self, text: str) -> None:
        query = text.strip().lower()
        self.analysis_list.clear()
        for item in self._all_analysis_items:
            if not query or query in item.lower():
                self.analysis_list.addItem(item)

    def _add_selected_analysis_window(self) -> None:
        item = self.analysis_list.currentItem()
        if item is None and self.analysis_list.count() > 0:
            item = self.analysis_list.item(0)
        if item is not None:
            self.add_analysis_window(item.text())

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QMdiArea {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                background: #202326;
                color: #e7ecef;
            }
            QMenuBar, QMenu, QDockWidget, QStatusBar, QTabBar::tab {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                background: #2b2f33;
                color: #e7ecef;
            }
            QTabBar::tab {
                padding: 8px 12px;
                border-right: 1px solid #3a4046;
            }
            QTabBar::tab:selected {
                background: #3a4046;
                color: #f4c95d;
            }
            QLineEdit, QListWidget {
                background: #171a1d;
                color: #e7ecef;
                border: 1px solid #3a4046;
                padding: 6px;
            }
            QPushButton {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                background: #3f6f8f;
                color: #ffffff;
                border: 0;
                padding: 7px 10px;
            }
            QLabel {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                color: #d7dde2;
            }
            QFrame#analysisWindowFrame {
                background: #252a2e;
            }
            QLabel#analysisWindowTitle {
                color: #f4c95d;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#analysisWindowPlaceholder {
                color: #b8c0c7;
            }
            """
        )


def _object_name(text: str, *, suffix: str) -> str:
    cleaned = "".join(char if char.isalnum() else " " for char in text)
    parts = cleaned.split()
    if not parts:
        return suffix[:1].lower() + suffix[1:]
    first, *rest = parts
    return first[:1].lower() + first[1:] + "".join(part.title() for part in rest) + suffix
