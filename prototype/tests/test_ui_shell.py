import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6 import QtCore, QtWidgets
import shiboken6

from mflog_proto.persistence.project_state import ProjectState, WindowState
from mflog_proto.ui.main_window import DEFAULT_ANALYSIS_ITEMS, MainWindow, _root_asset_path
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    GGDiagramWindow,
    VehicleModelWindow,
)
from mflog_proto.ui.time_series_window import TimeSeriesWindow


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

    created = {
        title: window.add_analysis_window(title).widget()
        for title in (
            "G-G Diagram",
            "Current Values Table",
            "Benchmark Summary",
            "3D Vehicle Model",
        )
    }

    assert isinstance(created["G-G Diagram"], GGDiagramWindow)
    assert isinstance(created["Current Values Table"], CurrentValuesWindow)
    assert isinstance(created["Benchmark Summary"], BenchmarkSummaryWindow)
    assert isinstance(created["3D Vehicle Model"], VehicleModelWindow)


def test_root_asset_path_finds_car_glb_from_prototype_cwd(monkeypatch):
    monkeypatch.chdir("prototype")

    path = _root_asset_path("car.glb")

    assert path.name == "car.glb"
    assert path.exists()


def test_playback_status_updates_shared_bottom_timeline_from_clamped_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_playback_position(sample_index=42)

    assert window.timeline_status.text() == "시간 4.200 s | 샘플 42"


def test_bottom_timeline_subscribes_to_shared_playback_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.playback_state.set_seconds(9.96)

    assert window.timeline_status.text() == "시간 10.000 s | 샘플 100"


def test_main_window_can_set_playback_by_seconds_without_sample_argument(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_playback_seconds(9.96)

    assert window.timeline_status.text() == "시간 10.000 s | 샘플 100"


def test_main_window_playback_position_moves_time_series_cursor(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    time_series = window.workspace.subWindowList()[0].widget()

    window.set_playback_position(sample_index=999)

    assert isinstance(time_series, TimeSeriesWindow)
    assert time_series.cursor_line.value() == 10.0


def test_main_window_captures_workspace_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
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
    assert state.playback_seconds == 3.5
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
    source.active_profile = "mf_2026"
    source.add_analysis_window("G-G Diagram")
    source.add_analysis_window("Benchmark Summary")
    source.set_playback_position(12)
    state = source.capture_project_state(csv_path="example.csv")

    restored = MainWindow()
    qtbot.addWidget(restored)
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
