from pathlib import Path
import shutil
import sys

from PySide6 import QtCore, QtGui, QtWidgets
import pytest
import shiboken6

from mflog_proto.analysis.event_reviews import EventReviewState
from mflog_proto.analysis.segments import AnalysisSegment
from mflog_proto.persistence.project_state import ProjectState, WindowState
from mflog_proto.ui.main_window import DEFAULT_ANALYSIS_ITEMS, MainWindow, _root_asset_path
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    DataAnalysisWindow,
    DocumentsWindow,
    EventReviewWindow,
    ExportReportWindow,
    GGDiagramWindow,
    GPSMapWindow,
    MapTileImage,
    SegmentAnalysisWindow,
    VehicleDynamicsWindow,
    VehicleModelWindow,
)
from mflog_proto.ui.time_series_window import TimeSeriesWindow


PROTOTYPE_ROOT = Path(__file__).resolve().parents[1]


class FakeMapTileProvider:
    def __init__(self) -> None:
        self.request_count = 0

    def tile_for_bounds(self, *, latitudes, longitudes):
        self.request_count += 1
        image = QtGui.QImage(2, 2, QtGui.QImage.Format.Format_RGBA8888)
        image.fill(QtGui.QColor("#345678"))
        return MapTileImage(
            image=image,
            west=min(longitudes) - 0.001,
            east=max(longitudes) + 0.001,
            south=min(latitudes) - 0.001,
            north=max(latitudes) + 0.001,
        )


