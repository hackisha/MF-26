"""Main application shell for the PySide6 prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
from typing import Callable, Sequence

from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

from mflog_proto.benchmark.metrics import collect_environment
from mflog_proto.data.column_store import ColumnStore
from mflog_proto.data.csv_loader import CsvLoadOptions, load_csv
from mflog_proto.data.derived import compute_basic_derived_channels
from mflog_proto.persistence.project_state import (
    ProjectState,
    WindowState,
    load_project_state,
    save_project_state,
)
from mflog_proto.playback import CursorEvent, CursorKind, PlaybackState
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    DataAnalysisWindow,
    DocumentsWindow,
    GGDiagramWindow,
    GPSMapWindow,
    GPSRouteLayer,
    MapTileProvider,
    VehicleModelWindow,
    load_glb_info,
)
from mflog_proto.ui.time_series_window import TimeSeriesWindow


@dataclass(frozen=True)
class PlaybackMarker:
    name: str
    time_ms: int
    severity: str
    sensor: str
    value: float
    condition: str


@dataclass(frozen=True)
class VisualizationSettings:
    gps_map_background_enabled: bool = False
    graph_line_color: str | None = None
    graph_line_width: float = 1.0
    gg_limit_radius: float = 1.0


@dataclass(frozen=True)
class SidebarSettings:
    search_visible: bool = True
    add_button_visible: bool = True
    sort_mode: str = "Default"
    density: str = "Comfortable"
    width_px: int = 260


class _AnalysisWindowOverlayControls(QtCore.QObject):
    def __init__(
        self,
        sub_window: QtWidgets.QMdiSubWindow,
        content: QtWidgets.QWidget,
    ) -> None:
        super().__init__(sub_window)
        self._sub_window = sub_window
        self._content = content
        self._frame = QtWidgets.QFrame(content)
        self._frame.setObjectName("analysisWindowOverlayControls")
        self._frame.setStyleSheet(
            """
            QFrame#analysisWindowOverlayControls {
                background: rgba(31, 36, 40, 210);
                border: 1px solid #5f6a72;
            }
            QToolButton {
                color: #f2f5f7;
                background: transparent;
                border: none;
                padding: 2px 6px;
                font-weight: 700;
            }
            QToolButton:hover {
                background: #3d5566;
            }
            """
        )

        layout = QtWidgets.QHBoxLayout(self._frame)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self._minimize_button = self._make_button(
            object_name="analysisWindowMinimizeButton",
            text="_",
            tooltip="최소화",
        )
        self._restore_button = self._make_button(
            object_name="analysisWindowRestoreButton",
            text="[]",
            tooltip="복원/최대화",
        )
        self._close_button = self._make_button(
            object_name="analysisWindowCloseButton",
            text="x",
            tooltip="닫기",
        )

        layout.addWidget(self._minimize_button)
        layout.addWidget(self._restore_button)
        layout.addWidget(self._close_button)

        self._minimize_button.clicked.connect(sub_window.showMinimized)
        self._restore_button.clicked.connect(self._toggle_maximized)
        self._close_button.clicked.connect(sub_window.close)
        self._frame.hide()

        sub_window.installEventFilter(self)
        content.installEventFilter(self)
        self.update_geometry()

    def eventFilter(self, watched: object, event: QtCore.QEvent) -> bool:  # noqa: N802
        if event.type() in {
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.WindowStateChange,
        }:
            QtCore.QTimer.singleShot(0, self.update_geometry)
        return super().eventFilter(watched, event)

    def update_geometry(self) -> None:
        if not shiboken6.isValid(self._sub_window) or not shiboken6.isValid(self._content):
            return
        is_maximized = (
            self._sub_window.isMaximized()
            or bool(self._sub_window.windowState() & QtCore.Qt.WindowState.WindowMaximized)
        )
        self._frame.setVisible(is_maximized)
        self._restore_button.setText("[]" if is_maximized else "[ ]")
        self._frame.adjustSize()
        margin = 8
        x = max(margin, self._content.width() - self._frame.width() - margin)
        self._frame.move(x, margin)
        self._frame.raise_()

    def _toggle_maximized(self) -> None:
        if self._sub_window.isMaximized():
            self._sub_window.showNormal()
        else:
            self._sub_window.showMaximized()
        self.update_geometry()

    def _make_button(
        self,
        *,
        object_name: str,
        text: str,
        tooltip: str,
    ) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self._frame)
        button.setObjectName(object_name)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedSize(28, 24)
        button.setAutoRaise(True)
        return button


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
    "Data Analysis",
    "GPS Map",
    "G-G Diagram",
    "3D Vehicle Model",
    "Current Values Table",
    "Benchmark Summary",
    "Documents",
)


class MainWindow(QtWidgets.QMainWindow):
    """Korean-first shell that mirrors the SRS and root UI storyboard."""

    def __init__(self, *, map_tile_provider: MapTileProvider | None = None) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("MF-LOG-ANALYZER v2 Prototype")
        self.setFont(QtGui.QFont("Malgun Gothic", 9))
        self.resize(1400, 900)

        self._all_analysis_items = list(DEFAULT_ANALYSIS_ITEMS)
        self.active_profile = "prototype"
        self.channel_mappings: dict[str, str] = {}
        self.derived_channel_settings: dict[str, dict[str, object]] = {}
        self.selected_channels: list[str] = []
        self.pending_project_state: ProjectState | None = None
        self.loaded_csv_path: Path | None = None
        self.visualization_settings = VisualizationSettings()
        self.sidebar_settings = SidebarSettings()
        self.vehicle_model_path = _root_asset_path("car.glb")
        self.vehicle_model_info = load_glb_info(self.vehicle_model_path)
        self.gps_route_layers: dict[str, GPSRouteLayer] = {}
        self.active_gps_route_name = ""
        self._map_tile_provider = map_tile_provider
        self.playback_state = PlaybackState([0.0])
        self.sensor_series = _blank_sensor_series(self.playback_state.sample_count)
        self.playback_events: tuple[PlaybackMarker, ...] = ()
        self.session_row_count = 0
        self.session_sampling_interval_ms = 0
        self._syncing_event_marker_selection = False
        self.playback_timer = QtCore.QTimer(self)
        self.playback_timer.setInterval(33)
        self.playback_timer.timeout.connect(self._tick_playback_timer)
        self._playback_elapsed = QtCore.QElapsedTimer()
        self._app_event_filter_installed = False
        self._unsubscribe_playback_status = self.playback_state.subscribe(
            self._handle_playback_event
        )

        self._build_menu_bar()
        self._build_central_workspace()
        self._build_left_sidebar()
        self._build_right_properties_panel()
        self._build_playback_dock()
        self._build_bottom_timeline()
        self._apply_theme()
        self.clear_csv_session()

        self.add_analysis_window("Time-Series Graph")
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._app_event_filter_installed = True

    def set_playback_position(self, sample_index: int) -> None:
        self.playback_state.set_sample(sample_index)
        self._update_timeline_status()
        self._update_playback_dock_status()

    def set_playback_seconds(self, seconds: float) -> None:
        self.playback_state.set_seconds(seconds)
        self._update_timeline_status()
        self._update_playback_dock_status()

    def _handle_playback_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_timeline_status()
            self._update_playback_dock_status()

    def _update_timeline_status(self) -> None:
        self.timeline_status.setText(
            f"시간 {self.playback_state.current_seconds:.3f} s | "
            f"샘플 {self.playback_state.current_sample}"
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        app = QtWidgets.QApplication.instance()
        if app is not None and self._app_event_filter_installed:
            app.removeEventFilter(self)
            self._app_event_filter_installed = False
        self._unsubscribe_playback_status()
        super().closeEvent(event)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        if event.type() != QtCore.QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)
        if not isinstance(event, QtGui.QKeyEvent):
            return super().eventFilter(watched, event)
        if not self._is_event_from_this_window(watched):
            return super().eventFilter(watched, event)
        if isinstance(QtWidgets.QApplication.focusWidget(), QtWidgets.QLineEdit):
            return super().eventFilter(watched, event)
        if self._handle_playback_shortcut(event.key()):
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        if self._handle_playback_shortcut(event.key()):
            return
        super().keyPressEvent(event)

    def _is_event_from_this_window(self, watched: QtCore.QObject) -> bool:
        if watched is self:
            return True
        if not isinstance(watched, QtWidgets.QWidget):
            return False
        return watched.window() is self or self.isAncestorOf(watched)

    def _handle_playback_shortcut(self, key: int) -> bool:
        if self.loaded_csv_path is None:
            return False
        if key == QtCore.Qt.Key.Key_Space:
            self._toggle_playback()
            return True
        if key == QtCore.Qt.Key.Key_Left:
            self.seek_to_time_ms(self.playback_state.current_time_ms - 500)
            return True
        if key == QtCore.Qt.Key.Key_Right:
            self.seek_to_time_ms(self.playback_state.current_time_ms + 500)
            return True
        return False

    def capture_project_state(
        self,
        *,
        csv_path: str | Path | None = None,
        active_profile: str | None = None,
    ) -> ProjectState:
        profile = self.active_profile if active_profile is None else active_profile
        self.active_profile = profile
        return ProjectState(
            csv_path=None if csv_path is None else Path(csv_path),
            active_profile=profile,
            channel_mappings=dict(self.channel_mappings),
            derived_channel_settings=dict(self.derived_channel_settings),
            open_windows=tuple(self._capture_window_state()),
            selected_channels=tuple(self.selected_channels),
            playback_seconds=self.playback_state.current_seconds,
            vehicle_model_path=self.vehicle_model_path,
            preset_tab_order=tuple(
                self.preset_tabs.tabText(index) for index in range(self.preset_tabs.count())
            ),
            active_tab_index=self.preset_tabs.currentIndex(),
        )

    def queue_project_restore_after_data_load(self, state: ProjectState) -> None:
        self.pending_project_state = state

    def complete_data_load_for_pending_project(self, csv_path: str | Path) -> bool:
        self.loaded_csv_path = Path(csv_path)
        if self.pending_project_state is None:
            return False
        expected = self.pending_project_state.csv_path
        if expected is not None and Path(expected) != self.loaded_csv_path:
            return False

        state = self.pending_project_state
        self.pending_project_state = None
        self.restore_project_state(state)
        return True

    def restore_project_state(self, state: ProjectState) -> None:
        self.active_profile = state.active_profile
        self.channel_mappings = dict(state.channel_mappings)
        self.derived_channel_settings = dict(state.derived_channel_settings)
        self.selected_channels = list(state.selected_channels)
        if state.vehicle_model_path is not None:
            self.load_vehicle_model_path(state.vehicle_model_path)
        self._restore_preset_tabs(state)
        self._clear_workspace()

        for window_state in state.open_windows:
            sub_window = self.add_analysis_window(window_state.title)
            sub_window.move(window_state.x, window_state.y)
            sub_window.resize(window_state.width, window_state.height)

        self.set_playback_seconds(state.playback_seconds)

    def _capture_window_state(self) -> list[WindowState]:
        windows: list[WindowState] = []
        for sub_window in self.workspace.subWindowList():
            position = sub_window.pos()
            size = sub_window.size()
            windows.append(
                WindowState(
                    title=sub_window.windowTitle(),
                    x=position.x(),
                    y=position.y(),
                    width=size.width(),
                    height=size.height(),
                )
            )
        return windows

    def _restore_preset_tabs(self, state: ProjectState) -> None:
        if not state.preset_tab_order:
            return
        while self.preset_tabs.count():
            self.preset_tabs.removeTab(0)
        seen = set(state.preset_tab_order)
        for tab_title in state.preset_tab_order:
            self.preset_tabs.addTab(tab_title)
        for tab_title in DEFAULT_PRESET_TABS:
            if tab_title not in seen:
                self.preset_tabs.addTab(tab_title)
        if self.preset_tabs.count():
            self.preset_tabs.setCurrentIndex(
                min(max(state.active_tab_index, 0), self.preset_tabs.count() - 1)
            )

    def _clear_workspace(self) -> None:
        for sub_window in list(self.workspace.subWindowList()):
            widget = sub_window.widget()
            if widget is not None:
                _dispose_widget(widget)
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            self.workspace.removeSubWindow(sub_window)
            sub_window.hide()
            sub_window.deleteLater()

    def add_analysis_window(self, title: str) -> QtWidgets.QMdiSubWindow:
        if title == "Time-Series Graph":
            widget = self._build_time_series_window()
        elif title == "Data Analysis":
            widget = self._build_data_analysis_window()
        elif title == "Documents":
            widget = self._build_documents_window()
        elif title == "G-G Diagram":
            widget = self._build_gg_diagram_window()
        elif title == "GPS Map":
            widget = self._build_gps_map_window()
        elif title == "Current Values Table":
            widget = self._build_current_values_window()
        elif title == "Benchmark Summary":
            widget = BenchmarkSummaryWindow(collect_environment())
        elif title == "3D Vehicle Model":
            widget = self._build_vehicle_model_window()
        else:
            widget = self._build_placeholder_window(title)

        sub_window = self.workspace.addSubWindow(widget)
        sub_window.setWindowTitle(title)
        sub_window.setWindowFlag(QtCore.Qt.WindowType.WindowMinMaxButtonsHint, True)
        sub_window.setWindowFlag(QtCore.Qt.WindowType.WindowCloseButtonHint, True)
        sub_window._overlay_controls_controller = _AnalysisWindowOverlayControls(  # type: ignore[attr-defined]
            sub_window,
            widget,
        )
        sub_window.resize(460, 260)
        sub_window.show()
        self.workspace.setActiveSubWindow(sub_window)
        self._update_properties_for_active_window(sub_window)
        return sub_window

    def _build_time_series_window(self) -> TimeSeriesWindow:
        widget = TimeSeriesWindow(
            self.playback_state,
            line_color=self.visualization_settings.graph_line_color,
            line_width=self.visualization_settings.graph_line_width,
        )
        x_values = [
            self.playback_state.seconds_at(index)
            for index in range(self.playback_state.sample_count)
        ]
        widget.set_series(
            {
                "RPM": (x_values, self.sensor_series["RPM"]),
                "TPS_percent": (x_values, self.sensor_series["TPS_percent"]),
            }
        )
        return widget

    def _build_gg_diagram_window(self) -> GGDiagramWindow:
        widget = GGDiagramWindow(self.playback_state)
        widget.set_limit_circle_radius(self.visualization_settings.gg_limit_radius)
        widget.set_acceleration(
            ax_corrected=self.sensor_series["AX_CORRECTED_G"],
            ay_corrected=self.sensor_series["AY_CORRECTED_G"],
        )
        return widget

    def _build_gps_map_window(self) -> GPSMapWindow:
        widget = GPSMapWindow(self.playback_state, tile_provider=self._map_tile_provider)
        widget.set_map_background_enabled(
            self.visualization_settings.gps_map_background_enabled
        )
        if self.gps_route_layers:
            widget.set_route_layers(
                tuple(self.gps_route_layers.values()),
                active_route_name=self.active_gps_route_name,
            )
        else:
            widget.set_track(
                latitude=self.sensor_series["latitude"],
                longitude=self.sensor_series["longitude"],
            )
        return widget

    def _build_vehicle_model_window(self) -> VehicleModelWindow:
        return VehicleModelWindow(self.vehicle_model_info)

    def _build_current_values_window(self) -> CurrentValuesWindow:
        return CurrentValuesWindow(
            self.playback_state,
            {
                "RPM": self.sensor_series["RPM"],
                "TPS_percent": self.sensor_series["TPS_percent"],
                "AX_CORRECTED_G": self.sensor_series["AX_CORRECTED_G"],
                "AY_CORRECTED_G": self.sensor_series["AY_CORRECTED_G"],
            },
        )

    def _build_data_analysis_window(self) -> DataAnalysisWindow:
        session_name = self.loaded_csv_path.name if self.loaded_csv_path is not None else "No CSV"
        return DataAnalysisWindow(
            session_name=session_name,
            row_count=self.session_row_count,
            duration_ms=self.playback_state.total_time_ms,
            sampling_interval_ms=self.session_sampling_interval_ms,
            sensor_series=self.sensor_series,
            events=self.playback_events,
        )

    def _build_documents_window(self) -> DocumentsWindow:
        return DocumentsWindow(_project_document_paths())

    def _build_placeholder_window(self, title: str) -> QtWidgets.QFrame:
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
        return widget

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
                if action_title == "Open CSV":
                    action.triggered.connect(self._open_csv_dialog)
                elif action_title == "Open Project":
                    action.triggered.connect(self._open_project_dialog)
                elif action_title == "Save Project":
                    action.triggered.connect(self._save_project_dialog)

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
        self.workspace.subWindowActivated.connect(self._update_properties_for_active_window)

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
        self._apply_sidebar_settings()

    def _build_right_properties_panel(self) -> None:
        self.properties_panel = QtWidgets.QDockWidget("속성", self)
        self.properties_panel.setObjectName("propertiesPanel")
        self.properties_panel.setAllowedAreas(QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.properties_selection_label = QtWidgets.QLabel("선택 창: -")
        self.properties_selection_label.setObjectName("propertiesSelectionLabel")
        self.properties_stack = QtWidgets.QStackedWidget()
        self.properties_stack.setObjectName("propertiesStack")

        self.gps_map_background_checkbox = QtWidgets.QCheckBox("실제 지도 배경")
        self.gps_map_background_checkbox.setObjectName("gpsMapBackgroundCheckbox")
        self.gps_map_background_checkbox.setChecked(
            self.visualization_settings.gps_map_background_enabled
        )
        self.gps_map_background_checkbox.toggled.connect(
            self._update_visualization_settings_from_controls
        )
        self.graph_line_color_combo = QtWidgets.QComboBox()
        self.graph_line_color_combo.setObjectName("graphLineColorCombo")
        self.graph_line_color_combo.addItems(("Default", "Yellow", "Blue", "Green", "Red"))
        self.graph_line_color_combo.currentTextChanged.connect(
            self._update_visualization_settings_from_controls
        )
        self.graph_line_width_spin = QtWidgets.QDoubleSpinBox()
        self.graph_line_width_spin.setObjectName("graphLineWidthSpin")
        self.graph_line_width_spin.setRange(0.5, 5.0)
        self.graph_line_width_spin.setSingleStep(0.25)
        self.graph_line_width_spin.setDecimals(2)
        self.graph_line_width_spin.setValue(self.visualization_settings.graph_line_width)
        self.graph_line_width_spin.valueChanged.connect(
            self._update_visualization_settings_from_controls
        )
        self.gg_limit_radius_spin = QtWidgets.QDoubleSpinBox()
        self.gg_limit_radius_spin.setObjectName("ggLimitRadiusSpin")
        self.gg_limit_radius_spin.setRange(0.5, 5.0)
        self.gg_limit_radius_spin.setSingleStep(0.25)
        self.gg_limit_radius_spin.setDecimals(2)
        self.gg_limit_radius_spin.setSuffix(" G")
        self.gg_limit_radius_spin.setValue(self.visualization_settings.gg_limit_radius)
        self.gg_limit_radius_spin.valueChanged.connect(
            self._update_visualization_settings_from_controls
        )

        self.sidebar_search_visible_checkbox = QtWidgets.QCheckBox("검색창 표시")
        self.sidebar_search_visible_checkbox.setObjectName("sidebarSearchVisibleCheckbox")
        self.sidebar_search_visible_checkbox.setChecked(self.sidebar_settings.search_visible)
        self.sidebar_search_visible_checkbox.toggled.connect(
            self._update_sidebar_settings_from_controls
        )
        self.sidebar_add_button_visible_checkbox = QtWidgets.QCheckBox("추가 버튼 표시")
        self.sidebar_add_button_visible_checkbox.setObjectName("sidebarAddButtonVisibleCheckbox")
        self.sidebar_add_button_visible_checkbox.setChecked(
            self.sidebar_settings.add_button_visible
        )
        self.sidebar_add_button_visible_checkbox.toggled.connect(
            self._update_sidebar_settings_from_controls
        )
        self.sidebar_sort_combo = QtWidgets.QComboBox()
        self.sidebar_sort_combo.setObjectName("sidebarSortCombo")
        self.sidebar_sort_combo.addItems(("Default", "A-Z"))
        self.sidebar_sort_combo.setCurrentText(self.sidebar_settings.sort_mode)
        self.sidebar_sort_combo.currentTextChanged.connect(
            self._update_sidebar_settings_from_controls
        )
        self.sidebar_density_combo = QtWidgets.QComboBox()
        self.sidebar_density_combo.setObjectName("sidebarDensityCombo")
        self.sidebar_density_combo.addItems(("Comfortable", "Compact"))
        self.sidebar_density_combo.setCurrentText(self.sidebar_settings.density)
        self.sidebar_density_combo.currentTextChanged.connect(
            self._update_sidebar_settings_from_controls
        )
        self.sidebar_width_spin = QtWidgets.QSpinBox()
        self.sidebar_width_spin.setObjectName("sidebarWidthSpin")
        self.sidebar_width_spin.setRange(180, 420)
        self.sidebar_width_spin.setSingleStep(10)
        self.sidebar_width_spin.setSuffix(" px")
        self.sidebar_width_spin.setValue(self.sidebar_settings.width_px)
        self.sidebar_width_spin.valueChanged.connect(
            self._update_sidebar_settings_from_controls
        )

        self.vehicle_model_path_edit = QtWidgets.QLineEdit(str(self.vehicle_model_path))
        self.vehicle_model_path_edit.setObjectName("vehicleModelPathEdit")
        self.vehicle_model_path_edit.setReadOnly(True)
        self.vehicle_model_load_button = QtWidgets.QPushButton("Load GLB...")
        self.vehicle_model_load_button.setObjectName("vehicleModelLoadButton")
        self.vehicle_model_load_button.clicked.connect(self._open_vehicle_model_dialog)

        self.workspace_properties_page = self._make_properties_page(
            "workspacePropertiesPage",
            (
                ("좌측 검색", self.sidebar_search_visible_checkbox),
                ("좌측 추가", self.sidebar_add_button_visible_checkbox),
                ("좌측 정렬", self.sidebar_sort_combo),
                ("좌측 밀도", self.sidebar_density_combo),
                ("좌측 폭", self.sidebar_width_spin),
            ),
        )
        self.time_series_properties_page = self._make_properties_page(
            "timeSeriesPropertiesPage",
            (
                ("그래프 모드", QtWidgets.QLabel("Overlay")),
                ("단위", QtWidgets.QLabel("프로필 기본값")),
                ("선 색상", self.graph_line_color_combo),
                ("선 굵기", self.graph_line_width_spin),
            ),
        )
        self.gps_properties_page = self._make_properties_page(
            "gpsPropertiesPage",
            (("GPS", self.gps_map_background_checkbox),),
        )
        self.gg_properties_page = self._make_properties_page(
            "ggPropertiesPage",
            (("G-G 한계원", self.gg_limit_radius_spin),),
        )
        self.vehicle_model_properties_page = self._make_properties_page(
            "vehicleModelPropertiesPage",
            (
                ("Vehicle GLB", self.vehicle_model_path_edit),
                ("", self.vehicle_model_load_button),
            ),
        )
        self.read_only_properties_label = QtWidgets.QLabel("선택한 창의 추가 설정이 없습니다.")
        self.read_only_properties_label.setWordWrap(True)
        self.read_only_properties_page = self._make_properties_page(
            "readOnlyPropertiesPage",
            (("정보", self.read_only_properties_label),),
        )

        for page in (
            self.workspace_properties_page,
            self.time_series_properties_page,
            self.gps_properties_page,
            self.gg_properties_page,
            self.vehicle_model_properties_page,
            self.read_only_properties_page,
        ):
            self.properties_stack.addWidget(page)

        layout.addWidget(self.properties_selection_label)
        layout.addWidget(self.properties_stack, 1)

        self.properties_panel.setWidget(content)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.properties_panel)
        self._update_properties_for_active_window()

    def _make_properties_page(
        self,
        object_name: str,
        rows: tuple[tuple[str, QtWidgets.QWidget], ...],
    ) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setObjectName(object_name)
        form = QtWidgets.QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        for label, widget in rows:
            form.addRow(label, widget)
        return page

    def _update_properties_for_active_window(
        self,
        sub_window: QtWidgets.QMdiSubWindow | None = None,
    ) -> None:
        if not hasattr(self, "properties_stack"):
            return

        if sub_window is None:
            sub_window = self.workspace.activeSubWindow()
        if sub_window is not None and not shiboken6.isValid(sub_window):
            sub_window = None

        selected_title = "작업공간"
        selected_page = self.workspace_properties_page
        try:
            selected_widget = None if sub_window is None else sub_window.widget()
        except RuntimeError:
            selected_widget = None
        if selected_widget is not None:
            selected_title = sub_window.windowTitle()
            if isinstance(selected_widget, TimeSeriesWindow):
                selected_page = self.time_series_properties_page
            elif isinstance(selected_widget, GPSMapWindow):
                selected_page = self.gps_properties_page
            elif isinstance(selected_widget, GGDiagramWindow):
                selected_page = self.gg_properties_page
            elif isinstance(selected_widget, VehicleModelWindow):
                selected_page = self.vehicle_model_properties_page
            else:
                selected_page = self.read_only_properties_page

        self.properties_selection_label.setText(f"선택 창: {selected_title}")
        self.properties_stack.setCurrentWidget(selected_page)

    def _update_visualization_settings_from_controls(self, *_args: object) -> None:
        self.visualization_settings = VisualizationSettings(
            gps_map_background_enabled=self.gps_map_background_checkbox.isChecked(),
            graph_line_color=_graph_line_color(self.graph_line_color_combo.currentText()),
            graph_line_width=float(self.graph_line_width_spin.value()),
            gg_limit_radius=float(self.gg_limit_radius_spin.value()),
        )
        self._apply_visualization_settings_to_open_windows()

    def _update_sidebar_settings_from_controls(self, *_args: object) -> None:
        self.sidebar_settings = SidebarSettings(
            search_visible=self.sidebar_search_visible_checkbox.isChecked(),
            add_button_visible=self.sidebar_add_button_visible_checkbox.isChecked(),
            sort_mode=self.sidebar_sort_combo.currentText(),
            density=self.sidebar_density_combo.currentText(),
            width_px=int(self.sidebar_width_spin.value()),
        )
        self._apply_sidebar_settings()

    def _apply_sidebar_settings(self) -> None:
        if hasattr(self, "sidebar_search"):
            self.sidebar_search.setVisible(self.sidebar_settings.search_visible)
            if not self.sidebar_settings.search_visible and self.sidebar_search.text():
                self.sidebar_search.clear()

        if hasattr(self, "add_window_button"):
            self.add_window_button.setVisible(self.sidebar_settings.add_button_visible)

        if hasattr(self, "analysis_list"):
            self.analysis_list.setSpacing(
                2 if self.sidebar_settings.density == "Compact" else 8
            )
            self._filter_analysis_items(self.sidebar_search.text())

        if hasattr(self, "left_sidebar"):
            self.left_sidebar.setMinimumWidth(self.sidebar_settings.width_px)
            self.left_sidebar.resize(
                self.sidebar_settings.width_px,
                max(1, self.left_sidebar.height()),
            )

    def _apply_visualization_settings_to_open_windows(self) -> None:
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, TimeSeriesWindow):
                widget.set_graph_style(
                    line_color=self.visualization_settings.graph_line_color,
                    line_width=self.visualization_settings.graph_line_width,
                )
            elif isinstance(widget, GPSMapWindow):
                widget.set_map_background_enabled(
                    self.visualization_settings.gps_map_background_enabled
                )
            elif isinstance(widget, GGDiagramWindow):
                widget.set_limit_circle_radius(self.visualization_settings.gg_limit_radius)

    def _build_playback_dock(self) -> None:
        self.playback_dock = QtWidgets.QDockWidget("CSV Playback", self)
        self.playback_dock.setObjectName("playbackDock")
        self.playback_dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
        self.playback_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

        content = QtWidgets.QFrame()
        content.setObjectName("playbackDockContent")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        status_row = QtWidgets.QHBoxLayout()
        self.playback_file_label = QtWidgets.QLabel()
        self.playback_file_label.setObjectName("playbackFileLabel")
        self.playback_row_label = QtWidgets.QLabel()
        self.playback_row_label.setObjectName("playbackRowLabel")
        self.playback_interval_label = QtWidgets.QLabel()
        self.playback_interval_label.setObjectName("playbackIntervalLabel")
        self.playback_event_count_label = QtWidgets.QLabel()
        self.playback_event_count_label.setObjectName("playbackEventCountLabel")
        self.current_time_label = QtWidgets.QLabel()
        self.current_time_label.setObjectName("playbackCurrentTimeLabel")
        self.current_row_label = QtWidgets.QLabel()
        self.current_row_label.setObjectName("playbackCurrentRowLabel")
        for label in (
            self.playback_file_label,
            self.playback_row_label,
            self.playback_interval_label,
            self.playback_event_count_label,
            self.current_time_label,
            self.current_row_label,
        ):
            status_row.addWidget(label)
        status_row.addStretch(1)

        control_row = QtWidgets.QHBoxLayout()
        control_row.setSpacing(6)
        self.home_button = QtWidgets.QPushButton("처음")
        self.home_button.setObjectName("playbackHomeButton")
        self.home_button.clicked.connect(lambda: self.seek_to_time_ms(0))
        self.end_button = QtWidgets.QPushButton("끝")
        self.end_button.setObjectName("playbackEndButton")
        self.end_button.clicked.connect(
            lambda: self.seek_to_time_ms(self.playback_state.total_time_ms)
        )
        self.prev_event_button = QtWidgets.QPushButton("이전 이벤트")
        self.prev_event_button.setObjectName("playbackPrevEventButton")
        self.prev_event_button.clicked.connect(self.seek_previous_event)
        self.play_pause_button = QtWidgets.QPushButton("Play")
        self.play_pause_button.setObjectName("playbackPlayPauseButton")
        self.play_pause_button.clicked.connect(self._toggle_playback)
        self.next_event_button = QtWidgets.QPushButton("다음 이벤트")
        self.next_event_button.setObjectName("playbackNextEventButton")
        self.next_event_button.clicked.connect(self.seek_next_event)
        self.speed_combo = QtWidgets.QComboBox()
        self.speed_combo.setObjectName("playbackSpeedCombo")
        self.speed_combo.addItems(("0.25x", "0.5x", "1x", "2x", "4x"))
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._set_playback_speed_from_text)
        for widget in (
            self.home_button,
            self.end_button,
            self.prev_event_button,
            self.play_pause_button,
            self.next_event_button,
            self.speed_combo,
        ):
            control_row.addWidget(widget)

        self.timeline_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.timeline_slider.setObjectName("playbackTimelineSlider")
        self.timeline_slider.setRange(0, self.playback_state.total_time_ms)
        self.timeline_slider.valueChanged.connect(self.seek_to_time_ms)
        control_row.addWidget(self.timeline_slider, 1)

        lower_row = QtWidgets.QHBoxLayout()
        self.event_marker_list = QtWidgets.QListWidget()
        self.event_marker_list.setObjectName("eventMarkerList")
        self.event_marker_list.setMaximumHeight(74)
        self.event_marker_list.currentItemChanged.connect(self._seek_to_event_item)
        self.sensor_card_container = QtWidgets.QWidget()
        self.sensor_card_container.setObjectName("sensorCardContainer")
        self.sensor_card_layout = QtWidgets.QHBoxLayout(self.sensor_card_container)
        self.sensor_card_layout.setContentsMargins(0, 0, 0, 0)
        self.sensor_card_layout.setSpacing(6)
        self.sensor_card_value_labels: dict[str, QtWidgets.QLabel] = {}
        self._build_sensor_cards()
        lower_row.addWidget(self.event_marker_list, 1)
        lower_row.addWidget(self.sensor_card_container, 2)

        self.playback_warning_label = QtWidgets.QLabel()
        self.playback_warning_label.setObjectName("playbackWarningLabel")

        layout.addLayout(status_row)
        layout.addLayout(control_row)
        layout.addLayout(lower_row)
        layout.addWidget(self.playback_warning_label)
        self.playback_dock.setWidget(content)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.playback_dock)

    def _build_sensor_cards(self) -> None:
        for channel_id in (
            "RPM",
            "VSS / GPS speed",
            "Gear",
            "Battery voltage",
            "TPS",
            "ax",
            "ay",
            "roll rate",
            "pitch rate",
            "yaw rate",
        ):
            card = QtWidgets.QFrame()
            card.setObjectName("sensorCard")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            title = QtWidgets.QLabel(channel_id)
            title.setObjectName("sensorCardTitle")
            value = QtWidgets.QLabel("-")
            value.setObjectName("sensorCardValue")
            card_layout.addWidget(title)
            card_layout.addWidget(value)
            self.sensor_card_layout.addWidget(card)
            self.sensor_card_value_labels[channel_id] = value

    def _build_bottom_timeline(self) -> None:
        self.timeline_status = QtWidgets.QLabel("시간 0.000 s | 샘플 0")
        self.timeline_status.setObjectName("timelineStatus")
        self.statusBar().addPermanentWidget(self.timeline_status, 1)
        self.statusBar().showMessage("CSV를 열어 분석을 시작하세요.")

    def _filter_analysis_items(self, text: str) -> None:
        query = text.strip().lower() if self.sidebar_settings.search_visible else ""
        items = [
            item
            for item in self._all_analysis_items
            if not query or query in item.lower()
        ]
        if self.sidebar_settings.sort_mode == "A-Z":
            items = sorted(items)

        self.analysis_list.clear()
        for item in items:
            self.analysis_list.addItem(item)

    def _add_selected_analysis_window(self) -> None:
        item = self.analysis_list.currentItem()
        if item is None and self.analysis_list.count() > 0:
            item = self.analysis_list.item(0)
        if item is not None:
            self.add_analysis_window(item.text())

    def _open_csv_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open CSV",
            str(Path.cwd()),
            "CSV files (*.csv);;All files (*.*)",
        )
        if path:
            self.load_csv_session(Path(path))

    def _open_vehicle_model_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Vehicle GLB",
            str(self.vehicle_model_path.parent),
            "GLB files (*.glb);;All files (*.*)",
        )
        if path:
            self.load_vehicle_model_path(Path(path))

    def load_vehicle_model_path(self, model_path: Path) -> bool:
        try:
            model_info = load_glb_info(model_path)
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(f"Vehicle model load failed: {exc}")
            return False

        self.vehicle_model_path = model_path
        self.vehicle_model_info = model_info
        if hasattr(self, "vehicle_model_path_edit"):
            self.vehicle_model_path_edit.setText(str(model_path))

        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, VehicleModelWindow):
                widget.set_model_info(model_info)

        self.statusBar().showMessage(f"Vehicle model loaded: {model_path.name}")
        return True

    def _open_project_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(Path.cwd()),
            "MF Log Project (*.mflogproj *.json);;All files (*.*)",
        )
        if path:
            self.open_project_file(Path(path))

    def _save_project_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Project",
            str(Path.cwd() / "session.mflogproj"),
            "MF Log Project (*.mflogproj);;All files (*.*)",
        )
        if path:
            self.save_project_file(Path(path))

    def save_project_file(self, project_path: Path) -> ProjectState:
        state = self.capture_project_state(csv_path=self.loaded_csv_path)
        save_project_state(project_path, state)
        self.statusBar().showMessage(f"Project saved: {project_path.name}")
        return state

    def open_project_file(self, project_path: Path) -> bool:
        state = load_project_state(project_path)
        loaded_csv = False
        if state.csv_path is not None and state.csv_path.exists():
            self.load_csv_session(state.csv_path)
            loaded_csv = True
        else:
            self.queue_project_restore_after_data_load(state)
        self.restore_project_state(state)
        if not loaded_csv and state.csv_path is not None:
            self.playback_warning_label.setText(
                f"Referenced CSV is missing: {state.csv_path}"
            )
        self.statusBar().showMessage(f"Project opened: {project_path.name}")
        return loaded_csv

    def load_demo_session(self) -> None:
        sample_count = 101
        self._configure_playback_session(
            csv_path=Path("prototype-demo.csv"),
            timestamps=[index / 10 for index in range(sample_count)],
            sensor_series=_demo_sensor_series(sample_count),
            events=_demo_playback_markers(),
            row_count=sample_count,
            sampling_interval_ms=100,
        )

    def load_csv_session(self, csv_path: Path, *, autosave_warning: str = "") -> None:
        result = load_csv(csv_path, CsvLoadOptions(numeric_probe=False))
        timestamps = _timestamps_from_store(result.store)
        sample_count = len(timestamps)
        warning = _join_warnings(
            autosave_warning,
            _csv_diagnostic_warning(
                malformed_count=len(result.malformed_rows),
                numeric_error_count=len(result.numeric_errors),
            ),
        )
        self._configure_playback_session(
            csv_path=csv_path,
            timestamps=timestamps,
            sensor_series=_sensor_series_from_store(result.store, sample_count),
            events=_detect_playback_markers(result.store, timestamps),
            row_count=result.store.row_count,
            sampling_interval_ms=_estimate_sampling_interval_ms(timestamps),
            autosave_warning=warning,
        )

    def _configure_playback_session(
        self,
        *,
        csv_path: Path,
        timestamps: list[float],
        sensor_series: dict[str, list[float]],
        events: tuple[PlaybackMarker, ...],
        row_count: int,
        sampling_interval_ms: int,
        autosave_warning: str = "",
    ) -> None:
        window_states = self._capture_window_state()
        if self.playback_state.is_playing:
            self.playback_state.pause()
        self.playback_timer.stop()
        self._unsubscribe_playback_status()
        self.playback_state = PlaybackState(timestamps)
        self._unsubscribe_playback_status = self.playback_state.subscribe(
            self._handle_playback_event
        )
        self.sensor_series = sensor_series
        self._remember_gps_route(csv_path, sensor_series)
        self.playback_events = events
        self.session_sampling_interval_ms = sampling_interval_ms
        self.set_csv_session(csv_path, row_count=row_count, autosave_warning=autosave_warning)
        self._restore_analysis_windows(window_states)

    def _remember_gps_route(self, csv_path: Path, sensor_series: dict[str, list[float]]) -> None:
        route_name = csv_path.name
        self.gps_route_layers[route_name] = GPSRouteLayer(
            name=route_name,
            latitude=tuple(sensor_series.get("latitude", [])),
            longitude=tuple(sensor_series.get("longitude", [])),
        )
        self.active_gps_route_name = route_name

    def _restore_analysis_windows(self, window_states: list[WindowState]) -> None:
        if not window_states:
            return
        self._clear_workspace()
        for window_state in window_states:
            sub_window = self.add_analysis_window(window_state.title)
            sub_window.move(window_state.x, window_state.y)
            sub_window.resize(window_state.width, window_state.height)

    def _toggle_playback(self) -> None:
        if self.playback_state.is_playing:
            self.playback_state.pause()
            self.playback_timer.stop()
        else:
            self.playback_state.play()
            self._playback_elapsed.restart()
            self.playback_timer.start()
        self._update_playback_dock_status()

    def _tick_playback_timer(self) -> None:
        if not self.playback_state.is_playing:
            self.playback_timer.stop()
            return
        self.advance_playback(self._playback_elapsed.restart())

    def advance_playback(self, elapsed_ms: int) -> None:
        if elapsed_ms <= 0:
            return
        target_ms = self.playback_state.current_time_ms + round(
            elapsed_ms * self.playback_state.playback_speed
        )
        if target_ms >= self.playback_state.total_time_ms:
            self.seek_to_time_ms(self.playback_state.total_time_ms)
            self.playback_state.pause()
            self.playback_timer.stop()
            self._update_playback_dock_status()
            return
        self.seek_to_time_ms(target_ms)

    def seek_to_time_ms(self, time_ms: int) -> None:
        self.playback_state.set_time_ms(time_ms)
        self._update_playback_dock_status()
        self._update_timeline_status()

    def seek_previous_event(self) -> None:
        if not self.playback_events:
            return
        current = self.playback_state.current_time_ms
        previous = [event for event in self.playback_events if event.time_ms < current]
        target = previous[-1] if previous else self.playback_events[0]
        self.seek_to_time_ms(target.time_ms)

    def seek_next_event(self) -> None:
        if not self.playback_events:
            return
        current = self.playback_state.current_time_ms
        next_events = [event for event in self.playback_events if event.time_ms > current]
        target = next_events[0] if next_events else self.playback_events[-1]
        self.seek_to_time_ms(target.time_ms)

    def _seek_to_event_item(
        self,
        current: QtWidgets.QListWidgetItem | None,
        _previous: QtWidgets.QListWidgetItem | None = None,
    ) -> None:
        if self._syncing_event_marker_selection:
            return
        if current is None:
            return
        self.seek_to_time_ms(int(current.data(QtCore.Qt.ItemDataRole.UserRole)))

    def _set_playback_speed_from_text(self, text: str) -> None:
        self.playback_state.set_speed(float(text.removesuffix("x")))
        self._update_playback_dock_status()

    def set_csv_session(self, csv_path: Path, *, row_count: int, autosave_warning: str = "") -> None:
        self.loaded_csv_path = csv_path
        self.session_row_count = row_count
        self.playback_warning_label.setText(autosave_warning)
        self._populate_event_markers()
        self._set_playback_controls_enabled(True)
        self._update_playback_dock_status()

    def clear_csv_session(self) -> None:
        self.loaded_csv_path = None
        if self.playback_state.is_playing:
            self.playback_state.pause()
        self.playback_timer.stop()
        self._set_playback_controls_enabled(False)
        self.playback_file_label.setText("CSV를 업로드하면 재생할 수 있습니다.")
        self.playback_row_label.setText("Rows: -")
        self.playback_interval_label.setText("Sample: -")
        self.playback_event_count_label.setText("Events: -")
        self.current_time_label.setText("- / -")
        self.current_row_label.setText("Row: -")

    def sensor_card_value(self, channel_id: str) -> str:
        return self.sensor_card_value_labels[channel_id].text()

    def _set_playback_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.home_button,
            self.end_button,
            self.prev_event_button,
            self.play_pause_button,
            self.next_event_button,
            self.speed_combo,
            self.timeline_slider,
            self.event_marker_list,
        ):
            widget.setEnabled(enabled)

    def _populate_event_markers(self) -> None:
        self._syncing_event_marker_selection = True
        try:
            self.event_marker_list.clear()
            for event in self.playback_events:
                item = QtWidgets.QListWidgetItem(
                    f"{event.severity.upper()} {event.name} @ {_format_seconds(event.time_ms)}"
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, event.time_ms)
                item.setToolTip(
                    f"{event.name}\n"
                    f"time: {_format_seconds(event.time_ms)}\n"
                    f"sensor: {event.sensor}\n"
                    f"value: {event.value:g}\n"
                    f"condition: {event.condition}"
                )
                item.setForeground(QtGui.QBrush(_event_color(event.severity)))
                item.setBackground(QtGui.QBrush(QtGui.QColor("#2f3338")))
                self.event_marker_list.addItem(item)
        finally:
            self._syncing_event_marker_selection = False

    def _update_playback_dock_status(self) -> None:
        if not hasattr(self, "timeline_slider"):
            return
        current = self.playback_state.current_sample
        current_ms = self.playback_state.current_time_ms
        total_ms = self.playback_state.total_time_ms
        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setRange(0, total_ms)
        self.timeline_slider.setValue(current_ms)
        self.timeline_slider.blockSignals(False)
        if self.loaded_csv_path is not None:
            self.playback_file_label.setText(self.loaded_csv_path.name)
        self.playback_row_label.setText(f"Rows: {self.session_row_count}")
        self.playback_interval_label.setText(f"Sample: {self.session_sampling_interval_ms} ms")
        self.playback_event_count_label.setText(f"Events: {len(self.playback_events)}")
        self.current_time_label.setText(f"{_format_seconds(current_ms)} / {_format_seconds(total_ms)}")
        self.current_row_label.setText(f"Row: {current}")
        self.play_pause_button.setText("Pause" if self.playback_state.is_playing else "Play")
        self._highlight_nearest_event(current_ms)
        self._update_sensor_cards(current)

    def _update_sensor_cards(self, sample_index: int) -> None:
        for channel_id, label in self.sensor_card_value_labels.items():
            values = self.sensor_series[channel_id]
            value = values[min(max(sample_index, 0), len(values) - 1)]
            if channel_id == "Gear":
                label.setText(f"{round(value):.0f}")
            else:
                label.setText(f"{value:.3f}")
            if _is_abnormal_sensor_value(channel_id, value):
                label.setStyleSheet("color: #ec7063; font-weight: 700;")
            else:
                label.setStyleSheet("")

    def _highlight_nearest_event(self, current_ms: int) -> None:
        if self.event_marker_list.count() == 0:
            return
        nearest_row = min(
            range(self.event_marker_list.count()),
            key=lambda row: abs(
                int(self.event_marker_list.item(row).data(QtCore.Qt.ItemDataRole.UserRole))
                - current_ms
            ),
        )
        self._syncing_event_marker_selection = True
        try:
            for row in range(self.event_marker_list.count()):
                item = self.event_marker_list.item(row)
                color = item.foreground().color() if row == nearest_row else QtGui.QColor("#2f3338")
                self.event_marker_list.item(row).setBackground(QtGui.QBrush(color))
            self.event_marker_list.setCurrentRow(nearest_row)
        finally:
            self._syncing_event_marker_selection = False

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
            QFrame#playbackDockContent, QFrame#sensorCard {
                background: #171a1d;
                border: 1px solid #3a4046;
            }
            QLabel#sensorCardTitle {
                color: #f4c95d;
                font-weight: 700;
            }
            QLabel#sensorCardValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
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


def _demo_sensor_series(sample_count: int) -> dict[str, list[float]]:
    return {
        "RPM": [2200.0 + index * 35.0 for index in range(sample_count)],
        "GPS speed": [40.0 + (index % 50) * 1.7 for index in range(sample_count)],
        "VSS / GPS speed": [40.0 + (index % 50) * 1.7 for index in range(sample_count)],
        "Gear": [float(1 + (index // 20) % 5) for index in range(sample_count)],
        "Battery voltage": [13.8 + (index % 5) * 0.01 for index in range(sample_count)],
        "TPS": [20.0 + (index % 25) * 2.0 for index in range(sample_count)],
        "TPS_percent": [20.0 + (index % 25) * 2.0 for index in range(sample_count)],
        "AX_CORRECTED_G": [-0.4 + index * 0.008 for index in range(sample_count)],
        "AY_CORRECTED_G": [0.25 if index % 2 == 0 else -0.25 for index in range(sample_count)],
        "ax": [-0.4 + index * 0.008 for index in range(sample_count)],
        "ay": [0.25 if index % 2 == 0 else -0.25 for index in range(sample_count)],
        "roll rate": [index * 0.05 for index in range(sample_count)],
        "pitch rate": [index * -0.03 for index in range(sample_count)],
        "yaw rate": [index * 0.1 for index in range(sample_count)],
        "latitude": [37.0 + index * 0.00001 for index in range(sample_count)],
        "longitude": [127.0 + index * 0.000015 for index in range(sample_count)],
    }


def _demo_playback_markers() -> tuple[PlaybackMarker, ...]:
    return (
        PlaybackMarker("GPS speed dip", 2500, "info", "GPS speed", 82.5, "speed_delta > 5"),
        PlaybackMarker("Battery warning", 5500, "warning", "Battery voltage", 12.1, "Batt_V < 12.5"),
        PlaybackMarker("DBW tracking risk", 8200, "danger", "DBW_ERROR", 11.0, "abs(error) > 10"),
    )


def _blank_sensor_series(sample_count: int) -> dict[str, list[float]]:
    keys = (
        "RPM",
        "GPS speed",
        "VSS / GPS speed",
        "Gear",
        "Battery voltage",
        "TPS",
        "TPS_percent",
        "AX_CORRECTED_G",
        "AY_CORRECTED_G",
        "ax",
        "ay",
        "roll rate",
        "pitch rate",
        "yaw rate",
        "latitude",
        "longitude",
    )
    return {key: [0.0 for _index in range(sample_count)] for key in keys}


def _sensor_series_from_store(store: ColumnStore, sample_count: int) -> dict[str, list[float]]:
    derived = compute_basic_derived_channels(store)
    gps_speed = _numeric_series(
        store,
        sample_count,
        "GPS_Speed_KPH",
        "VSS_kmh",
        "VSS",
        "GPS speed",
    )
    ax = _derived_or_numeric_series(
        derived,
        "AX_CORRECTED_G",
        store,
        sample_count,
        "AX_CORRECTED_G",
        "AX_RAW_G",
        "ax_g",
        "ax",
    )
    ay = _derived_or_numeric_series(
        derived,
        "AY_CORRECTED_G",
        store,
        sample_count,
        "AY_CORRECTED_G",
        "AY_RAW_G",
        "ay_g",
        "ay",
    )
    return {
        "RPM": _numeric_series(store, sample_count, "RPM"),
        "GPS speed": gps_speed,
        "VSS / GPS speed": gps_speed,
        "Gear": _numeric_series(store, sample_count, "Gear"),
        "Battery voltage": _numeric_series(store, sample_count, "Batt_V", "Battery voltage"),
        "TPS": _numeric_series(store, sample_count, "TPS_percent", "TPS"),
        "TPS_percent": _numeric_series(store, sample_count, "TPS_percent", "TPS"),
        "AX_CORRECTED_G": ax,
        "AY_CORRECTED_G": ay,
        "ax": ax,
        "ay": ay,
        "roll rate": _numeric_series(store, sample_count, "gx_dps", "roll rate"),
        "pitch rate": _numeric_series(store, sample_count, "gy_dps", "pitch rate"),
        "yaw rate": _numeric_series(store, sample_count, "gz_dps", "yaw rate"),
        "latitude": _numeric_series(store, sample_count, "Latitude", "latitude"),
        "longitude": _numeric_series(store, sample_count, "Longitude", "longitude"),
    }


def _derived_or_numeric_series(
    derived: dict[str, list[float | None]],
    channel_id: str,
    store: ColumnStore,
    sample_count: int,
    *candidates: str,
) -> list[float]:
    if channel_id in derived:
        return _float_series(derived[channel_id], sample_count)
    return _numeric_series(store, sample_count, *candidates)


def _float_series(values: Sequence[float | None], sample_count: int) -> list[float]:
    output = [0.0 if value is None else float(value) for value in values[:sample_count]]
    if len(output) < sample_count:
        output.extend(0.0 for _index in range(sample_count - len(output)))
    return output


def _numeric_series(
    store: ColumnStore,
    sample_count: int,
    *candidates: str,
    default: float = 0.0,
) -> list[float]:
    values = _store_values(store, *candidates)
    if values is None:
        return [default for _index in range(sample_count)]
    output = [_to_float(value, default) for value in values[:sample_count]]
    if len(output) < sample_count:
        output.extend(default for _index in range(sample_count - len(output)))
    return output


def _store_values(store: ColumnStore, *candidates: str) -> list[str] | None:
    for candidate in candidates:
        try:
            return list(store.values(candidate))
        except KeyError:
            continue
    return None


def _timestamps_from_store(store: ColumnStore) -> list[float]:
    values = _store_values(store, "TIME", "Timestamp", "time", "timestamp")
    if not values:
        return [0.0]

    timestamps: list[float] = []
    first_numeric: float | None = None
    first_datetime: datetime | None = None
    for value in values:
        parsed_numeric = _parse_float(value)
        if parsed_numeric is not None:
            if first_numeric is None:
                first_numeric = parsed_numeric
            seconds = parsed_numeric - first_numeric
        else:
            parsed_datetime = _parse_datetime(value)
            if parsed_datetime is None:
                seconds = _next_fallback_timestamp(timestamps)
            else:
                if first_datetime is None:
                    first_datetime = parsed_datetime
                seconds = (parsed_datetime - first_datetime).total_seconds()

        if timestamps and seconds < timestamps[-1]:
            seconds = timestamps[-1]
        timestamps.append(max(0.0, seconds))

    return timestamps or [0.0]


def _estimate_sampling_interval_ms(timestamps: list[float]) -> int:
    deltas = [
        right - left
        for left, right in zip(timestamps, timestamps[1:])
        if right > left
    ]
    if not deltas:
        return 0
    sorted_deltas = sorted(deltas)
    return round(sorted_deltas[len(sorted_deltas) // 2] * 1000)


def _detect_playback_markers(
    store: ColumnStore,
    timestamps: list[float],
) -> tuple[PlaybackMarker, ...]:
    sample_count = len(timestamps)
    battery = _numeric_series(store, sample_count, "Batt_V", "Battery voltage")
    ax = _numeric_series(store, sample_count, "AX_RAW_G", "ax_g", "ax")
    ay = _numeric_series(store, sample_count, "AY_RAW_G", "ay_g", "ay")
    markers: list[PlaybackMarker] = []

    battery_index = _first_index(battery, lambda value: value < 12.0)
    if battery_index is not None:
        markers.append(
            PlaybackMarker(
                "Battery low",
                round(timestamps[battery_index] * 1000),
                "warning",
                "Battery voltage",
                battery[battery_index],
                "Batt_V < 12.0",
            )
        )

    acceleration_index = _first_index(
        [max(abs(x), abs(y)) for x, y in zip(ax, ay, strict=True)],
        lambda value: value > 1.0,
    )
    if acceleration_index is not None:
        markers.append(
            PlaybackMarker(
                "G limit exceeded",
                round(timestamps[acceleration_index] * 1000),
                "danger",
                "ax/ay",
                max(abs(ax[acceleration_index]), abs(ay[acceleration_index])),
                "max(abs(ax), abs(ay)) > 1.0",
            )
        )

    return tuple(markers)


def _is_abnormal_sensor_value(channel_id: str, value: float) -> bool:
    if channel_id == "RPM":
        return value > 9000
    if channel_id in {"VSS / GPS speed", "GPS speed"}:
        return value < 0
    if channel_id == "Battery voltage":
        return value < 12.0
    if channel_id == "TPS":
        return value > 90.0
    if channel_id in {"ax", "ay"}:
        return abs(value) > 1.0
    if channel_id in {"roll rate", "pitch rate", "yaw rate"}:
        return abs(value) > 100.0
    return False


def _first_index(values: list[float], predicate: Callable[[float], bool]) -> int | None:
    for index, value in enumerate(values):
        if predicate(value):
            return index
    return None


def _next_fallback_timestamp(timestamps: list[float]) -> float:
    if len(timestamps) >= 2:
        return timestamps[-1] + max(timestamps[-1] - timestamps[-2], 0.001)
    if timestamps:
        return timestamps[-1] + 0.1
    return 0.0


def _parse_float(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _parse_datetime(value: str) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _to_float(value: str, default: float) -> float:
    parsed = _parse_float(value)
    return default if parsed is None else parsed


def _format_seconds(time_ms: int) -> str:
    return f"{time_ms / 1000:.3f} s"


def _csv_diagnostic_warning(*, malformed_count: int, numeric_error_count: int) -> str:
    parts: list[str] = []
    if malformed_count:
        parts.append(f"Malformed rows: {malformed_count}")
    if numeric_error_count:
        parts.append(f"Numeric errors: {numeric_error_count}")
    return ", ".join(parts)


def _join_warnings(*warnings: str) -> str:
    return " | ".join(warning for warning in warnings if warning)


def _event_color(severity: str) -> QtGui.QColor:
    if severity == "danger":
        return QtGui.QColor("#ec7063")
    if severity == "warning":
        return QtGui.QColor("#f4c95d")
    return QtGui.QColor("#5dade2")


def _graph_line_color(name: str) -> str | None:
    return {
        "Yellow": "#f4c95d",
        "Blue": "#5dade2",
        "Green": "#58d68d",
        "Red": "#ec7063",
    }.get(name)


def _object_name(text: str, *, suffix: str) -> str:
    cleaned = "".join(char if char.isalnum() else " " for char in text)
    parts = cleaned.split()
    if not parts:
        return suffix[:1].lower() + suffix[1:]
    first, *rest = parts
    return first[:1].lower() + first[1:] + "".join(part.title() for part in rest) + suffix


def _root_asset_path(name: str) -> Path:
    for root in _asset_roots():
        candidate = root / name
        if candidate.exists():
            return candidate
    return _asset_roots()[-1] / name


def _project_document_paths() -> tuple[Path, ...]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in _asset_roots():
        for pattern in ("*.pdf", "*.glb", "*.md", "*.docx", "*.xlsx"):
            for path in root.glob(pattern):
                resolved = path.resolve()
                if resolved not in seen:
                    candidates.append(path)
                    seen.add(resolved)
        docs_dir = root / "docs"
        if docs_dir.exists():
            for path in docs_dir.glob("*.md"):
                resolved = path.resolve()
                if resolved not in seen:
                    candidates.append(path)
                    seen.add(resolved)
    return tuple(sorted(candidates, key=lambda path: path.name.lower()))


def _asset_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(str(bundle_root)))
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    roots.extend(
        (
            Path.cwd(),
            Path.cwd().parent,
            Path(__file__).resolve().parents[4],
        )
    )
    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            unique_roots.append(root)
            seen.add(resolved)
    return tuple(unique_roots)


def _dispose_widget(widget: QtWidgets.QWidget) -> None:
    dispose = getattr(widget, "dispose", None)
    if callable(dispose):
        dispose()
