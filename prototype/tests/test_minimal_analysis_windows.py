from pathlib import Path

import pytest
from PySide6 import QtCore, QtGui

from mflog_proto.benchmark.metrics import DependencyInfo, EnvironmentInfo
from mflog_proto.playback import PlaybackState
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    DataAnalysisWindow,
    DocumentsWindow,
    GGDiagramWindow,
    GlbMeshPrimitive,
    GlbModelInfo,
    GPSMapWindow,
    MapTileImage,
    OpenStreetMapTileProvider,
    VehicleModelWindow,
    _qimage_to_rgba_array,
    load_glb_info,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


class FakeMosaicTileProvider(OpenStreetMapTileProvider):
    def __init__(self, cache_dir: Path) -> None:
        super().__init__(cache_dir=cache_dir)
        self.loaded_tiles: list[tuple[int, int, int]] = []

    def _load_tile(self, zoom: int, tile_x: int, tile_y: int) -> QtGui.QImage | None:
        self.loaded_tiles.append((zoom, tile_x, tile_y))
        image = QtGui.QImage(256, 256, QtGui.QImage.Format.Format_RGBA8888)
        image.fill(QtGui.QColor(tile_x % 255, tile_y % 255, zoom % 255))
        return image


def test_osm_tile_provider_builds_high_resolution_mosaic_for_gps_bounds(tmp_path):
    provider = FakeMosaicTileProvider(tmp_path)
    latitudes = [35.2915, 35.2930, 35.2931]
    longitudes = [126.5740, 126.5748, 126.5750]

    tile = provider.tile_for_bounds(latitudes=latitudes, longitudes=longitudes)

    assert tile is not None
    assert len(provider.loaded_tiles) > 1
    assert tile.image.width() > 256 or tile.image.height() > 256
    assert tile.west <= min(longitudes)
    assert tile.east >= max(longitudes)
    assert tile.south <= min(latitudes)
    assert tile.north >= max(latitudes)


def test_qimage_conversion_keeps_map_north_at_higher_latitude():
    image = QtGui.QImage(1, 2, QtGui.QImage.Format.Format_RGBA8888)
    image.setPixelColor(0, 0, QtGui.QColor("#ff0000"))
    image.setPixelColor(0, 1, QtGui.QColor("#0000ff"))

    rgba = _qimage_to_rgba_array(image)

    assert tuple(rgba[0, 0, :3]) == (0, 0, 255)
    assert tuple(rgba[1, 0, :3]) == (255, 0, 0)


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
    assert window.limit_circle_item.zValue() > window.cloud_item.zValue()


def test_gg_diagram_can_update_limit_circle_radius(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1])
    window = GGDiagramWindow(playback)
    qtbot.addWidget(window)

    window.set_limit_circle_radius(2.5)
    x_values, y_values = window.limit_circle_item.getData()

    assert window.limit_circle_radius == 2.5
    assert max(x_values) == pytest.approx(2.5)
    assert min(x_values) == pytest.approx(-2.5)
    assert max(y_values) == pytest.approx(2.5)
    assert min(y_values) == pytest.approx(-2.5)


def test_gg_diagram_shows_hover_info_for_nearest_point(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GGDiagramWindow(playback)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    window.set_acceleration(
        ax_corrected=[0.0, 0.25, -0.5],
        ay_corrected=[0.1, -0.2, 0.3],
    )
    window.plot.setXRange(-1.0, 1.0)
    window.plot.setYRange(-1.0, 1.0)
    qtbot.waitExposed(window)

    scene_pos = window.plot.plotItem.vb.mapViewToScene(QtCore.QPointF(0.25, -0.2))
    window.plot.scene().sigMouseMoved.emit(scene_pos)

    assert window.hover_label.text() == "Hover | G-G | 0.100 s | ax 0.250 g | ay -0.200 g"
    assert window.last_tooltip_text == "G-G | 0.100 s | ax 0.250 g | ay -0.200 g"


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
    assert window.route_background_point_count == 3


def test_gps_map_ignores_zero_and_out_of_range_coordinates(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2, 0.3])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)

    window.set_track(
        latitude=[0.0, 35.292, 91.0, 35.293],
        longitude=[0.0, 126.574, 126.575, 126.576],
    )

    assert window.point_count == 2
    assert window.route_background_point_count == 2
    assert window.current_position is None

    playback.set_sample(1)

    assert window.current_position == pytest.approx((35.292, 126.574))


