from pathlib import Path
import sys

from PySide6 import QtCore, QtWidgets
import pytest
import shiboken6

from mflog_proto.persistence.project_state import ProjectState, WindowState
from mflog_proto.ui.main_window import DEFAULT_ANALYSIS_ITEMS, MainWindow, _root_asset_path
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    DataAnalysisWindow,
    DocumentsWindow,
    GGDiagramWindow,
    GPSMapWindow,
    VehicleModelWindow,
)
from mflog_proto.ui.time_series_window import TimeSeriesWindow


PROTOTYPE_ROOT = Path(__file__).resolve().parents[1]


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
        "0.0,37.0,127.0,40,1000,10,41,1,13.1,0.1,0.2,1,2,3\n"
        "0.1,37.1,127.2,50,2000,20,51,2,12.9,0.3,0.4,4,5,6\n"
        "0.2,37.2,127.4,60,3000,95,61,3,11.8,1.2,0.6,7,8,120\n",
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
    assert state.playback_seconds == 3.47
    assert state.active_tab_index == 1
    assert state.preset_tab_order[0] == "GPS / LapTime"
    assert [item.title for item in state.open_windows] == [
        "Time-Series Graph",
        "G-G Diagram",
        "Current Values Table",
    ]


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