def test_main_window_builds_required_shell_regions(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    expected_tabs = [
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
    ]

    assert _menu_titles(window) == ["파일", "편집", "도구", "설정", "도움말"]
    assert window.preset_tabs.count() == len(expected_tabs)
    assert [window.preset_tabs.tabText(i) for i in range(window.preset_tabs.count())] == expected_tabs
    assert window.sidebar_search.placeholderText() == "분석/문서 검색"
    assert window.analysis_list.count() == len(DEFAULT_ANALYSIS_ITEMS)
    assert window.workspace.subWindowList()
    assert window.properties_panel.windowTitle() == "속성"
    assert "샘플" in window.timeline_status.text()


def test_sidebar_filter_limits_analysis_items(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.sidebar_search.setText("GPS")

    assert window.analysis_list.count() == 1
    assert window.analysis_list.item(0).text() == "GPS Map"


def test_left_sidebar_keeps_documents_and_data_analysis_menu_items(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    item_titles = [
        window.analysis_list.item(index).text()
        for index in range(window.analysis_list.count())
    ]

    assert "Documents" in item_titles
    assert "Data Analysis" in item_titles


def test_left_sidebar_groups_analysis_items_by_workflow(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    groups = {
        window.analysis_tree.topLevelItem(index).text(0)
        for index in range(window.analysis_tree.topLevelItemCount())
    }

    assert groups == {"시각화", "분석", "리포트", "문서"}
    assert window.sidebar_item_titles("분석") == [
        "Data Analysis",
        "Vehicle Dynamics",
        "Segment Analysis",
        "Event Review",
    ]
    assert window.sidebar_item_titles("리포트") == [
        "Benchmark Summary",
        "Export Report",
    ]


def test_right_properties_can_configure_left_sidebar_visibility_width_and_density(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.sidebar_search.setText("GPS")
    window.sidebar_search_visible_checkbox.setChecked(False)
    window.sidebar_add_button_visible_checkbox.setChecked(False)
    window.sidebar_width_spin.setValue(320)
    window.sidebar_density_combo.setCurrentText("Compact")

    assert window.sidebar_search.isVisible() is False
    assert window.sidebar_search.text() == ""
    assert window.analysis_list.count() == len(DEFAULT_ANALYSIS_ITEMS)
    assert window.add_window_button.isVisible() is False
    assert window.left_sidebar.minimumWidth() == 320
    assert window.analysis_list.spacing() == 2


def test_right_properties_can_sort_left_sidebar_analysis_items(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.sidebar_sort_combo.setCurrentText("A-Z")
    item_titles = [
        window.analysis_list.item(index).text()
        for index in range(window.analysis_list.count())
    ]

    assert item_titles == sorted(DEFAULT_ANALYSIS_ITEMS)


def test_right_properties_follow_selected_analysis_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    time_series_subwindow = window.workspace.subWindowList()[0]

    window.workspace.setActiveSubWindow(time_series_subwindow)
    QtWidgets.QApplication.processEvents()

    assert window.properties_stack.currentWidget().objectName() == "timeSeriesPropertiesPage"
    assert window.properties_selection_label.text() == "선택 창: Time-Series Graph"
    assert window.graph_line_width_spin.isVisible() is True
    assert window.gps_map_background_checkbox.isVisible() is False
    assert window.vehicle_model_load_button.isVisible() is False

    gps_subwindow = window.add_analysis_window("GPS Map")
    window.workspace.setActiveSubWindow(gps_subwindow)
    QtWidgets.QApplication.processEvents()

    assert window.properties_stack.currentWidget().objectName() == "gpsPropertiesPage"
    assert window.properties_selection_label.text() == "선택 창: GPS Map"
    assert window.gps_map_background_checkbox.isVisible() is True
    assert window.graph_line_width_spin.isVisible() is False
    assert window.vehicle_model_load_button.isVisible() is False

    vehicle_subwindow = window.add_analysis_window("3D Vehicle Model")
    window.workspace.setActiveSubWindow(vehicle_subwindow)
    QtWidgets.QApplication.processEvents()

    assert window.properties_stack.currentWidget().objectName() == "vehicleModelPropertiesPage"
    assert window.vehicle_model_load_button.isVisible() is True
    assert window.gps_map_background_checkbox.isVisible() is False


def test_right_properties_panel_uses_grouped_readable_rows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    group = window.time_series_properties_page.findChild(
        QtWidgets.QFrame,
        "settingsGroupFrame",
    )
    rows = window.time_series_properties_page.findChildren(
        QtWidgets.QFrame,
        "settingsRow",
    )
    labels = window.time_series_properties_page.findChildren(
        QtWidgets.QLabel,
        "settingsRowLabel",
    )
    row_layouts = [row.layout() for row in rows]
    style = window.styleSheet()

    assert group is not None
    assert len(rows) >= 5
    assert all(64 <= label.minimumWidth() <= 78 for label in labels)
    assert all(layout is not None and layout.spacing() <= 6 for layout in row_layouts)
    assert group.layout().contentsMargins().left() <= 6
    assert all(layout.contentsMargins().left() <= 8 for layout in row_layouts if layout is not None)
    for selector in (
        "QDockWidget#propertiesPanel",
        "QMdiSubWindow::title",
        "QMdiSubWindow::title:active",
        "QMdiSubWindow::close-button:hover",
        "QWidget#propertiesPanelContent",
        "QFrame#settingsGroupFrame",
        "QFrame#settingsRow",
        "QLabel#settingsRowLabel",
        "QFrame#workspaceCommandBar",
        "QFrame#analysisWindowFrame[active=\"true\"]",
        "QFrame#playbackStatusStrip",
        "QFrame#playbackTransportStrip",
        "QCheckBox::indicator",
        "QCheckBox::indicator:unchecked",
        "QListWidget::indicator",
        "QListWidget::indicator:unchecked",
        "QListWidget::indicator:checked",
        "QComboBox QAbstractItemView",
        "QComboBox QAbstractItemView::item",
        "QComboBox QAbstractItemView::item:selected",
        "QAbstractItemView::item:selected",
        "QHeaderView::section",
        "QMenu::item",
        "QMenu::item:selected",
        "QComboBox:disabled",
        "QLabel#hoverLabel",
    ):
        assert selector in style
    assert "background: #26313a;" in style
    assert "selection-background-color: #3d5566;" in style
    assert "background: #334450;" in style
    assert "background: #405665;" in style


def test_bottom_playback_dock_exposes_required_csv_controls_and_status(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    assert window.playback_dock.allowedAreas() == QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
    assert window.current_time_label.text() == "0.000 s / 10.000 s"
    assert window.playback_file_label.text() == "prototype-demo.csv"
    assert window.playback_row_label.text() == "Rows: 101"
    assert window.playback_interval_label.text() == "Sample: 100 ms"
    assert window.playback_event_count_label.text() == "Events: 3"
    assert [window.speed_combo.itemText(index) for index in range(window.speed_combo.count())] == [
        "0.25x",
        "0.5x",
        "1x",
        "2x",
        "4x",
    ]


def test_playback_dock_uses_scrollable_sensor_cards_for_narrow_width(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    assert isinstance(window.sensor_card_scroll_area, QtWidgets.QScrollArea)
    assert window.sensor_card_scroll_area.widgetResizable()
    assert window.playback_controls_row.layout().spacing() <= 8


def test_bottom_playback_slider_updates_graphs_gg_and_sensor_cards(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    gg_window = window.add_analysis_window("G-G Diagram").widget()
    gps_window = window.add_analysis_window("GPS Map").widget()
    time_series = window.workspace.subWindowList()[0].widget()

    window.timeline_slider.setValue(4200)

    assert window.playback_state.current_time_ms == 4200
    assert window.current_row_label.text() == "Row: 42"
    assert time_series.cursor_line.value() == 4.2
    assert gg_window.current_point == pytest.approx((-0.064, 0.25))
    assert gps_window.current_position == pytest.approx((37.00042, 127.00063))
    assert window.sensor_card_value("RPM") == "3670.000"


def test_bottom_playback_sensor_cards_cover_required_current_values(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.timeline_slider.setValue(4200)

    assert tuple(window.sensor_card_value_labels) == (
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
    )
    assert window.sensor_card_value("Gear") == "3"
    assert window.sensor_card_value("yaw rate") == "4.200"


def test_bottom_playback_buttons_speed_and_event_markers_seek(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.timeline_slider.setValue(3000)
    qtbot.mouseClick(window.home_button, QtCore.Qt.LeftButton)

    assert window.playback_state.current_time_ms == 0

    qtbot.mouseClick(window.end_button, QtCore.Qt.LeftButton)

    assert window.playback_state.current_time_ms == window.playback_state.total_time_ms

    qtbot.mouseClick(window.home_button, QtCore.Qt.LeftButton)

    window.speed_combo.setCurrentText("2x")
    assert window.playback_state.playback_speed == 2.0

    qtbot.mouseClick(window.play_pause_button, QtCore.Qt.LeftButton)
    assert window.playback_state.is_playing is True
    assert window.play_pause_button.text() == "Pause"

    qtbot.mouseClick(window.next_event_button, QtCore.Qt.LeftButton)
    assert window.playback_state.current_time_ms == 2500

    item = window.event_marker_list.item(1)
    window.event_marker_list.setCurrentItem(item)

    assert window.playback_state.current_time_ms == 5500
    assert item.background().color().isValid()

    window.seek_to_time_ms(5400)

    assert window.event_marker_list.currentItem().data(QtCore.Qt.ItemDataRole.UserRole) == 5500


def test_playback_timer_advances_current_time_using_selected_speed(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.timeline_slider.setValue(1000)
    window.speed_combo.setCurrentText("2x")
    qtbot.mouseClick(window.play_pause_button, QtCore.Qt.LeftButton)

    assert window.playback_timer.isActive() is True

    window.advance_playback(250)

    assert window.playback_state.current_time_ms == 1500

    qtbot.mouseClick(window.play_pause_button, QtCore.Qt.LeftButton)

    assert window.playback_timer.isActive() is False


def test_playback_keyboard_shortcuts_work_with_slider_focus(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    window.timeline_slider.setFocus()

    qtbot.keyClick(window.timeline_slider, QtCore.Qt.Key_Right)
    assert window.playback_state.current_time_ms == 500

    qtbot.keyClick(window.timeline_slider, QtCore.Qt.Key_Left)
    assert window.playback_state.current_time_ms == 0

    qtbot.keyClick(window.timeline_slider, QtCore.Qt.Key_Space)
    assert window.playback_state.is_playing is True


def test_csv_session_and_playback_position_survive_tab_switches(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.timeline_slider.setValue(4200)
    window.preset_tabs.setCurrentIndex(1)
    window.preset_tabs.setCurrentIndex(7)
    window.preset_tabs.setCurrentIndex(0)

    assert window.loaded_csv_path == Path("prototype-demo.csv")
    assert window.playback_state.current_time_ms == 4200
    assert window.current_time_label.text() == "4.200 s / 10.000 s"
    assert window.current_row_label.text() == "Row: 42"


def test_autosave_warning_keeps_current_csv_session_playable(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    window.timeline_slider.setValue(2500)

    window.set_csv_session(
        Path("prototype-demo.csv"),
        row_count=window.playback_state.sample_count,
        autosave_warning="자동 저장 실패: 현재 세션은 유지됩니다.",
    )

    assert window.playback_warning_label.text() == "자동 저장 실패: 현재 세션은 유지됩니다."
    assert window.timeline_slider.isEnabled() is True
    assert window.play_pause_button.isEnabled() is True
    assert window.playback_state.current_time_ms == 2500


def test_previous_and_next_event_buttons_tolerate_empty_event_list(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    window.playback_events = ()
    window.set_csv_session(Path("no-events.csv"), row_count=window.playback_state.sample_count)
    window.timeline_slider.setValue(3000)

    qtbot.mouseClick(window.prev_event_button, QtCore.Qt.LeftButton)
    qtbot.mouseClick(window.next_event_button, QtCore.Qt.LeftButton)

    assert window.playback_state.current_time_ms == 3000
    assert window.playback_event_count_label.text() == "Events: 0"


def test_main_window_loads_csv_file_into_shared_playback_session(tmp_path, qtbot):
    csv_path = tmp_path / "emu.csv"
    csv_path.write_text(
        "Timestamp,Latitude,Longitude,GPS_Speed_KPH,RPM,TPS_percent,VSS_kmh,Gear,"
        "Batt_V,ax_g,ay_g,gx_dps,gy_dps,gz_dps\n"
        "0.0,37.0,127.0,40,1000,10,41,1,13.1,0.8,1.6,1,2,3\n"
        "0.1,37.1,127.2,50,2000,20,51,2,12.9,2.4,3.2,4,5,6\n"
        "0.2,37.2,127.4,60,3000,95,61,3,11.8,9.6,4.8,7,8,120\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)
    gg_window = window.add_analysis_window("G-G Diagram").widget()
    gps_window = window.add_analysis_window("GPS Map").widget()
    time_series = window.workspace.subWindowList()[0].widget()
    window.timeline_slider.setValue(100)

    assert window.playback_file_label.text() == "emu.csv"
    assert window.playback_row_label.text() == "Rows: 3"
    assert window.current_time_label.text() == "0.100 s / 0.200 s"
    assert window.current_row_label.text() == "Row: 1"
    assert time_series.cursor_line.value() == 0.1
    assert gps_window.current_position == pytest.approx((37.1, 127.2))
    assert gg_window.current_point == pytest.approx((0.3, 0.4))
    assert window.sensor_card_value("RPM") == "2000.000"
    assert window.sensor_card_value("Gear") == "2"
    assert window.sensor_card_value("yaw rate") == "6.000"

    window.timeline_slider.setValue(200)

    assert window.sensor_card_value_labels["Battery voltage"].styleSheet()
    assert window.sensor_card_value_labels["TPS"].styleSheet()
    assert window.sensor_card_value_labels["ax"].styleSheet()
    assert window.sensor_card_value_labels["yaw rate"].styleSheet()


def test_main_window_uses_corrected_adxl_acceleration_for_uploaded_csv(tmp_path, qtbot):
    csv_path = tmp_path / "emu.csv"
    csv_path.write_text(
        "Timestamp,Latitude,Longitude,GPS_Speed_KPH,RPM,TPS_percent,VSS_kmh,Gear,"
        "Batt_V,ax_g,ay_g,gx_dps,gy_dps,gz_dps\n"
        "0.0,37.0,127.0,40,1000,10,41,1,13.1,8,16,1,2,3\n"
        "0.1,37.1,127.2,50,2000,20,51,2,12.9,16,-8,4,5,6\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)
    gg_window = window.add_analysis_window("G-G Diagram").widget()
    window.timeline_slider.setValue(100)

    assert gg_window.current_point == pytest.approx((2.0, -1.0))
    assert window.sensor_card_value("ax") == "2.000"
    assert window.sensor_card_value("ay") == "-1.000"


def test_vehicle_dynamics_uses_steering_angle_alias_from_csv(tmp_path, qtbot):
    csv_path = tmp_path / "steering.csv"
    csv_path.write_text(
        "Timestamp,GPS_Speed_KPH,SteeringAngle_deg,gz_dps,ax_g,ay_g\n"
        "0.0,36,10,90,0,2\n"
        "0.1,36,10,90,0,2\n"
        "0.2,36,10,90,0,2\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)
    dynamics_window = window.add_analysis_window("Vehicle Dynamics").widget()

    assert dynamics_window.metric_value("Yaw response ratio") != "-"
    assert dynamics_window.metric_value("Handling balance") == "oversteer tendency"


def test_vehicle_dynamics_marks_missing_acceleration_unavailable(tmp_path, qtbot):
    csv_path = tmp_path / "minimal.csv"
    csv_path.write_text(
        "Timestamp,RPM\n"
        "0.0,1000\n"
        "0.1,1100\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)
    dynamics_window = window.add_analysis_window("Vehicle Dynamics").widget()

    assert dynamics_window.metric_value("Peak lateral G") == "-"
    assert dynamics_window.metric_value("Peak combined G") == "-"
    assert dynamics_window.metric_value("G utilization") == "-"


def test_main_window_reports_csv_malformed_row_diagnostics(tmp_path, qtbot):
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text(
        "Timestamp,RPM,TPS_percent\n"
        "0.0,1000,10\n"
        "0.1,1100\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)

    assert "Malformed rows: 1" in window.playback_warning_label.text()
    assert window.timeline_slider.isEnabled() is True


def test_playback_dock_disables_without_csv_session(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.timeline_slider.isEnabled() is False
    assert window.play_pause_button.isEnabled() is False
    assert window.playback_file_label.text() == "CSV를 업로드하면 재생할 수 있습니다."


def test_add_analysis_window_from_sidebar(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    initial_count = len(window.workspace.subWindowList())

    matches = window.analysis_list.findItems("G-G Diagram", QtCore.Qt.MatchExactly)
    window.analysis_list.setCurrentItem(matches[0])
    qtbot.mouseClick(window.add_window_button, QtCore.Qt.LeftButton)

    titles = [sub.windowTitle() for sub in window.workspace.subWindowList()]
    assert len(titles) == initial_count + 1
    assert "G-G Diagram" in titles


def test_time_series_analysis_window_uses_real_pyqtgraph_widget(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    first_subwindow = window.workspace.subWindowList()[0]

    assert first_subwindow.windowTitle() == "Time-Series Graph"
    assert isinstance(first_subwindow.widget(), TimeSeriesWindow)


def test_workspace_command_bar_exposes_layout_presets(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.workspace_command_bar.objectName() == "workspaceCommandBar"
    assert window.workspace_preset_names() == (
        "Drive Review",
        "GPS / Line",
        "Dynamics",
        "Sensor Debug",
    )
    assert window.tile_workspace_button.objectName() == "tileWorkspaceButton"


def test_workspace_preset_opens_and_arranges_analysis_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.apply_workspace_preset("Dynamics")
    titles = [sub.windowTitle() for sub in window.workspace.subWindowList()]
    geometries = {
        sub.windowTitle(): sub.geometry()
        for sub in window.workspace.subWindowList()
        if sub.windowTitle()
        in {"Time-Series Graph", "G-G Diagram", "Vehicle Dynamics", "3D Vehicle Model"}
    }

    assert titles.count("Time-Series Graph") == 1
    assert {"G-G Diagram", "Vehicle Dynamics", "3D Vehicle Model"}.issubset(titles)
    assert len({(rect.x(), rect.y()) for rect in geometries.values()}) >= 3


def test_new_analysis_windows_are_staggered_in_workspace(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    gps_window = window.add_analysis_window("GPS Map")
    gg_window = window.add_analysis_window("G-G Diagram")

    assert gps_window.pos() != gg_window.pos()
    assert gps_window.size().width() >= 420
    assert gg_window.size().height() >= 260


def test_analysis_window_uses_colored_custom_title_bar_controls(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    sub_window = window.add_analysis_window("G-G Diagram")

    sub_window.showMaximized()
    QtWidgets.QApplication.processEvents()

    title_bar = sub_window.findChild(
        QtWidgets.QFrame,
        "analysisWindowTitleBar",
    )
    title_label = sub_window.findChild(
        QtWidgets.QLabel,
        "analysisWindowTitleLabel",
    )
    restore_button = sub_window.findChild(
        QtWidgets.QToolButton,
        "analysisWindowRestoreButton",
    )
    close_button = sub_window.findChild(
        QtWidgets.QToolButton,
        "analysisWindowCloseButton",
    )

    assert bool(sub_window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
    assert title_bar is not None
    assert title_bar.isVisible()
    assert "#334450" in title_bar.styleSheet()
    assert "#405665" in title_bar.styleSheet()
    assert title_label is not None
    assert title_label.text() == "G-G Diagram"
    assert restore_button is not None
    assert restore_button.isVisible()
    assert close_button is not None
    assert close_button.isVisible()

    qtbot.mouseClick(restore_button, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()

    assert not sub_window.isMaximized()


def test_active_analysis_window_uses_frame_accent(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    first_subwindow = window.workspace.subWindowList()[0]
    gps_subwindow = window.add_analysis_window("GPS Map")

    window.workspace.setActiveSubWindow(gps_subwindow)
    QtWidgets.QApplication.processEvents()

    assert gps_subwindow.frame_widget().property("active") is True
    assert first_subwindow.frame_widget().property("active") is False
    assert 'QFrame#analysisWindowFrame[active="true"]' in window.styleSheet()


def test_analysis_window_can_resize_by_dragging_border_handle(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    sub_window = window.add_analysis_window("G-G Diagram")
    sub_window.resize(360, 220)
    QtWidgets.QApplication.processEvents()

    resize_handle = sub_window.findChild(
        QtWidgets.QWidget,
        "analysisWindowResizeHandleBottomRight",
    )
    for handle_name in (
        "TopLeft",
        "Top",
        "TopRight",
        "Right",
        "BottomRight",
        "Bottom",
        "BottomLeft",
        "Left",
    ):
        assert sub_window.findChild(
            QtWidgets.QWidget,
            f"analysisWindowResizeHandle{handle_name}",
        ) is not None
    initial_size = sub_window.size()

    assert resize_handle is not None
    assert resize_handle.cursor().shape() == QtCore.Qt.CursorShape.SizeFDiagCursor

    qtbot.mousePress(resize_handle, QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseMove(resize_handle, QtCore.QPoint(80, 60))
    qtbot.mouseRelease(resize_handle, QtCore.Qt.MouseButton.LeftButton)
    QtWidgets.QApplication.processEvents()

    assert sub_window.width() > initial_size.width()
    assert sub_window.height() > initial_size.height()


def test_visual_settings_update_gps_background_and_time_series_style(qtbot):
    tile_provider = FakeMapTileProvider()
    window = MainWindow(map_tile_provider=tile_provider)
    qtbot.addWidget(window)
    window.load_demo_session()
    gps_window = window.add_analysis_window("GPS Map").widget()
    dynamics_window = window.add_analysis_window("Vehicle Dynamics").widget()
    time_series = window.workspace.subWindowList()[0].widget()

    window.gps_map_background_checkbox.setChecked(True)
    window.graph_line_width_spin.setValue(0.75)
    window.graph_line_color_combo.setCurrentText("Red")
    window.gg_limit_radius_spin.setValue(2.25)

    assert gps_window.map_background_enabled is True
    assert gps_window.map_tile_loaded is True
    assert tile_provider.request_count == 1
    assert time_series.curve_style("RPM") == ("#ec7063", 0.75)
    assert window.add_analysis_window("G-G Diagram").widget().limit_circle_radius == 2.25
    assert dynamics_window.summary_text() == "Samples: 101 | G limit: 2.25 G"

    new_time_series = window.add_analysis_window("Time-Series Graph").widget()
    assert new_time_series.curve_style("RPM") == ("#ec7063", 0.75)


def test_gps_properties_enable_ideal_path_for_open_and_new_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    gps_window = window.add_analysis_window("GPS Map").widget()

    assert window.ideal_path_enabled_checkbox.objectName() == "idealPathEnabledCheckbox"
    assert "steering angle" in [
        window.ideal_path_steering_channel_combo.itemText(index)
        for index in range(window.ideal_path_steering_channel_combo.count())
    ]

    window.ideal_path_steering_channel_combo.setCurrentText("steering angle")
    window.ideal_path_wheelbase_spin.setValue(1.6)
    window.ideal_path_steering_ratio_spin.setValue(1.0)
    window.ideal_path_enabled_checkbox.setChecked(True)

    assert gps_window.ideal_path_visible is True
    assert gps_window.ideal_path_point_count == window.playback_state.sample_count
    assert "ready" in gps_window.ideal_path_text()

    new_gps_window = window.add_analysis_window("GPS Map").widget()

    assert new_gps_window.ideal_path_visible is True
    assert new_gps_window.ideal_path_point_count == window.playback_state.sample_count


def test_right_properties_selects_time_series_channels_for_open_and_new_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    time_series = window.workspace.subWindowList()[0].widget()

    _check_time_series_channels(window, ("AX_CORRECTED_G", "AY_CORRECTED_G"))

    assert window.selected_channels == ["AX_CORRECTED_G", "AY_CORRECTED_G"]
    assert time_series.channel_ids == ("AX_CORRECTED_G", "AY_CORRECTED_G")

    new_time_series = window.add_analysis_window("Time-Series Graph").widget()

    assert new_time_series.channel_ids == ("AX_CORRECTED_G", "AY_CORRECTED_G")


def test_csv_raw_numeric_channels_are_available_for_time_series_selection(tmp_path, qtbot):
    csv_path = tmp_path / "emu.csv"
    csv_path.write_text(
        "Timestamp,RPM,TPS_percent,Susp_FL_mm,Susp_FR_mm,Mode\n"
        "0.0,1000,10,20.5,21.5,launch\n"
        "0.1,2000,20,22.5,23.5,run\n",
        encoding="utf-8",
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_csv_session(csv_path)
    time_series = window.workspace.subWindowList()[0].widget()
    _check_time_series_channels(window, ("Susp_FL_mm", "Susp_FR_mm"))

    assert "Susp_FL_mm" in _time_series_channel_options(window)
    assert "Susp_FR_mm" in _time_series_channel_options(window)
    assert "Mode" not in _time_series_channel_options(window)
    assert time_series.channel_ids == ("Susp_FL_mm", "Susp_FR_mm")


def test_right_properties_load_vehicle_model_path_for_open_and_new_windows(qtbot, tmp_path):
    custom_model = tmp_path / "custom-car.glb"
    shutil.copyfile(PROTOTYPE_ROOT.parent / "car.glb", custom_model)
    window = MainWindow()
    qtbot.addWidget(window)
    vehicle_window = window.add_analysis_window("3D Vehicle Model").widget()

    assert window.vehicle_model_path.name == "car.glb"
    assert window.vehicle_model_load_button.objectName() == "vehicleModelLoadButton"

    assert window.load_vehicle_model_path(custom_model) is True

    assert window.vehicle_model_path == custom_model
    assert window.vehicle_model_path_edit.text() == str(custom_model)
    assert vehicle_window.model_status_text().startswith("custom-car.glb | GLB v")
    assert vehicle_window.is_model_mesh_loaded is True

    new_vehicle_window = window.add_analysis_window("3D Vehicle Model").widget()
    assert new_vehicle_window.model_status_text().startswith("custom-car.glb | GLB v")


def test_main_window_routes_minimal_analysis_windows_to_real_widgets(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    created = {
        title: window.add_analysis_window(title).widget()
        for title in (
            "Data Analysis",
            "Documents",
            "G-G Diagram",
            "GPS Map",
            "Current Values Table",
            "Benchmark Summary",
            "3D Vehicle Model",
        )
    }

    assert isinstance(created["Data Analysis"], DataAnalysisWindow)
    assert isinstance(created["Documents"], DocumentsWindow)
    assert created["Data Analysis"].metric_for("RPM", "Mean") == "3950.000"
    assert "car.glb" in created["Documents"].document_names()
    assert isinstance(created["G-G Diagram"], GGDiagramWindow)
    assert isinstance(created["GPS Map"], GPSMapWindow)
    assert isinstance(created["Current Values Table"], CurrentValuesWindow)
    assert isinstance(created["Benchmark Summary"], BenchmarkSummaryWindow)
    assert isinstance(created["3D Vehicle Model"], VehicleModelWindow)


def test_main_window_passes_yaw_rate_to_vehicle_model_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    vehicle_window = window.add_analysis_window("3D Vehicle Model").widget()

    window.set_playback_position(10)

    assert vehicle_window.attitude_degrees[2] == pytest.approx(0.5)
    assert "yaw 0.5 deg" in vehicle_window.attitude_text()


def test_root_asset_path_finds_car_glb_from_prototype_cwd(monkeypatch):
    monkeypatch.chdir(PROTOTYPE_ROOT)

    path = _root_asset_path("car.glb")

    assert path.name == "car.glb"
    assert path.exists()


def test_root_asset_path_finds_bundled_assets_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(PROTOTYPE_ROOT.parent), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    path = _root_asset_path("car.glb")

    assert path == PROTOTYPE_ROOT.parent / "car.glb"


def test_playback_status_updates_shared_bottom_timeline_from_clamped_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.set_playback_position(sample_index=42)

    assert window.timeline_status.text() == "시간 4.200 s | 샘플 42"


def test_bottom_timeline_subscribes_to_shared_playback_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.playback_state.set_seconds(9.96)

    assert window.timeline_status.text() == "시간 9.960 s | 샘플 100"


def test_main_window_can_set_playback_by_seconds_without_sample_argument(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.set_playback_seconds(9.96)

    assert window.timeline_status.text() == "시간 9.960 s | 샘플 100"


def test_main_window_playback_position_moves_time_series_cursor(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    time_series = window.workspace.subWindowList()[0].widget()

    window.set_playback_position(sample_index=999)

    assert isinstance(time_series, TimeSeriesWindow)
    assert time_series.cursor_line.value() == 10.0


def test_event_review_window_seeks_and_edits_review_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    sub_window = window.add_analysis_window("Event Review")
    review_window = sub_window.widget()

    assert isinstance(review_window, EventReviewWindow)
    assert review_window.windowTitle() == "Event Review"
    assert review_window.event_table.rowCount() == 3

    review_window.event_table.selectRow(1)
    assert window.playback_state.current_time_ms == 5500

    review_window.state_combo.setCurrentText("확인")
    review_window.note_edit.setPlainText("Driver felt rear slip")
    review_window.apply_current_review()

    assert window.event_reviews[1].state is EventReviewState.CONFIRMED
    assert window.event_reviews[1].note == "Driver felt rear slip"


def test_segment_analysis_window_creates_segment_from_playback_times(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    sub_window = window.add_analysis_window("Segment Analysis")
    segment_window = sub_window.widget()

    assert isinstance(segment_window, SegmentAnalysisWindow)
    window.set_playback_seconds(1.0)
    segment_window.set_start_from_playback()
    window.set_playback_seconds(3.0)
    segment_window.set_end_from_playback()
    segment_window.name_edit.setText("Corner 1")
    segment_window.add_segment()

    assert window.analysis_segments[0].name == "Corner 1"
    assert window.analysis_segments[0].start_ms == 1000
    assert window.analysis_segments[0].end_ms == 3000
    assert segment_window.segment_table.rowCount() == 1
    assert segment_window.segment_table.item(0, 0).text() == "Corner 1"


def test_export_report_window_writes_html_report(tmp_path, qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    output = tmp_path / "report.html"

    window.export_report_file(output)

    html = output.read_text(encoding="utf-8")
    assert "MF-LOG-ANALYZER v2 Report" in html
    assert "prototype-demo.csv" in html


def test_main_window_captures_workspace_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    window.channel_mappings = {"RPM": "RPM"}
    window.derived_channel_settings = {"AX_CORRECTED_G": {"formula": "ax_g / 8"}}
    window.selected_channels = ["RPM", "AX_CORRECTED_G"]
    window.add_analysis_window("G-G Diagram")
    window.add_analysis_window("Current Values Table")
    window.set_playback_seconds(3.47)
    window.preset_tabs.moveTab(1, 0)
    window.preset_tabs.setCurrentIndex(1)

    state = window.capture_project_state(csv_path="example.csv", active_profile="mf_2026")

    assert state.csv_path.name == "example.csv"
    assert state.active_profile == "mf_2026"
    assert state.channel_mappings == {"RPM": "RPM"}
    assert state.derived_channel_settings == {"AX_CORRECTED_G": {"formula": "ax_g / 8"}}
    assert state.selected_channels == ("RPM", "AX_CORRECTED_G")
    assert state.vehicle_model_path == window.vehicle_model_path
    assert state.playback_seconds == 3.47
    assert state.active_tab_index == 1
    assert state.preset_tab_order[0] == "GPS / LapTime"
    assert [item.title for item in state.open_windows] == [
        "Time-Series Graph",
        "G-G Diagram",
        "Current Values Table",
    ]


def test_main_window_captures_integrated_analysis_state(qtbot, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    window.add_analysis_window("Event Review")
    window.add_analysis_window("Segment Analysis")
    window.event_reviews = window.event_reviews[:1]
    window.analysis_segments = (AnalysisSegment("Corner 1", 1000, 3000),)
    window.report_output_path = tmp_path / "report.html"
    window.selected_sidebar_group = "분석"

    state = window.capture_project_state(csv_path="example.csv")

    assert state.event_reviews == window.event_reviews
    assert state.analysis_segments == window.analysis_segments
    assert state.report_output_path == tmp_path / "report.html"
    assert state.selected_sidebar_group == "분석"


def test_main_window_restores_workspace_project_state(qtbot):
    source = MainWindow()
    qtbot.addWidget(source)
    source.load_demo_session()
    source.active_profile = "mf_2026"
    source.add_analysis_window("G-G Diagram")
    source.add_analysis_window("Benchmark Summary")
    source.set_playback_position(12)
    state = source.capture_project_state(csv_path="example.csv")

    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.load_demo_session()
    restored.restore_project_state(state)

    titles = [sub.windowTitle() for sub in restored.workspace.subWindowList()]
    assert titles == ["Time-Series Graph", "G-G Diagram", "Benchmark Summary"]
    assert restored.active_profile == "mf_2026"
    assert restored.playback_state.current_sample == 12
    assert restored.timeline_status.text() == "시간 1.200 s | 샘플 12"


def test_main_window_restores_event_reviews_segments_and_report_path(qtbot, tmp_path):
    source = MainWindow()
    qtbot.addWidget(source)
    source.load_demo_session()
    source.add_analysis_window("Event Review")
    source.add_analysis_window("Segment Analysis")
    source.event_reviews = source.event_reviews[:1]
    source.analysis_segments = (AnalysisSegment("Corner 1", 1000, 3000),)
    source.report_output_path = tmp_path / "report.html"

    state = source.capture_project_state(csv_path="example.csv")

    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.load_demo_session()
    restored.restore_project_state(state)

    assert restored.event_reviews == source.event_reviews
    assert restored.analysis_segments == source.analysis_segments
    assert restored.report_output_path == source.report_output_path
    assert "Event Review" in [sub.windowTitle() for sub in restored.workspace.subWindowList()]
    assert "Segment Analysis" in [sub.windowTitle() for sub in restored.workspace.subWindowList()]


def test_add_analysis_window_supports_integrated_ux_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    created = {
        title: window.add_analysis_window(title).widget()
        for title in ("Event Review", "Segment Analysis", "Vehicle Dynamics", "Export Report")
    }

    assert isinstance(created["Event Review"], EventReviewWindow)
    assert isinstance(created["Segment Analysis"], SegmentAnalysisWindow)
    assert isinstance(created["Vehicle Dynamics"], VehicleDynamicsWindow)
    assert isinstance(created["Export Report"], ExportReportWindow)


def test_main_window_restores_vehicle_model_path_from_project_state(qtbot, tmp_path):
    custom_model = tmp_path / "project-car.glb"
    shutil.copyfile(PROTOTYPE_ROOT.parent / "car.glb", custom_model)
    state = ProjectState(
        vehicle_model_path=custom_model,
        open_windows=(WindowState("3D Vehicle Model", x=1, y=2, width=420, height=260),),
    )
    restored = MainWindow()
    qtbot.addWidget(restored)

    restored.restore_project_state(state)

    vehicle_window = restored.workspace.subWindowList()[0].widget()
    assert restored.vehicle_model_path == custom_model
    assert restored.vehicle_model_path_edit.text() == str(custom_model)
    assert isinstance(vehicle_window, VehicleModelWindow)
    assert vehicle_window.model_status_text().startswith("project-car.glb | GLB v")


def test_main_window_queues_project_restore_until_csv_load_completes(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    state = ProjectState(
        csv_path=Path("example.csv"),
        open_windows=(WindowState("G-G Diagram", x=1, y=2, width=300, height=240),),
        playback_seconds=0.2,
    )

    window.queue_project_restore_after_data_load(state)

    assert [sub.windowTitle() for sub in window.workspace.subWindowList()] == [
        "Time-Series Graph"
    ]
    assert window.complete_data_load_for_pending_project(Path("other.csv")) is False
    window.load_demo_session()
    assert window.complete_data_load_for_pending_project(Path("example.csv")) is True
    assert [sub.windowTitle() for sub in window.workspace.subWindowList()] == ["G-G Diagram"]
    assert window.playback_state.current_sample == 2


def test_main_window_saves_and_opens_project_file(tmp_path, qtbot):
    csv_path = tmp_path / "emu.csv"
    csv_path.write_text(
        "Timestamp,Latitude,Longitude,GPS_Speed_KPH,RPM,TPS_percent,VSS_kmh,Gear,"
        "Batt_V,ax_g,ay_g,gx_dps,gy_dps,gz_dps\n"
        "0.0,37.0,127.0,40,1000,10,41,1,13.1,0.1,0.2,1,2,3\n"
        "0.1,37.1,127.2,50,2000,20,51,2,12.9,0.3,0.4,4,5,6\n"
        "0.2,37.2,127.4,60,3000,30,61,3,12.8,0.5,0.6,7,8,9\n",
        encoding="utf-8",
    )
    project_path = tmp_path / "session.mflogproj"
    source = MainWindow()
    qtbot.addWidget(source)
    source.load_csv_session(csv_path)
    source.add_analysis_window("G-G Diagram")
    source.seek_to_time_ms(100)

    source.save_project_file(project_path)

    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.open_project_file(project_path)

    assert restored.loaded_csv_path == csv_path
    assert restored.playback_state.current_time_ms == 100
    assert restored.current_row_label.text() == "Row: 1"
    assert [sub.windowTitle() for sub in restored.workspace.subWindowList()] == [
        "Time-Series Graph",
        "G-G Diagram",
    ]


def test_main_window_restore_deletes_previous_mdi_widgets(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    old_widget = window.workspace.subWindowList()[0].widget()
    state = ProjectState(
        open_windows=(WindowState("Benchmark Summary", x=0, y=0, width=300, height=240),)
    )

    window.restore_project_state(state)
    QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()

    assert not shiboken6.isValid(old_widget)


def _menu_titles(window: QtWidgets.QMainWindow) -> list[str]:
    return [
        action.text().replace("&", "")
        for action in window.menuBar().actions()
        if action.menu() is not None
    ]


def _check_time_series_channels(window: MainWindow, channel_ids: tuple[str, ...]) -> None:
    selected = set(channel_ids)
    for index in range(window.time_series_channel_list.count()):
        item = window.time_series_channel_list.item(index)
        state = (
            QtCore.Qt.CheckState.Checked
            if item.text() in selected
            else QtCore.Qt.CheckState.Unchecked
        )
        item.setCheckState(state)
    QtWidgets.QApplication.processEvents()


def _time_series_channel_options(window: MainWindow) -> list[str]:
    return [
        window.time_series_channel_list.item(index).text()
        for index in range(window.time_series_channel_list.count())
    ]
