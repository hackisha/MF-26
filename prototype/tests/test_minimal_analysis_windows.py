from pathlib import Path

import pytest
from PySide6 import QtGui

from mflog_proto.benchmark.metrics import DependencyInfo, EnvironmentInfo
from mflog_proto.playback import PlaybackState
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    GGDiagramWindow,
    GlbModelInfo,
    GPSMapWindow,
    VehicleModelWindow,
    load_glb_info,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_gg_diagram_tracks_playback_point_from_corrected_acceleration(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GGDiagramWindow(playback)
    qtbot.addWidget(window)

    window.set_acceleration(
        ax_corrected=[0.0, 0.25, -0.5],
        ay_corrected=[0.1, -0.2, 0.3],
    )
    playback.set_sample(2)

    assert window.point_count == 3
    assert window.current_point == (-0.5, 0.3)
    assert window.reliability_text() == "Reliability: info"


def test_gg_diagram_draws_one_g_limit_circle(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GGDiagramWindow(playback)
    qtbot.addWidget(window)

    x_values, y_values = window.limit_circle_item.getData()

    assert window.limit_circle_radius == 1.0
    assert len(x_values) >= 64
    assert x_values[0] == pytest.approx(x_values[-1])
    assert y_values[0] == pytest.approx(y_values[-1])


def test_gps_map_tracks_current_position_from_playback(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)

    window.set_track(
        latitude=[37.0, 37.0001, 37.0002],
        longitude=[127.0, 127.0002, 127.0004],
    )
    playback.set_sample(1)

    assert window.point_count == 3
    assert window.current_position == pytest.approx((37.0001, 127.0002))


def test_current_values_table_updates_from_playback_state(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = CurrentValuesWindow(
        playback,
        {
            "RPM": [1000.0, 2500.0, 4000.0],
            "TPS_percent": [5.0, 30.0, 80.0],
        },
    )
    qtbot.addWidget(window)

    playback.set_sample(1)

    assert window.value_for("RPM") == "2500.000"
    assert window.value_for("TPS_percent") == "30.000"
    assert window.reliability_text() == "Reliability: info"


def test_benchmark_summary_window_lists_environment_dependencies(qtbot):
    info = EnvironmentInfo(
        python_version="3.12.6",
        platform="Windows-test",
        machine="AMD64",
        processor="CPU",
        dependencies={
            "PySide6": DependencyInfo("PySide6", True, "6.11.1"),
            "polars": DependencyInfo("polars", False, None),
        },
    )
    window = BenchmarkSummaryWindow(info)
    qtbot.addWidget(window)

    assert window.summary_text() == "Python 3.12.6 | Windows-test | AMD64"
    assert window.dependency_status("PySide6") == "6.11.1"
    assert window.dependency_status("polars") == "missing"
    assert window.reliability_text() == "Reliability: info"


def test_load_glb_info_reads_root_car_fixture():
    info = load_glb_info(PROJECT_ROOT / "car.glb")

    assert info.path.name == "car.glb"
    assert info.version >= 2
    assert info.byte_length > 0
    assert info.json_chunk_length > 0
    assert info.bin_chunk_length >= 0
    assert info.mesh_count > 0
    assert info.node_count > 0
    assert info.has_scene_bounds is True


def test_load_glb_info_rejects_non_glb_file(tmp_path):
    bad_model = tmp_path / "bad.glb"
    bad_model.write_bytes(b"not glb")

    with pytest.raises(ValueError, match="not a GLB"):
        load_glb_info(bad_model)


def test_vehicle_model_window_reports_model_and_throttles_when_hidden(qtbot):
    info = GlbModelInfo(
        path=Path("car.glb"),
        version=2,
        byte_length=1024,
        json_chunk_length=128,
        bin_chunk_length=896,
        mesh_count=1,
        node_count=2,
        scene_min=(-1.0, -0.5, -0.25),
        scene_max=(1.0, 0.5, 0.25),
    )
    window = VehicleModelWindow(info)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.model_status_text() == "car.glb | GLB v2 | 1.0 KB"
    assert window.model_geometry_text() == "Loaded geometry: 1 mesh | 2 nodes"
    assert window.camera_status_text() == "Camera framed | viewport visible"
    assert window.is_camera_framed is True
    assert window.is_model_visible is True
    assert window.reliability_text() == "Reliability: info"
    assert window.is_rendering_enabled is True

    window.hideEvent(QtGui.QHideEvent())

    assert window.is_rendering_enabled is False