def test_gps_map_shows_hover_info_for_nearest_position(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    window.set_track(
        latitude=[37.0, 37.0001, 37.0002],
        longitude=[127.0, 127.0002, 127.0004],
    )
    window.plot.setXRange(126.9999, 127.0005)
    window.plot.setYRange(36.9999, 37.0003)
    qtbot.waitExposed(window)

    scene_pos = window.plot.plotItem.vb.mapViewToScene(QtCore.QPointF(127.0002, 37.0001))
    window.plot.scene().sigMouseMoved.emit(scene_pos)

    assert window.hover_label.text() == (
        "Hover | GPS | 0.100 s | lat 37.000100 | lon 127.000200"
    )
    assert window.last_tooltip_text == "GPS | 0.100 s | lat 37.000100 | lon 127.000200"


def test_gps_map_draws_all_routes_and_highlights_active_hover(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    window.set_route_layers(
        (
            {
                "name": "practice.csv",
                "latitude": (36.99, 36.9902),
                "longitude": (126.99, 126.9903),
            },
            {
                "name": "endurance.csv",
                "latitude": (37.0, 37.0001, 37.0002),
                "longitude": (127.0, 127.0002, 127.0004),
            },
        ),
        active_route_name="endurance.csv",
    )
    window.plot.setXRange(126.989, 127.001)
    window.plot.setYRange(36.989, 37.001)
    qtbot.waitExposed(window)

    scene_pos = window.plot.plotItem.vb.mapViewToScene(QtCore.QPointF(127.0002, 37.0001))
    window.plot.scene().sigMouseMoved.emit(scene_pos)

    assert window.background_route_layer_count == 2
    assert window.route_background_point_count == 5
    assert window.active_route_name == "endurance.csv"
    assert window.point_count == 3
    assert window.current_position == pytest.approx((37.0, 127.0))
    assert window.hover_position == pytest.approx((37.0001, 127.0002))
    assert window.hover_route_name == "endurance.csv"
    assert window.hover_marker_visible is True
    assert window.last_tooltip_text == "GPS | 0.100 s | lat 37.000100 | lon 127.000200"


def test_gps_map_toggles_real_map_background(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1])
    tile_provider = FakeMapTileProvider()
    window = GPSMapWindow(playback, tile_provider=tile_provider)
    qtbot.addWidget(window)
    window.set_track(
        latitude=[37.0, 37.0001],
        longitude=[127.0, 127.0002],
    )

    assert window.map_background_enabled is False
    assert window.map_background_text() == "Map background: off"
    assert window.map_tile_loaded is False

    window.set_map_background_enabled(True)

    assert window.map_background_enabled is True
    assert "tile loaded" in window.map_background_text()
    assert window.map_tile_loaded is True
    assert tile_provider.request_count == 1

    window.set_map_background_enabled(False)

    assert window.map_background_text() == "Map background: off"
    assert window.map_tile_loaded is False


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


def test_data_analysis_window_summarizes_session_metrics_and_events(qtbot):
    window = DataAnalysisWindow(
        session_name="sample.csv",
        row_count=3,
        duration_ms=200,
        sampling_interval_ms=100,
        sensor_series={
            "RPM": [1000.0, 2000.0, 3000.0],
            "TPS": [10.0, 20.0, 30.0],
        },
        events=(("warning", "Battery low", 100, "Batt_V < 12.0"),),
    )
    qtbot.addWidget(window)

    assert window.summary_text() == "sample.csv | Rows: 3 | Duration: 0.200 s | Sample: 100 ms"
    assert window.metric_for("RPM", "Mean") == "2000.000"
    assert window.metric_for("TPS", "Max") == "30.000"
    assert window.event_count == 1
    assert window.event_name_at(0) == "Battery low"


def test_documents_window_lists_project_reference_files(qtbot):
    window = DocumentsWindow(
        [
            PROJECT_ROOT / "데이터분석기 콘티.pdf",
            PROJECT_ROOT / "car.glb",
        ]
    )
    qtbot.addWidget(window)

    assert window.document_names() == ["데이터분석기 콘티.pdf", "car.glb"]
    assert window.type_for("car.glb") == ".glb"


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
    assert info.has_renderable_mesh is True
    assert info.vertex_count > 0
    assert info.triangle_count > 0


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
        primitives=(
            GlbMeshPrimitive(
                vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                triangles=((0, 1, 2),),
            ),
        ),
    )
    window = VehicleModelWindow(info)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.model_status_text() == "car.glb | GLB v2 | 1.0 KB"
    assert window.model_geometry_text() == "Loaded geometry: 1 mesh | 2 nodes"
    assert window.camera_status_text() == "Camera framed | viewport visible"
    assert window.qualitative_note_text() == "Qualitative visualization only"
    assert window.preview_status_text() == "Loaded 3D GLB mesh"
    assert window.is_model_preview_rendered is True
    assert window.is_camera_framed is True
    assert window.is_model_visible is True
    assert window.reliability_text() == "Reliability: info"
    assert window.is_rendering_enabled is True

    window.hideEvent(QtGui.QHideEvent())

    assert window.is_rendering_enabled is False


def test_vehicle_model_window_renders_actual_glb_mesh(qtbot):
    info = load_glb_info(PROJECT_ROOT / "car.glb")
    window = VehicleModelWindow(info)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    qtbot.waitExposed(window)

    assert window.is_model_mesh_loaded is True
    assert window.rendered_vertex_count == info.vertex_count
    assert window.rendered_triangle_count == info.triangle_count
    assert window.preview_status_text() == "Loaded 3D GLB mesh"
