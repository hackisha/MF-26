"""Minimal non-time-series analysis windows for the prototype."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import tempfile
from typing import Any, Callable, Mapping, Protocol, Sequence
import urllib.error
import urllib.request

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtMultimedia, QtMultimediaWidgets, QtWidgets

from mflog_proto.analysis.dynamics import DynamicsSummary
from mflog_proto.analysis.event_reviews import EventReview, EventReviewState
from mflog_proto.analysis.reference_route import ReferenceRoute, ReferenceRoutePoint
from mflog_proto.analysis.segments import AnalysisSegment, SegmentSummary
from mflog_proto.benchmark.metrics import EnvironmentInfo
from mflog_proto.playback import CursorEvent, CursorKind, PlaybackState


@dataclass(frozen=True)
class GlbMeshPrimitive:
    vertices: tuple[tuple[float, float, float], ...]
    triangles: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class GlbModelInfo:
    path: Path
    version: int
    byte_length: int
    json_chunk_length: int
    bin_chunk_length: int
    mesh_count: int = 0
    node_count: int = 0
    scene_min: tuple[float, float, float] | None = None
    scene_max: tuple[float, float, float] | None = None
    primitives: tuple[GlbMeshPrimitive, ...] = ()

    @property
    def has_visible_geometry(self) -> bool:
        return self.mesh_count > 0 and self.node_count > 0

    @property
    def has_scene_bounds(self) -> bool:
        return self.scene_min is not None and self.scene_max is not None

    @property
    def has_renderable_mesh(self) -> bool:
        return any(primitive.vertices and primitive.triangles for primitive in self.primitives)

    @property
    def vertex_count(self) -> int:
        return sum(len(primitive.vertices) for primitive in self.primitives)

    @property
    def triangle_count(self) -> int:
        return sum(len(primitive.triangles) for primitive in self.primitives)


@dataclass(frozen=True)
class _VehicleProjection:
    center: tuple[float, float, float]
    span: float
    project: Callable[[tuple[float, float, float]], tuple[QtCore.QPointF, float]]


@dataclass(frozen=True)
class MapTileImage:
    image: QtGui.QImage
    west: float
    east: float
    south: float
    north: float


@dataclass(frozen=True)
class GPSRouteLayer:
    name: str
    latitude: Sequence[float | None]
    longitude: Sequence[float | None]


@dataclass(frozen=True)
class _PreparedGPSRouteLayer:
    name: str
    positions: tuple[tuple[float, float] | None, ...]
    plot_latitudes: tuple[float, ...]
    plot_longitudes: tuple[float, ...]
    valid_count: int


@dataclass(frozen=True)
class _GPSHoverCandidate:
    route_name: str
    sample_index: int
    latitude: float
    longitude: float


class MapTileProvider(Protocol):
    def tile_for_bounds(
        self,
        *,
        latitudes: Sequence[float],
        longitudes: Sequence[float],
    ) -> MapTileImage | None:
        """Return a map tile image covering or near the requested GPS bounds."""


class OpenStreetMapTileProvider:
    _tile_pixel_size = 256
    _max_mosaic_tile_count = 12

    def __init__(self, cache_dir: Path | None = None, timeout_seconds: float = 1.5) -> None:
        self._cache_dir = cache_dir if cache_dir is not None else _default_tile_cache_dir()
        self._timeout_seconds = timeout_seconds

    def tile_for_bounds(
        self,
        *,
        latitudes: Sequence[float],
        longitudes: Sequence[float],
    ) -> MapTileImage | None:
        if not latitudes or not longitudes:
            return None

        south = max(min(latitudes), -85.05112878)
        north = min(max(latitudes), 85.05112878)
        west = max(min(longitudes), -180.0)
        east = min(max(longitudes), 180.0)
        zoom = _zoom_for_span(abs(north - south), abs(east - west))
        tile_range = _tile_range_for_bounds(
            south=south,
            north=north,
            west=west,
            east=east,
            zoom=zoom,
            padding=1,
        )
        while (
            _tile_count_in_range(tile_range) > self._max_mosaic_tile_count
            and zoom > 6
        ):
            zoom -= 1
            tile_range = _tile_range_for_bounds(
                south=south,
                north=north,
                west=west,
                east=east,
                zoom=zoom,
                padding=1,
            )

        min_x, max_x, min_y, max_y = tile_range
        column_count = max_x - min_x + 1
        row_count = max_y - min_y + 1
        mosaic = QtGui.QImage(
            column_count * self._tile_pixel_size,
            row_count * self._tile_pixel_size,
            QtGui.QImage.Format.Format_RGBA8888,
        )
        mosaic.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(mosaic)
        loaded_any_tile = False
        try:
            for tile_y in range(min_y, max_y + 1):
                for tile_x in range(min_x, max_x + 1):
                    image = self._load_tile(zoom, tile_x, tile_y)
                    if image is None:
                        continue
                    loaded_any_tile = True
                    painter.drawImage(
                        (tile_x - min_x) * self._tile_pixel_size,
                        (tile_y - min_y) * self._tile_pixel_size,
                        image,
                    )
        finally:
            painter.end()

        if not loaded_any_tile:
            return None

        tile_west, _, _, tile_north = _tile_bounds(min_x, min_y, zoom)
        _, tile_east, tile_south, _ = _tile_bounds(max_x, max_y, zoom)
        return MapTileImage(
            image=mosaic,
            west=tile_west,
            east=tile_east,
            south=tile_south,
            north=tile_north,
        )

    def _load_tile(self, zoom: int, tile_x: int, tile_y: int) -> QtGui.QImage | None:
        cache_path = self._cache_dir / str(zoom) / str(tile_x) / f"{tile_y}.png"
        if cache_path.exists():
            cached = QtGui.QImage(str(cache_path))
            if not cached.isNull():
                return cached

        url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "MF-LOG-ANALYZER-v2/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = response.read()
        except (OSError, TimeoutError, urllib.error.URLError):
            return None

        image = QtGui.QImage()
        if not image.loadFromData(payload):
            return None

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(cache_path), "PNG")
        except OSError:
            pass
        return image


class GGDiagramWindow(QtWidgets.QWidget):
    def __init__(self, playback_state: PlaybackState, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ggDiagramWindow")
        self._playback_state = playback_state
        self._points: list[tuple[float, float] | None] = []
        self._current_point: tuple[float, float] | None = None
        self.last_tooltip_text = ""
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.plot = pg.PlotWidget(background="#1f2428")
        self.plot.setObjectName("ggDiagramPlot")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.getPlotItem().getViewBox().setAspectLocked(True, ratio=1)
        self.plot.setLabel("bottom", "AX_CORRECTED_G")
        self.plot.setLabel("left", "AY_CORRECTED_G")
        self.plot.scene().sigMouseMoved.connect(self._handle_mouse_moved)
        self.limit_circle_radius = 1.0
        self.limit_circle_item = pg.PlotDataItem(
            *_circle_points(self.limit_circle_radius),
            pen=pg.mkPen("#f4c95d", width=2.25),
        )
        self.cloud_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#5dade2", width=1),
            brush=pg.mkBrush("#5dade2"),
            size=6,
        )
        self.current_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#f4c95d", width=2),
            brush=pg.mkBrush("#f4c95d"),
            size=11,
        )
        self.cloud_item.setZValue(5)
        self.limit_circle_item.setZValue(10)
        self.current_item.setZValue(20)
        self.plot.addItem(self.limit_circle_item)
        self.plot.addItem(self.cloud_item)
        self.plot.addItem(self.current_item)
        self.hover_label = QtWidgets.QLabel("Hover | -")
        self.hover_label.setObjectName("hoverLabel")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.hover_label)
        layout.addWidget(self.reliability_badge)

    @property
    def point_count(self) -> int:
        return sum(point is not None for point in self._points)

    @property
    def current_point(self) -> tuple[float, float] | None:
        return self._current_point

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def set_limit_circle_radius(self, radius: float) -> None:
        self.limit_circle_radius = max(0.1, float(radius))
        self.limit_circle_item.setData(*_circle_points(self.limit_circle_radius))

    def set_acceleration(
        self,
        *,
        ax_corrected: Sequence[float | None],
        ay_corrected: Sequence[float | None],
    ) -> None:
        self._points = []
        plot_points: list[dict[str, float]] = []
        for ax_value, ay_value in zip(ax_corrected, ay_corrected, strict=True):
            if ax_value is None or ay_value is None:
                self._points.append(None)
                continue
            point = (float(ax_value), float(ay_value))
            self._points.append(point)
            plot_points.append({"pos": point})

        self.cloud_item.setData(plot_points)
        self._update_current_point(self._playback_state.current_sample)

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_current_point(event.sample_index)

    def _update_current_point(self, sample_index: int) -> None:
        if not self._points:
            self.current_item.setData([])
            self._current_point = None
            return
        clamped = min(max(sample_index, 0), len(self._points) - 1)
        self._current_point = self._points[clamped]
        if self._current_point is None:
            self.current_item.setData([])
        else:
            self.current_item.setData([{"pos": self._current_point}])

    def _handle_mouse_moved(self, scene_pos: object) -> None:
        scene_pos = _single_scene_point(scene_pos)
        if scene_pos is None or not self.plot.sceneBoundingRect().contains(scene_pos):
            return
        nearest = _nearest_indexed_point(
            self.plot,
            scene_pos,
            self._points,
        )
        if nearest is None:
            return
        sample_index, (ax_value, ay_value) = nearest
        detail = _gg_hover_text(
            seconds=self._playback_state.seconds_at(sample_index),
            ax_value=ax_value,
            ay_value=ay_value,
        )
        self._show_hover_tooltip(scene_pos, detail)
        self._playback_state.publish_hover(
            sample_index=sample_index,
            channel_id="G-G",
            value=math.hypot(ax_value, ay_value),
        )

    def _show_hover_tooltip(self, scene_pos: QtCore.QPointF, detail: str) -> None:
        self.last_tooltip_text = detail
        self.hover_label.setText(f"Hover | {detail}")
        widget_pos = self.plot.mapFromScene(scene_pos)
        global_pos = self.plot.mapToGlobal(widget_pos)
        QtWidgets.QToolTip.showText(global_pos, detail, self.plot)


class GPSMapWindow(QtWidgets.QWidget):
    referenceRouteChanged = QtCore.Signal(object)

    def __init__(
        self,
        playback_state: PlaybackState,
        parent: QtWidgets.QWidget | None = None,
        *,
        tile_provider: MapTileProvider | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gpsMapWindow")
        self._playback_state = playback_state
        self._tile_provider = (
            tile_provider if tile_provider is not None else OpenStreetMapTileProvider()
        )
        self._positions: list[tuple[float, float] | None] = []
        self._route_layers: tuple[_PreparedGPSRouteLayer, ...] = ()
        self._hover_candidates: tuple[_GPSHoverCandidate, ...] = ()
        self._all_positions: tuple[tuple[float, float], ...] = ()
        self._active_route_name = ""
        self._current_position: tuple[float, float] | None = None
        self._hover_position: tuple[float, float] | None = None
        self._hover_route_name = ""
        self._hover_marker_visible = False
        self._route_background_point_count = 0
        self._route_hover_candidates: tuple[_GPSHoverCandidate, ...] = ()
        self._route_positions: tuple[tuple[float, float], ...] = ()
        self._ideal_positions: list[tuple[float, float] | None] = []
        self._ideal_hover_candidates: tuple[_GPSHoverCandidate, ...] = ()
        self._ideal_valid_positions: tuple[tuple[float, float], ...] = ()
        self._ideal_path_point_count = 0
        self._ideal_path_status = "off"
        self._ideal_current_position: tuple[float, float] | None = None
        self._reference_route = ReferenceRoute(name="Reference route", points=())
        self._reference_route_positions: tuple[tuple[float, float], ...] = ()
        self._reference_hover_candidates: tuple[_GPSHoverCandidate, ...] = ()
        self._reference_route_edit_enabled = False
        self._map_background_enabled = False
        self._map_tile_loaded = False
        self._map_background_status = "off"
        self.last_tooltip_text = ""
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.plot = pg.PlotWidget(background="#1f2428")
        self.plot.setObjectName("gpsMapPlot")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("bottom", "Longitude")
        self.plot.setLabel("left", "Latitude")
        self.plot.scene().sigMouseMoved.connect(self._handle_mouse_moved)
        self.plot.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
        self.map_tile_item = pg.ImageItem(axisOrder="row-major")
        self.route_background_item = pg.PlotDataItem(
            pen=pg.mkPen(QtGui.QColor(93, 173, 226, 45), width=2)
        )
        self.ideal_path_item = pg.PlotDataItem(
            pen=pg.mkPen(QtGui.QColor(244, 201, 93, 210), width=2, style=QtCore.Qt.PenStyle.DashLine)
        )
        self.reference_route_item = pg.PlotDataItem(
            pen=pg.mkPen(QtGui.QColor(72, 201, 176, 220), width=2.5)
        )
        self.reference_start_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#2ecc71"),
            size=12,
        )
        self.reference_end_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#e74c3c"),
            size=12,
        )
        self.track_item = pg.PlotDataItem(pen=pg.mkPen("#5dade2", width=3))
        self.current_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#f4c95d", width=2),
            brush=pg.mkBrush("#f4c95d"),
            size=11,
        )
        self.ideal_current_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#f4c95d", width=2),
            brush=pg.mkBrush(QtGui.QColor(244, 201, 93, 90)),
            size=14,
            symbol="x",
        )
        self.hover_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush(QtGui.QColor(244, 201, 93, 80)),
            size=15,
        )
        self.map_tile_item.setZValue(-10)
        self.map_tile_item.setVisible(False)
        self.route_background_item.setZValue(0)
        self.ideal_path_item.setZValue(6)
        self.reference_route_item.setZValue(7)
        self.reference_start_item.setZValue(13)
        self.reference_end_item.setZValue(13)
        self.track_item.setZValue(5)
        self.current_item.setZValue(10)
        self.ideal_current_item.setZValue(11)
        self.hover_item.setZValue(15)
        self.plot.addItem(self.map_tile_item)
        self.plot.addItem(self.route_background_item)
        self.plot.addItem(self.ideal_path_item)
        self.plot.addItem(self.reference_route_item)
        self.plot.addItem(self.reference_start_item)
        self.plot.addItem(self.reference_end_item)
        self.plot.addItem(self.track_item)
        self.plot.addItem(self.current_item)
        self.plot.addItem(self.ideal_current_item)
        self.plot.addItem(self.hover_item)
        self.map_background_label = QtWidgets.QLabel(self.map_background_text())
        self.map_background_label.setObjectName("gpsMapBackgroundStatus")
        self.ideal_path_label = QtWidgets.QLabel(self.ideal_path_text())
        self.ideal_path_label.setObjectName("gpsIdealPathStatus")
        self.hover_label = QtWidgets.QLabel("Hover | -")
        self.hover_label.setObjectName("hoverLabel")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.map_background_label)
        layout.addWidget(self.ideal_path_label)
        layout.addWidget(self.hover_label)
        layout.addWidget(self.reliability_badge)

    @property
    def point_count(self) -> int:
        return sum(position is not None for position in self._positions)

    @property
    def route_background_point_count(self) -> int:
        return self._route_background_point_count

    @property
    def background_route_layer_count(self) -> int:
        return len(self._route_layers)

    @property
    def active_route_name(self) -> str:
        return self._active_route_name

    @property
    def current_position(self) -> tuple[float, float] | None:
        return self._current_position

    @property
    def hover_position(self) -> tuple[float, float] | None:
        return self._hover_position

    @property
    def hover_route_name(self) -> str:
        return self._hover_route_name

    @property
    def hover_marker_visible(self) -> bool:
        return self._hover_marker_visible

    @property
    def map_background_enabled(self) -> bool:
        return self._map_background_enabled

    @property
    def map_tile_loaded(self) -> bool:
        return self._map_tile_loaded

    @property
    def ideal_path_visible(self) -> bool:
        return self._ideal_path_point_count > 0 and self.ideal_path_item.isVisible()

    @property
    def ideal_path_point_count(self) -> int:
        return self._ideal_path_point_count

    @property
    def ideal_current_position(self) -> tuple[float, float] | None:
        return self._ideal_current_position

    @property
    def reference_route_name(self) -> str:
        return self._reference_route.name

    @property
    def reference_route_point_count(self) -> int:
        return len(self._reference_route.points)

    @property
    def reference_route_visible(self) -> bool:
        return self.reference_route_item.isVisible() and self.reference_route_point_count > 0

    @property
    def reference_route_start(self) -> tuple[float, float] | None:
        return self._reference_route_positions[0] if self._reference_route_positions else None

    @property
    def reference_route_end(self) -> tuple[float, float] | None:
        return self._reference_route_positions[-1] if self._reference_route_positions else None

    @property
    def reference_route(self) -> ReferenceRoute:
        return self._reference_route

    @property
    def reference_route_edit_enabled(self) -> bool:
        return self._reference_route_edit_enabled

    def set_reference_route(self, route: ReferenceRoute) -> None:
        self._reference_route = route
        self._refresh_reference_route_items()
        self.referenceRouteChanged.emit(self._reference_route)

    def clear_reference_route(self) -> None:
        self.set_reference_route(ReferenceRoute(name=self._reference_route.name, points=()))

    def set_reference_route_edit_enabled(self, enabled: bool) -> None:
        self._reference_route_edit_enabled = bool(enabled)

    def rename_reference_route(self, name: str) -> None:
        cleaned = name.strip() or "Reference route"
        self.set_reference_route(
            ReferenceRoute(
                name=cleaned,
                points=self._reference_route.points,
                created_at=self._reference_route.created_at,
                metadata=dict(self._reference_route.metadata),
                source_path=self._reference_route.source_path,
            )
        )

    def add_reference_point_from_scene(self, scene_pos: QtCore.QPointF) -> None:
        view_point = self.plot.plotItem.vb.mapSceneToView(scene_pos)
        point = ReferenceRoutePoint(latitude=float(view_point.y()), longitude=float(view_point.x()))
        self.set_reference_route(
            ReferenceRoute(
                name=self._reference_route.name,
                points=(*self._reference_route.points, point),
                created_at=self._reference_route.created_at,
                metadata=dict(self._reference_route.metadata),
                source_path=self._reference_route.source_path,
            )
        )

    def set_map_background_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._map_background_enabled:
            self.map_background_label.setText(self.map_background_text())
            return

        self._map_background_enabled = enabled
        if self._map_background_enabled:
            self.plot.setBackground("#182127")
            self._refresh_map_background()
        else:
            self.plot.setBackground("#1f2428")
            self._clear_map_background("off")

    def map_background_text(self) -> str:
        if not self._map_background_enabled:
            return "Map background: off"
        return f"Map background: on ({self._map_background_status})"

    def ideal_path_text(self) -> str:
        return f"Ideal path: {self._ideal_path_status} | {self._ideal_path_point_count} points"

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def set_track(
        self,
        *,
        latitude: Sequence[float | None],
        longitude: Sequence[float | None],
    ) -> None:
        self.set_route_layers(
            (
                GPSRouteLayer(
                    name="Current CSV",
                    latitude=latitude,
                    longitude=longitude,
                ),
            ),
            active_route_name="Current CSV",
        )

    def set_route_layers(
        self,
        route_layers: Sequence[GPSRouteLayer | Mapping[str, object]],
        *,
        active_route_name: str,
    ) -> None:
        prepared_layers = tuple(
            _prepare_gps_route_layer(_coerce_gps_route_layer(layer))
            for layer in route_layers
        )
        prepared_names = {layer.name for layer in prepared_layers}
        if active_route_name not in prepared_names and prepared_layers:
            active_route_name = prepared_layers[-1].name
        elif not prepared_layers:
            active_route_name = ""

        self._route_layers = prepared_layers
        self._active_route_name = active_route_name
        self._positions = []
        self._hover_position = None
        self._hover_route_name = ""
        self._hover_marker_visible = False
        self.hover_item.setData([])

        background_longitudes: list[float] = []
        background_latitudes: list[float] = []
        hover_candidates: list[_GPSHoverCandidate] = []
        all_positions: list[tuple[float, float]] = []
        valid_count = 0

        active_layer: _PreparedGPSRouteLayer | None = None
        for layer in prepared_layers:
            if background_longitudes:
                background_longitudes.append(math.nan)
                background_latitudes.append(math.nan)
            background_longitudes.extend(layer.plot_longitudes)
            background_latitudes.extend(layer.plot_latitudes)
            valid_count += layer.valid_count
            if layer.name == active_route_name:
                active_layer = layer
            for sample_index, position in enumerate(layer.positions):
                if position is None:
                    continue
                latitude_value, longitude_value = position
                all_positions.append(position)
                hover_candidates.append(
                    _GPSHoverCandidate(
                        route_name=layer.name,
                        sample_index=sample_index,
                        latitude=latitude_value,
                        longitude=longitude_value,
                    )
                )

        self._route_background_point_count = valid_count
        self._route_hover_candidates = tuple(hover_candidates)
        self._route_positions = tuple(all_positions)
        self.route_background_item.setData(background_longitudes, background_latitudes)

        if active_layer is None:
            self.track_item.setData([], [])
        else:
            self._positions = list(active_layer.positions)
            self.track_item.setData(active_layer.plot_longitudes, active_layer.plot_latitudes)

        self._sync_hover_and_map_positions()
        self._refresh_map_background()
        self._update_current_position(self._playback_state.current_sample)

    def set_ideal_path(
        self,
        *,
        latitude: Sequence[float | None],
        longitude: Sequence[float | None],
        status: str,
    ) -> None:
        prepared = _prepare_gps_route_layer(
            GPSRouteLayer(name="Ideal path", latitude=latitude, longitude=longitude)
        )
        self._ideal_positions = list(prepared.positions)
        self._ideal_valid_positions = tuple(
            position for position in prepared.positions if position is not None
        )
        self._ideal_path_point_count = prepared.valid_count
        self._ideal_path_status = status
        if prepared.valid_count == 0:
            self.ideal_path_item.setVisible(False)
            self.ideal_path_item.setData([], [])
        else:
            self.ideal_path_item.setVisible(True)
            self.ideal_path_item.setData(prepared.plot_longitudes, prepared.plot_latitudes)

        self._ideal_hover_candidates = tuple(
            _GPSHoverCandidate(
                route_name=prepared.name,
                sample_index=sample_index,
                latitude=position[0],
                longitude=position[1],
            )
            for sample_index, position in enumerate(prepared.positions)
            if position is not None
        )
        self.ideal_path_label.setText(self.ideal_path_text())
        self._sync_hover_and_map_positions()
        self._refresh_map_background()
        self._update_current_position(self._playback_state.current_sample)

    def clear_ideal_path(self, status: str = "off") -> None:
        self._ideal_positions = []
        self._ideal_valid_positions = ()
        self._ideal_hover_candidates = ()
        self._ideal_path_point_count = 0
        self._ideal_path_status = status
        self._ideal_current_position = None
        self.ideal_path_item.setVisible(False)
        self.ideal_path_item.setData([], [])
        self.ideal_current_item.setData([])
        self.ideal_path_label.setText(self.ideal_path_text())
        self._sync_hover_and_map_positions()

    def _refresh_reference_route_items(self) -> None:
        positions = tuple(
            (point.latitude, point.longitude) for point in self._reference_route.points
        )
        self._reference_route_positions = positions
        longitudes = tuple(position[1] for position in positions)
        latitudes = tuple(position[0] for position in positions)
        self.reference_route_item.setData(longitudes, latitudes)
        self.reference_route_item.setVisible(bool(positions))
        if positions:
            self.reference_start_item.setData([{"pos": (positions[0][1], positions[0][0])}])
            self.reference_end_item.setData([{"pos": (positions[-1][1], positions[-1][0])}])
        else:
            self.reference_start_item.setData([])
            self.reference_end_item.setData([])
        self._reference_hover_candidates = tuple(
            _GPSHoverCandidate(
                route_name=f"Reference: {self._reference_route.name}",
                sample_index=index,
                latitude=position[0],
                longitude=position[1],
            )
            for index, position in enumerate(positions)
        )
        self._sync_hover_and_map_positions()
        self._refresh_map_background()

    def _sync_hover_and_map_positions(self) -> None:
        self._hover_candidates = (
            self._route_hover_candidates
            + self._ideal_hover_candidates
            + self._reference_hover_candidates
        )
        self._all_positions = (
            self._route_positions
            + self._ideal_valid_positions
            + self._reference_route_positions
        )

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_current_position(event.sample_index)

    def _update_current_position(self, sample_index: int) -> None:
        if not self._positions:
            self.current_item.setData([])
            self._current_position = None
            self._update_ideal_current_position(sample_index)
            return
        clamped = min(max(sample_index, 0), len(self._positions) - 1)
        self._current_position = self._positions[clamped]
        if self._current_position is None:
            self.current_item.setData([])
        else:
            latitude, longitude = self._current_position
            self.current_item.setData([{"pos": (longitude, latitude)}])
        self._update_ideal_current_position(sample_index)

    def _update_ideal_current_position(self, sample_index: int) -> None:
        if not self._ideal_positions:
            self._ideal_current_position = None
            self.ideal_current_item.setData([])
            return
        clamped = min(max(sample_index, 0), len(self._ideal_positions) - 1)
        self._ideal_current_position = self._ideal_positions[clamped]
        if self._ideal_current_position is None:
            self.ideal_current_item.setData([])
        else:
            latitude, longitude = self._ideal_current_position
            self.ideal_current_item.setData([{"pos": (longitude, latitude)}])

    def _refresh_map_background(self) -> None:
        if not self._map_background_enabled:
            return

        positions = list(self._all_positions)
        if not positions:
            self._clear_map_background("waiting for GPS")
            return

        latitudes = [position[0] for position in positions]
        longitudes = [position[1] for position in positions]
        try:
            tile = self._tile_provider.tile_for_bounds(
                latitudes=latitudes,
                longitudes=longitudes,
            )
        except (OSError, RuntimeError, ValueError):
            tile = None

        if tile is None:
            self._clear_map_background("tile unavailable")
            return

        self.map_tile_item.setImage(_qimage_to_rgba_array(tile.image), autoLevels=False)
        self.map_tile_item.setRect(
            QtCore.QRectF(
                tile.west,
                tile.south,
                tile.east - tile.west,
                tile.north - tile.south,
            )
        )
        self.map_tile_item.setVisible(True)
        self._map_tile_loaded = True
        self._map_background_status = "tile loaded"
        self.map_background_label.setText(self.map_background_text())

    def _clear_map_background(self, status: str) -> None:
        self.map_tile_item.setVisible(False)
        self._map_tile_loaded = False
        self._map_background_status = status
        self.map_background_label.setText(self.map_background_text())

    def _handle_mouse_clicked(self, mouse_event: object) -> None:
        if not self._reference_route_edit_enabled:
            return
        if not hasattr(mouse_event, "button") or not hasattr(mouse_event, "scenePos"):
            return
        if mouse_event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        scene_pos = mouse_event.scenePos()
        if not isinstance(scene_pos, QtCore.QPointF):
            return
        if not self.plot.plotItem.vb.sceneBoundingRect().contains(scene_pos):
            return
        self.add_reference_point_from_scene(scene_pos)
        if hasattr(mouse_event, "accept"):
            mouse_event.accept()

    def _handle_mouse_moved(self, scene_pos: object) -> None:
        scene_pos = _single_scene_point(scene_pos)
        if scene_pos is None or not self.plot.sceneBoundingRect().contains(scene_pos):
            return
        nearest = self._nearest_hover_candidate(scene_pos)
        if nearest is None:
            return
        sample_index = min(nearest.sample_index, self._playback_state.sample_count - 1)
        detail = _gps_hover_text(
            seconds=self._playback_state.seconds_at(sample_index),
            latitude=nearest.latitude,
            longitude=nearest.longitude,
        )
        if nearest.route_name and nearest.route_name != self._active_route_name:
            detail = f"{nearest.route_name} | {detail}"
        self._show_hover_tooltip(scene_pos, detail, nearest)
        if nearest.route_name == self._active_route_name:
            self._playback_state.publish_hover(
                sample_index=sample_index,
                channel_id="GPS",
                value=None,
            )

    def _nearest_hover_candidate(
        self,
        scene_pos: QtCore.QPointF,
    ) -> _GPSHoverCandidate | None:
        best: _GPSHoverCandidate | None = None
        best_distance_squared: float | None = None
        view_box = self.plot.plotItem.vb

        for candidate in self._hover_candidates:
            point_scene = view_box.mapViewToScene(
                QtCore.QPointF(candidate.longitude, candidate.latitude)
            )
            dx = point_scene.x() - scene_pos.x()
            dy = point_scene.y() - scene_pos.y()
            distance_squared = dx * dx + dy * dy
            if best_distance_squared is None or distance_squared < best_distance_squared:
                best_distance_squared = distance_squared
                best = candidate

        return best

    def _show_hover_tooltip(
        self,
        scene_pos: QtCore.QPointF,
        detail: str,
        candidate: _GPSHoverCandidate,
    ) -> None:
        self.last_tooltip_text = detail
        self._hover_position = (candidate.latitude, candidate.longitude)
        self._hover_route_name = candidate.route_name
        self._hover_marker_visible = True
        self.hover_item.setData([{"pos": (candidate.longitude, candidate.latitude)}])
        self.hover_label.setText(f"Hover | {detail}")
        widget_pos = self.plot.mapFromScene(scene_pos)
        global_pos = self.plot.mapToGlobal(widget_pos)
        QtWidgets.QToolTip.showText(global_pos, detail, self.plot)


class _QtMediaVideoBackend(QtCore.QObject):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QtMultimedia.QMediaPlayer(self)
        self._audio_output = QtMultimedia.QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._duration_changed_callback: Callable[[int], None] | None = None
        self._player.durationChanged.connect(self._handle_duration_changed)

    @property
    def duration_ms(self) -> int:
        return int(self._player.duration())

    @property
    def position_ms(self) -> int:
        return int(self._player.position())

    @property
    def error_text(self) -> str:
        return self._player.errorString()

    def set_video_output(self, video_widget: QtMultimediaWidgets.QVideoWidget) -> None:
        self._player.setVideoOutput(video_widget)

    def set_source(self, path: Path) -> None:
        self._player.setSource(QtCore.QUrl.fromLocalFile(str(path)))

    def clear_source(self) -> None:
        self._player.setSource(QtCore.QUrl())

    def set_position(self, position_ms: int) -> None:
        self._player.setPosition(max(0, int(position_ms)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def set_muted(self, muted: bool) -> None:
        self._audio_output.setMuted(bool(muted))

    def set_playback_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(float(rate))

    def set_duration_changed_callback(self, callback: Callable[[int], None] | None) -> None:
        self._duration_changed_callback = callback

    def _handle_duration_changed(self, duration_ms: int) -> None:
        if self._duration_changed_callback is not None:
            self._duration_changed_callback(int(duration_ms))


class VideoSyncWindow(QtWidgets.QWidget):
    videoOffsetChanged = QtCore.Signal(int)
    videoMutedChanged = QtCore.Signal(bool)

    def __init__(
        self,
        playback_state: PlaybackState,
        *,
        video_path: Path | None = None,
        video_offset_ms: int = 0,
        video_muted: bool = True,
        backend: object | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("videoSyncWindow")
        self._playback_state = playback_state
        self._video_path: Path | None = None
        self._video_offset_ms = int(video_offset_ms)
        self._video_muted = bool(video_muted)
        self._warning_text = ""
        self._backend = backend if backend is not None else _QtMediaVideoBackend(self)
        self._last_is_playing = playback_state.is_playing
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        self.video_widget.setObjectName("videoSyncVideoWidget")
        self.video_widget.setMinimumSize(320, 180)
        self.video_widget.setStyleSheet("background: #11171b; border: 1px solid #53616b;")

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("videoSyncStatusLabel")
        self.status_label.setWordWrap(True)

        self.offset_spin = QtWidgets.QSpinBox()
        self.offset_spin.setObjectName("videoSyncOffsetSpin")
        self.offset_spin.setRange(-3_600_000, 3_600_000)
        self.offset_spin.setSuffix(" ms")
        self.offset_spin.setValue(self._video_offset_ms)
        self.offset_spin.valueChanged.connect(self.set_video_offset_ms)

        self.mute_checkbox = QtWidgets.QCheckBox("Mute")
        self.mute_checkbox.setObjectName("videoSyncMuteCheckbox")
        self.mute_checkbox.setChecked(self._video_muted)
        self.mute_checkbox.toggled.connect(self.set_video_muted)

        self.load_button = QtWidgets.QPushButton("Load Video...")
        self.load_button.setObjectName("videoSyncLoadButton")
        self.load_button.clicked.connect(self._open_video_dialog)
        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.setObjectName("videoSyncClearButton")
        self.clear_button.clicked.connect(lambda: self.set_video_path(None))

        control_row = QtWidgets.QHBoxLayout()
        for delta in (-1000, -100, 100, 1000):
            button = QtWidgets.QPushButton(f"{delta:+d}")
            button.setObjectName(f"videoSyncNudge{delta:+d}Button")
            button.clicked.connect(
                lambda _checked=False, value=delta: self.nudge_video_offset(value)
            )
            control_row.addWidget(button)
        control_row.addWidget(self.offset_spin)
        control_row.addWidget(self.mute_checkbox)
        control_row.addStretch(1)
        control_row.addWidget(self.load_button)
        control_row.addWidget(self.clear_button)

        layout.addWidget(self.video_widget, 1)
        layout.addLayout(control_row)
        layout.addWidget(self.status_label)

        if hasattr(self._backend, "set_video_output"):
            self._backend.set_video_output(self.video_widget)
        if hasattr(self._backend, "set_muted"):
            self._backend.set_muted(self._video_muted)
        if hasattr(self._backend, "set_playback_rate"):
            self._backend.set_playback_rate(self._playback_state.playback_speed)
        if hasattr(self._backend, "set_duration_changed_callback"):
            self._backend.set_duration_changed_callback(self._handle_backend_duration_changed)
        if video_path is not None:
            self.set_video_path(video_path)
        else:
            self._refresh_sync()

    def video_path(self) -> Path | None:
        return self._video_path

    def video_offset_ms(self) -> int:
        return self._video_offset_ms

    def video_muted(self) -> bool:
        return self._video_muted

    def target_video_time_ms(self) -> int:
        raw_position = self._playback_state.current_time_ms + self._video_offset_ms
        duration = int(getattr(self._backend, "duration_ms", 0) or 0)
        lower_clamped = max(0, raw_position)
        return min(lower_clamped, max(0, duration))

    def status_text(self) -> str:
        return self.status_label.text()

    def set_video_path(self, path: Path | str | None) -> None:
        had_warning = bool(self._warning_text)
        self._warning_text = ""
        if path in (None, ""):
            if self._video_path is None:
                self._refresh_sync()
                return
            self._video_path = None
            if hasattr(self._backend, "clear_source"):
                self._backend.clear_source()
            self._refresh_sync()
            return

        candidate = Path(path)
        if candidate == self._video_path and not had_warning:
            self._refresh_sync()
            return
        if candidate == self._video_path and had_warning and not candidate.exists():
            self._warning_text = f"Video missing: {candidate}"
            self._refresh_sync()
            return
        self._video_path = candidate
        if not candidate.exists():
            self._warning_text = f"Video missing: {candidate}"
            if hasattr(self._backend, "pause"):
                self._backend.pause()
            if hasattr(self._backend, "clear_source"):
                self._backend.clear_source()
            self._refresh_sync()
            return
        if hasattr(self._backend, "set_source"):
            self._backend.set_source(candidate)
        self._refresh_sync()

    def set_video_offset_ms(self, offset_ms: int, *, notify: bool = True) -> None:
        next_offset = int(offset_ms)
        changed = next_offset != self._video_offset_ms
        self._video_offset_ms = next_offset
        if self.offset_spin.value() != self._video_offset_ms:
            self.offset_spin.blockSignals(True)
            self.offset_spin.setValue(self._video_offset_ms)
            self.offset_spin.blockSignals(False)
        self._refresh_sync()
        if changed and notify:
            self.videoOffsetChanged.emit(self._video_offset_ms)

    def nudge_video_offset(self, delta_ms: int) -> None:
        self.set_video_offset_ms(self._video_offset_ms + int(delta_ms))

    def set_video_muted(self, muted: bool, *, notify: bool = True) -> None:
        next_muted = bool(muted)
        changed = next_muted != self._video_muted
        self._video_muted = next_muted
        if self.mute_checkbox.isChecked() != self._video_muted:
            self.mute_checkbox.blockSignals(True)
            self.mute_checkbox.setChecked(self._video_muted)
            self.mute_checkbox.blockSignals(False)
        if hasattr(self._backend, "set_muted"):
            self._backend.set_muted(self._video_muted)
        self._refresh_status()
        if changed and notify:
            self.videoMutedChanged.emit(self._video_muted)

    def dispose(self) -> None:
        self._unsubscribe()
        if hasattr(self._backend, "pause"):
            self._backend.pause()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _open_video_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load video",
            str(Path.cwd()),
            "Video files (*.mp4 *.mov *.m4v *.avi);;All files (*.*)",
        )
        if path:
            self.set_video_path(path)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is not CursorKind.PLAYBACK:
            return
        self._refresh_sync()
        if hasattr(self._backend, "set_playback_rate"):
            self._backend.set_playback_rate(self._playback_state.playback_speed)
        if self._playback_state.is_playing != self._last_is_playing:
            self._last_is_playing = self._playback_state.is_playing
            if self._playback_state.is_playing:
                if hasattr(self._backend, "play"):
                    self._backend.play()
            elif hasattr(self._backend, "pause"):
                self._backend.pause()

    def _handle_backend_duration_changed(self, _duration_ms: int) -> None:
        self._refresh_sync()

    def _refresh_sync(self) -> None:
        if (
            self._video_path is not None
            and not self._warning_text
            and hasattr(self._backend, "set_position")
        ):
            self._backend.set_position(self.target_video_time_ms())
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._warning_text:
            self.status_label.setText(self._warning_text)
            return
        name = "-" if self._video_path is None else self._video_path.name
        self.status_label.setText(
            f"Video: {name} | CSV {_format_seconds(self._playback_state.current_time_ms)} | "
            f"Video {_format_seconds(self.target_video_time_ms())} | "
            f"Offset {self._video_offset_ms:+d} ms"
        )


class CurrentValuesWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        series: dict[str, Sequence[float | None]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("currentValuesWindow")
        self._playback_state = playback_state
        self._series = series
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setObjectName("currentValuesTable")
        self.table.setHorizontalHeaderLabels(("Channel", "Value"))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.table, 1)
        layout.addWidget(self.reliability_badge)
        self._populate_rows()
        self._update_values(self._playback_state.current_sample)

    def value_for(self, channel_id: str) -> str:
        for row_index in range(self.table.rowCount()):
            if self.table.item(row_index, 0).text() == channel_id:
                return self.table.item(row_index, 1).text()
        raise KeyError(channel_id)

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _populate_rows(self) -> None:
        self.table.setRowCount(len(self._series))
        for row_index, channel_id in enumerate(self._series):
            self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(channel_id))
            self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem("-"))

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_values(event.sample_index)

    def _update_values(self, sample_index: int) -> None:
        for row_index, (channel_id, values) in enumerate(self._series.items()):
            clamped = min(max(sample_index, 0), len(values) - 1)
            value = values[clamped]
            text = "-" if value is None else f"{float(value):.3f}"
            self.table.item(row_index, 1).setText(text)


class _GaugeWidget(QtWidgets.QWidget):
    def __init__(
        self,
        title: str,
        unit: str,
        maximum: float,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.maximum = float(maximum)
        self.value: float | None = None
        self.setMinimumSize(170, 140)

    def set_value(self, value: float | None) -> None:
        self.value = None if value is None else float(value)
        self.update()

    def value_text(self) -> str:
        if self.value is None:
            return "-"
        if self.unit == "rpm":
            return f"{self.value:.0f} rpm"
        return f"{self.value:.1f} {self.unit}"

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)
        center = QtCore.QPointF(rect.center().x(), rect.bottom() - 18)
        radius = min(rect.width() / 2.0, rect.height() - 38)
        arc_rect = QtCore.QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        painter.setPen(QtGui.QPen(QtGui.QColor("#41505a"), 8))
        painter.drawArc(arc_rect, 30 * 16, 120 * 16)
        ratio = 0.0 if self.value is None else min(max(self.value / self.maximum, 0.0), 1.0)
        painter.setPen(QtGui.QPen(QtGui.QColor("#f4c95d"), 8))
        painter.drawArc(arc_rect, 150 * 16, int(-120 * ratio * 16))
        angle = math.radians(150 - 120 * ratio)
        needle_end = QtCore.QPointF(
            center.x() + math.cos(angle) * radius * 0.78,
            center.y() - math.sin(angle) * radius * 0.78,
        )
        painter.setPen(QtGui.QPen(QtGui.QColor("#e8f1f5"), 3))
        painter.drawLine(center, needle_end)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.drawText(
            rect,
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter,
            self.title,
        )
        painter.setPen(QtGui.QColor("#f4c95d"))
        painter.drawText(
            rect,
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignHCenter,
            self.value_text(),
        )


class GaugeIndicatorsWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        series: dict[str, Sequence[float | None]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gaugeIndicatorsWindow")
        self._playback_state = playback_state
        self._series = series
        self._speed_channel = _first_existing_channel(
            series,
            ("GPS speed", "VSS / GPS speed", "GPS_SPEED_KPH", "GPS_Speed_KPH", "VSS_kmh", "VSS"),
        )
        self._gauges = {
            "RPM": _GaugeWidget("RPM", "rpm", 9000.0),
            "Speed": _GaugeWidget("Speed", "km/h", 180.0),
        }
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        for gauge in self._gauges.values():
            layout.addWidget(gauge, 1)
        self._update_values(self._playback_state.current_sample)

    def gauge_value(self, name: str) -> float | None:
        return self._gauges[name].value

    def gauge_text(self, name: str) -> str:
        return self._gauges[name].value_text()

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_values(event.sample_index)

    def _update_values(self, sample_index: int) -> None:
        self._gauges["RPM"].set_value(_sample_value(self._series.get("RPM"), sample_index))
        self._gauges["Speed"].set_value(
            _sample_value(self._series.get(self._speed_channel, ()), sample_index)
        )


class _TireTemperaturePanel(QtWidgets.QWidget):
    def __init__(self, corner: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.corner = corner
        self.temperature: float | None = None
        self.setMinimumSize(150, 135)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def set_temperature(self, value: float | None) -> None:
        self.temperature = value
        self.update()

    def temperature_text(self) -> str:
        return "-" if self.temperature is None else f"{self.temperature:.1f} C"

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(10, 10, -10, -10)

        painter.setPen(QtGui.QPen(QtGui.QColor("#34424a"), 1))
        painter.setBrush(QtGui.QColor("#1c2327"))
        painter.drawRoundedRect(rect, 6, 6)

        label_rect = QtCore.QRect(rect.left() + 12, rect.top() + 8, 48, 26)
        painter.setPen(QtGui.QColor("#f2f5f7"))
        label_font = painter.font()
        label_font.setBold(True)
        label_font.setPointSize(11)
        painter.setFont(label_font)
        painter.drawText(label_rect, QtCore.Qt.AlignmentFlag.AlignLeft, self.corner)

        bar_rect = QtCore.QRect(
            rect.right() - 34,
            rect.top() + 24,
            14,
            max(54, rect.height() - 54),
        )
        gradient = QtGui.QLinearGradient(bar_rect.bottomLeft(), bar_rect.topLeft())
        gradient.setColorAt(0.0, QtGui.QColor("#4aa3ff"))
        gradient.setColorAt(0.55, QtGui.QColor("#f4c95d"))
        gradient.setColorAt(1.0, QtGui.QColor("#ec7063"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#7a8a94"), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(bar_rect, 4, 4)

        tire_rect = QtCore.QRectF(
            rect.left() + 30,
            rect.top() + 35,
            max(48, rect.width() - 88),
            max(58, rect.height() - 74),
        )
        painter.setPen(QtGui.QPen(QtGui.QColor("#6f7d85"), 2))
        painter.setBrush(QtGui.QColor("#273039"))
        painter.drawRoundedRect(tire_rect, 22, 22)

        inner = tire_rect.adjusted(12, 12, -12, -12)
        painter.setPen(QtGui.QPen(QtGui.QColor("#11161a"), 2))
        painter.setBrush(QtGui.QColor("#151b20"))
        painter.drawRoundedRect(inner, 14, 14)

        if self.temperature is not None:
            ratio = _clamp((self.temperature - 20.0) / 100.0, 0.0, 1.0)
            fill_height = tire_rect.height() * ratio
            heat_rect = QtCore.QRectF(
                tire_rect.left(),
                tire_rect.bottom() - fill_height,
                tire_rect.width(),
                fill_height,
            )
            heat_color = QtGui.QColor.fromRgbF(ratio, 0.25 + (1.0 - ratio) * 0.35, 1.0 - ratio)
            heat_color.setAlpha(70)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(heat_color)
            painter.drawRoundedRect(heat_rect, 18, 18)

        value_rect = QtCore.QRect(rect.left() + 12, rect.bottom() - 32, rect.width() - 24, 24)
        value_font = painter.font()
        value_font.setBold(True)
        value_font.setPointSize(12)
        painter.setFont(value_font)
        painter.setPen(QtGui.QColor("#f4c95d" if self.temperature is not None else "#9aa7af"))
        painter.drawText(
            value_rect,
            QtCore.Qt.AlignmentFlag.AlignCenter,
            self.temperature_text(),
        )


class TireTemperatureWindow(QtWidgets.QWidget):
    _ALIASES: Mapping[str, tuple[str, ...]] = {
        "FL": ("Tire_FL_C", "FL_TireTemp_C", "TireTemp_FL", "FL_temp"),
        "FR": ("Tire_FR_C", "FR_TireTemp_C", "TireTemp_FR", "FR_temp"),
        "RL": ("Tire_RL_C", "RL_TireTemp_C", "TireTemp_RL", "RL_temp"),
        "RR": ("Tire_RR_C", "RR_TireTemp_C", "TireTemp_RR", "RR_temp"),
    }

    def __init__(
        self,
        playback_state: PlaybackState,
        series: dict[str, Sequence[float | None]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tireTemperatureWindow")
        self._playback_state = playback_state
        self._series = series
        self._channels = {
            corner: _first_existing_channel(series, aliases)
            for corner, aliases in self._ALIASES.items()
        }
        self._panels = {
            corner: _TireTemperaturePanel(corner)
            for corner in ("FL", "FR", "RL", "RR")
        }
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        for index, corner in enumerate(("FL", "FR", "RL", "RR")):
            layout.addWidget(self._panels[corner], index // 2, index % 2)
        self._update_values(self._playback_state.current_sample)

    def temperature_text(self, corner: str) -> str:
        return self._panels[corner].temperature_text()

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_values(event.sample_index)

    def _update_values(self, sample_index: int) -> None:
        for corner, panel in self._panels.items():
            channel = self._channels[corner]
            panel.set_temperature(_sample_value(self._series.get(channel), sample_index))


class DataAnalysisWindow(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        session_name: str,
        row_count: int,
        duration_ms: int,
        sampling_interval_ms: int,
        sensor_series: dict[str, Sequence[float | None]],
        events: Sequence[object],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dataAnalysisWindow")
        self._session_name = session_name
        self._row_count = row_count
        self._duration_ms = duration_ms
        self._sampling_interval_ms = sampling_interval_ms
        self._events = tuple(events)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.summary_label = QtWidgets.QLabel(self.summary_text())
        self.summary_label.setObjectName("dataAnalysisSummary")

        self.metrics_table = QtWidgets.QTableWidget(0, 4)
        self.metrics_table.setObjectName("dataAnalysisMetricsTable")
        self.metrics_table.setHorizontalHeaderLabels(("Channel", "Min", "Max", "Mean"))
        self.metrics_table.horizontalHeader().setStretchLastSection(True)

        self.events_table = QtWidgets.QTableWidget(0, 4)
        self.events_table.setObjectName("dataAnalysisEventsTable")
        self.events_table.setHorizontalHeaderLabels(("Severity", "Event", "Time", "Condition"))
        self.events_table.horizontalHeader().setStretchLastSection(True)

        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")

        layout.addWidget(self.summary_label)
        layout.addWidget(self.metrics_table, 2)
        layout.addWidget(self.events_table, 1)
        layout.addWidget(self.reliability_badge)
        self._populate_metrics(sensor_series)
        self._populate_events()

    @property
    def event_count(self) -> int:
        return self.events_table.rowCount()

    def summary_text(self) -> str:
        return (
            f"{self._session_name} | Rows: {self._row_count} | "
            f"Duration: {self._duration_ms / 1000:.3f} s | "
            f"Sample: {self._sampling_interval_ms} ms"
        )

    def metric_for(self, channel_id: str, metric_name: str) -> str:
        column = {"Min": 1, "Max": 2, "Mean": 3}[metric_name]
        for row_index in range(self.metrics_table.rowCount()):
            if self.metrics_table.item(row_index, 0).text() == channel_id:
                return self.metrics_table.item(row_index, column).text()
        raise KeyError(channel_id)

    def event_name_at(self, row_index: int) -> str:
        return self.events_table.item(row_index, 1).text()

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def _populate_metrics(self, sensor_series: dict[str, Sequence[float | None]]) -> None:
        rows: list[tuple[str, float, float, float]] = []
        for channel_id, values in sensor_series.items():
            numeric_values = [float(value) for value in values if value is not None]
            if not numeric_values:
                continue
            rows.append(
                (
                    channel_id,
                    min(numeric_values),
                    max(numeric_values),
                    sum(numeric_values) / len(numeric_values),
                )
            )

        self.metrics_table.setRowCount(len(rows))
        for row_index, (channel_id, minimum, maximum, mean) in enumerate(rows):
            self.metrics_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(channel_id))
            self.metrics_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(f"{minimum:.3f}"))
            self.metrics_table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"{maximum:.3f}"))
            self.metrics_table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(f"{mean:.3f}"))

    def _populate_events(self) -> None:
        self.events_table.setRowCount(len(self._events))
        for row_index, event in enumerate(self._events):
            severity, name, time_ms, condition = _event_fields(event)
            self.events_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(severity))
            self.events_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(name))
            self.events_table.setItem(
                row_index,
                2,
                QtWidgets.QTableWidgetItem(f"{time_ms / 1000:.3f} s"),
            )
            self.events_table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(condition))


class VehicleDynamicsWindow(QtWidgets.QWidget):
    def __init__(
        self,
        summary: DynamicsSummary,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("vehicleDynamicsWindow")
        self.setWindowTitle("Vehicle Dynamics")
        self._summary = summary

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.summary_label = QtWidgets.QLabel(
            f"Samples: {summary.sample_count} | G limit: {summary.g_limit_radius:.2f} G"
        )
        self.summary_label.setObjectName("vehicleDynamicsSummary")

        self.metrics_table = QtWidgets.QTableWidget(0, 2)
        self.metrics_table.setObjectName("vehicleDynamicsMetricsTable")
        self.metrics_table.setHorizontalHeaderLabels(("Metric", "Value"))
        self.metrics_table.horizontalHeader().setStretchLastSection(True)

        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")

        layout.addWidget(self.summary_label)
        layout.addWidget(self.metrics_table, 1)
        layout.addWidget(self.reliability_badge)
        self._populate_metrics()

    def set_summary(self, summary: DynamicsSummary) -> None:
        self._summary = summary
        self.summary_label.setText(
            f"Samples: {summary.sample_count} | G limit: {summary.g_limit_radius:.2f} G"
        )
        self._populate_metrics()

    def summary_text(self) -> str:
        return self.summary_label.text()

    def metric_value(self, metric_name: str) -> str:
        for row_index in range(self.metrics_table.rowCount()):
            if self.metrics_table.item(row_index, 0).text() == metric_name:
                return self.metrics_table.item(row_index, 1).text()
        raise KeyError(metric_name)

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def _populate_metrics(self) -> None:
        rows = (
            ("Peak lateral G", _format_g(self._summary.peak_lateral_g)),
            ("Peak longitudinal G", _format_g(self._summary.peak_longitudinal_g)),
            ("Peak combined G", _format_g(self._summary.peak_combined_g)),
            ("G utilization", _format_percent(self._summary.g_utilization_percent)),
            ("G limit exceedance", str(self._summary.g_limit_exceedance_count)),
            ("Max yaw rate", _format_degrees_per_second(self._summary.max_abs_yaw_rate_dps)),
            ("Yaw response ratio", _format_optional_float(self._summary.yaw_response_ratio)),
            ("Handling balance", self._summary.balance_label),
        )
        self.metrics_table.setRowCount(len(rows))
        for row_index, (metric, value) in enumerate(rows):
            self.metrics_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(metric))
            self.metrics_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(value))


class EventReviewWindow(QtWidgets.QWidget):
    reviewChanged = QtCore.Signal(int, object)

    def __init__(
        self,
        reviews: Sequence[EventReview],
        seek_to_time_ms: Callable[[int], None],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("eventReviewWindow")
        self.setWindowTitle("Event Review")
        self._reviews = list(reviews)
        self._seek_to_time_ms = seek_to_time_ms
        self._syncing_selection = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.event_table = QtWidgets.QTableWidget(0, 5)
        self.event_table.setObjectName("eventReviewTable")
        self.event_table.setHorizontalHeaderLabels(("Time", "Severity", "Event", "Sensor", "State"))
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.event_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        editor = QtWidgets.QFrame()
        editor.setObjectName("eventReviewEditor")
        editor_layout = QtWidgets.QVBoxLayout(editor)
        editor_layout.setContentsMargins(6, 6, 6, 6)
        editor_layout.setSpacing(6)
        self.state_combo = QtWidgets.QComboBox()
        self.state_combo.setObjectName("eventReviewStateCombo")
        self.state_combo.addItems(("미검토", "확인", "무시"))
        self.note_edit = QtWidgets.QPlainTextEdit()
        self.note_edit.setObjectName("eventReviewNoteEdit")
        self.note_edit.setPlaceholderText("Review note")
        self.note_edit.setMaximumHeight(72)
        self.apply_button = QtWidgets.QPushButton("적용")
        self.apply_button.setObjectName("eventReviewApplyButton")
        editor_layout.addWidget(self.state_combo)
        editor_layout.addWidget(self.note_edit)
        editor_layout.addWidget(self.apply_button)

        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")

        layout.addWidget(self.event_table, 1)
        layout.addWidget(editor)
        layout.addWidget(self.reliability_badge)

        self.event_table.itemSelectionChanged.connect(self._handle_selection_changed)
        self.apply_button.clicked.connect(self.apply_current_review)
        self.refresh_reviews(self._reviews)

    def refresh_reviews(self, reviews: Sequence[EventReview]) -> None:
        current_row = self.event_table.currentRow()
        self._reviews = list(reviews)
        self._syncing_selection = True
        try:
            self.event_table.setRowCount(len(self._reviews))
            for row_index, review in enumerate(self._reviews):
                values = (
                    f"{review.time_ms / 1000.0:.3f} s",
                    review.severity,
                    review.name,
                    review.sensor,
                    self._label_for_state(review.state),
                )
                for column_index, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, review.time_ms)
                    self.event_table.setItem(row_index, column_index, item)
            if 0 <= current_row < len(self._reviews):
                self.event_table.selectRow(current_row)
        finally:
            self._syncing_selection = False

    def apply_current_review(self) -> None:
        row = self.event_table.currentRow()
        if row < 0 or row >= len(self._reviews):
            return
        self.reviewChanged.emit(
            row,
            {
                "state": self._state_for_label(self.state_combo.currentText()),
                "note": self.note_edit.toPlainText(),
            },
        )

    def _handle_selection_changed(self) -> None:
        if self._syncing_selection:
            return
        row = self.event_table.currentRow()
        if row < 0 or row >= len(self._reviews):
            return
        review = self._reviews[row]
        self._seek_to_time_ms(review.time_ms)
        self.state_combo.setCurrentText(self._label_for_state(review.state))
        self.note_edit.setPlainText(review.note)

    @staticmethod
    def _label_for_state(state: EventReviewState) -> str:
        return {
            EventReviewState.UNREVIEWED: "미검토",
            EventReviewState.CONFIRMED: "확인",
            EventReviewState.IGNORED: "무시",
        }[state]

    @staticmethod
    def _state_for_label(label: str) -> EventReviewState:
        return {
            "미검토": EventReviewState.UNREVIEWED,
            "확인": EventReviewState.CONFIRMED,
            "무시": EventReviewState.IGNORED,
        }.get(label, EventReviewState.UNREVIEWED)


class SegmentAnalysisWindow(QtWidgets.QWidget):
    segmentAdded = QtCore.Signal(object)

    def __init__(
        self,
        playback_state: PlaybackState,
        summaries: Sequence[SegmentSummary],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmentAnalysisWindow")
        self.setWindowTitle("Segment Analysis")
        self._playback_state = playback_state

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        controls = QtWidgets.QFrame()
        controls.setObjectName("segmentControls")
        controls_layout = QtWidgets.QGridLayout(controls)
        controls_layout.setContentsMargins(6, 6, 6, 6)
        controls_layout.setHorizontalSpacing(6)
        controls_layout.setVerticalSpacing(6)

        self.name_edit = QtWidgets.QLineEdit("Segment 1")
        self.name_edit.setObjectName("segmentNameEdit")
        self.start_ms_spin = QtWidgets.QSpinBox()
        self.start_ms_spin.setObjectName("segmentStartMsSpin")
        self.start_ms_spin.setRange(0, 100_000_000)
        self.start_ms_spin.setSuffix(" ms")
        self.end_ms_spin = QtWidgets.QSpinBox()
        self.end_ms_spin.setObjectName("segmentEndMsSpin")
        self.end_ms_spin.setRange(0, 100_000_000)
        self.end_ms_spin.setSuffix(" ms")
        self.start_from_playback_button = QtWidgets.QPushButton("시작=현재")
        self.end_from_playback_button = QtWidgets.QPushButton("끝=현재")
        self.add_button = QtWidgets.QPushButton("구간 추가")
        self.add_button.setObjectName("segmentAddButton")

        controls_layout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        controls_layout.addWidget(self.name_edit, 0, 1, 1, 3)
        controls_layout.addWidget(QtWidgets.QLabel("Start"), 1, 0)
        controls_layout.addWidget(self.start_ms_spin, 1, 1)
        controls_layout.addWidget(self.start_from_playback_button, 1, 2)
        controls_layout.addWidget(QtWidgets.QLabel("End"), 2, 0)
        controls_layout.addWidget(self.end_ms_spin, 2, 1)
        controls_layout.addWidget(self.end_from_playback_button, 2, 2)
        controls_layout.addWidget(self.add_button, 2, 3)

        self.segment_table = QtWidgets.QTableWidget(0, 7)
        self.segment_table.setObjectName("segmentSummaryTable")
        self.segment_table.setHorizontalHeaderLabels(
            ("Name", "Start", "End", "Rows", "Avg Speed", "Max |ay|", "Min Batt")
        )
        self.segment_table.horizontalHeader().setStretchLastSection(True)

        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")

        layout.addWidget(controls)
        layout.addWidget(self.segment_table, 1)
        layout.addWidget(self.reliability_badge)

        self.start_from_playback_button.clicked.connect(self.set_start_from_playback)
        self.end_from_playback_button.clicked.connect(self.set_end_from_playback)
        self.add_button.clicked.connect(self.add_segment)
        self.refresh_summaries(summaries)

    def set_start_from_playback(self) -> None:
        self.start_ms_spin.setValue(self._playback_state.current_time_ms)

    def set_end_from_playback(self) -> None:
        self.end_ms_spin.setValue(self._playback_state.current_time_ms)

    def add_segment(self) -> None:
        self.segmentAdded.emit(
            AnalysisSegment(
                name=self.name_edit.text().strip() or "Segment",
                start_ms=int(self.start_ms_spin.value()),
                end_ms=int(self.end_ms_spin.value()),
            )
        )

    def refresh_summaries(self, summaries: Sequence[SegmentSummary]) -> None:
        self.segment_table.setRowCount(len(summaries))
        for row_index, summary in enumerate(summaries):
            values = (
                summary.name,
                f"{summary.start_ms / 1000.0:.3f} s",
                f"{summary.end_ms / 1000.0:.3f} s",
                str(summary.row_count),
                _format_optional_float(summary.average_speed),
                _format_optional_float(summary.max_abs_ay),
                _format_optional_float(summary.min_battery_voltage),
            )
            for column_index, value in enumerate(values):
                self.segment_table.setItem(
                    row_index,
                    column_index,
                    QtWidgets.QTableWidgetItem(value),
                )


class ExportReportWindow(QtWidgets.QWidget):
    exportRequested = QtCore.Signal(object)

    def __init__(
        self,
        default_output_path: Path | None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("exportReportWindow")
        self.setWindowTitle("Export Report")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.output_path_edit = QtWidgets.QLineEdit(
            "" if default_output_path is None else str(default_output_path)
        )
        self.output_path_edit.setObjectName("reportOutputPathEdit")
        self.export_button = QtWidgets.QPushButton("HTML 리포트 저장")
        self.export_button.setObjectName("reportExportButton")
        self.status_label = QtWidgets.QLabel("Report: ready")
        self.status_label.setObjectName("reportStatusLabel")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")

        layout.addWidget(QtWidgets.QLabel("Output path"))
        layout.addWidget(self.output_path_edit)
        layout.addWidget(self.export_button)
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        layout.addWidget(self.reliability_badge)

        self.export_button.clicked.connect(self._emit_export_requested)

    def set_output_path(self, path: Path) -> None:
        self.output_path_edit.setText(str(path))
        self.status_label.setText(f"Report saved: {path.name}")

    def _emit_export_requested(self) -> None:
        text = self.output_path_edit.text().strip()
        if text:
            self.exportRequested.emit(Path(text))


class DocumentsWindow(QtWidgets.QWidget):
    def __init__(self, document_paths: Sequence[Path], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("documentsWindow")
        self._document_paths = tuple(document_paths)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.summary_label = QtWidgets.QLabel(f"Documents: {len(self._document_paths)}")
        self.summary_label.setObjectName("documentsSummary")
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setObjectName("documentsTable")
        self.table.setHorizontalHeaderLabels(("Name", "Type", "Size"))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.reliability_badge)
        self._populate_rows()

    def document_names(self) -> list[str]:
        return [self.table.item(row_index, 0).text() for row_index in range(self.table.rowCount())]

    def type_for(self, name: str) -> str:
        for row_index in range(self.table.rowCount()):
            if self.table.item(row_index, 0).text() == name:
                return self.table.item(row_index, 1).text()
        raise KeyError(name)

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def _populate_rows(self) -> None:
        self.table.setRowCount(len(self._document_paths))
        for row_index, path in enumerate(self._document_paths):
            self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(path.name))
            self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(path.suffix.lower()))
            size = path.stat().st_size if path.exists() else 0
            self.table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(_format_kib(size)))


class BenchmarkSummaryWindow(QtWidgets.QWidget):
    def __init__(self, environment: EnvironmentInfo, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("benchmarkSummaryWindow")
        self._environment = environment

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.summary_label = QtWidgets.QLabel(self.summary_text())
        self.summary_label.setObjectName("benchmarkSummaryText")
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setObjectName("benchmarkDependencyTable")
        self.table.setHorizontalHeaderLabels(("Dependency", "Status"))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.reliability_badge)
        self._populate_dependencies()

    def summary_text(self) -> str:
        return (
            f"Python {self._environment.python_version} | "
            f"{self._environment.platform} | {self._environment.machine}"
        )

    def dependency_status(self, name: str) -> str:
        for row_index in range(self.table.rowCount()):
            if self.table.item(row_index, 0).text() == name:
                return self.table.item(row_index, 1).text()
        raise KeyError(name)

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def _populate_dependencies(self) -> None:
        dependencies = self._environment.dependencies
        self.table.setRowCount(len(dependencies))
        for row_index, (name, info) in enumerate(dependencies.items()):
            status = info.version if info.available and info.version is not None else "missing"
            self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(status))


class VehicleModelViewport(QtWidgets.QWidget):
    AXIS_LABELS = ("X", "Y", "Z")
    ATTITUDE_ARROW_LABELS = ("Roll", "Pitch", "Yaw")

    def __init__(self, model_info: GlbModelInfo, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vehicleModelViewport")
        self._model_info = model_info
        self._roll_degrees = 0.0
        self._pitch_degrees = 0.0
        self._yaw_degrees = 0.0
        self.setMinimumHeight(160)

    def set_model_info(self, model_info: GlbModelInfo) -> None:
        self._model_info = model_info
        self.update()

    def set_attitude(
        self,
        *,
        roll_degrees: float,
        pitch_degrees: float,
        yaw_degrees: float = 0.0,
    ) -> None:
        self._roll_degrees = float(roll_degrees)
        self._pitch_degrees = float(pitch_degrees)
        self._yaw_degrees = float(yaw_degrees)
        self.update()

    @property
    def attitude_degrees(self) -> tuple[float, float, float]:
        return self._roll_degrees, self._pitch_degrees, self._yaw_degrees

    @property
    def axis_labels(self) -> tuple[str, str, str]:
        return self.AXIS_LABELS

    @property
    def attitude_arrow_labels(self) -> tuple[str, str, str]:
        return self.ATTITUDE_ARROW_LABELS

    @property
    def has_rendered_model(self) -> bool:
        return self._model_info.has_renderable_mesh and self._model_info.has_scene_bounds

    def preview_status_text(self) -> str:
        return "Loaded 3D GLB mesh" if self.has_rendered_model else "No renderable GLB mesh"

    def axis_origin_text(self) -> str:
        return "Axes origin: vehicle center"

    def attitude_overlay_text(self) -> str:
        roll = _format_degrees(self._roll_degrees)
        pitch = _format_degrees(self._pitch_degrees)
        yaw = _format_degrees(self._yaw_degrees)
        return f"Roll {roll} deg | Pitch {pitch} deg | Yaw {yaw} deg"

    def vehicle_axis_origin_for_rect(self, rect: QtCore.QRect) -> QtCore.QPointF | None:
        if not self.has_rendered_model:
            return None
        projection = self._projection_for_rect(rect)
        point, _ = projection.project(projection.center)
        return point

    @property
    def rendered_vertex_count(self) -> int:
        return self._model_info.vertex_count

    @property
    def rendered_triangle_count(self) -> int:
        return self._model_info.triangle_count

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QtGui.QColor("#161a1d"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#3a4046"), 1))
        painter.drawRect(rect)

        if not self.has_rendered_model:
            painter.setPen(QtGui.QColor("#c8d2dc"))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, self.preview_status_text())
            return

        self._draw_mesh_preview(painter, rect.adjusted(18, 18, -18, -18))

    def _draw_mesh_preview(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        projection = self._projection_for_rect(rect)

        projected_primitives = [
            [projection.project(vertex) for vertex in primitive.vertices]
            for primitive in self._model_info.primitives
        ]
        faces: list[tuple[float, QtGui.QPainterPath]] = []
        for primitive, projected in zip(
            self._model_info.primitives,
            projected_primitives,
            strict=True,
        ):
            for left, middle, right in primitive.triangles:
                if left >= len(projected) or middle >= len(projected) or right >= len(projected):
                    continue
                left_point, left_depth = projected[left]
                middle_point, middle_depth = projected[middle]
                right_point, right_depth = projected[right]
                path = QtGui.QPainterPath(left_point)
                path.lineTo(middle_point)
                path.lineTo(right_point)
                path.closeSubpath()
                average_depth = (left_depth + middle_depth + right_depth) / 3
                faces.append((average_depth, path))

        painter.setPen(QtGui.QPen(QtGui.QColor(112, 196, 245, 130), 1))
        for face_index, (_, path) in enumerate(sorted(faces, key=lambda face: face[0])):
            color = QtGui.QColor("#59afe3") if face_index % 2 else QtGui.QColor("#4b9bd1")
            color.setAlpha(115)
            painter.fillPath(path, QtGui.QBrush(color))
            painter.drawPath(path)

        painter.setPen(QtGui.QColor("#c8d2dc"))
        painter.drawText(
            rect.adjusted(4, 4, -4, -4),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop,
            self.preview_status_text(),
        )
        self._draw_vehicle_center_axes(painter, projection)
        self._draw_attitude_hud(painter, rect)

    def _projection_for_rect(self, rect: QtCore.QRect) -> _VehicleProjection:
        assert self._model_info.scene_min is not None
        assert self._model_info.scene_max is not None
        min_x, min_y, min_z = self._model_info.scene_min
        max_x, max_y, max_z = self._model_info.scene_max
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        span = max(max_x - min_x, max_y - min_y, max_z - min_z, 1e-6)
        scale = min(rect.width(), rect.height()) / span * 0.72
        origin = QtCore.QPointF(rect.center().x(), rect.center().y())
        model_roll = math.radians(self._roll_degrees)
        model_pitch = math.radians(self._pitch_degrees)
        model_yaw = math.radians(self._yaw_degrees)
        cos_roll = math.cos(model_roll)
        sin_roll = math.sin(model_roll)
        cos_model_pitch = math.cos(model_pitch)
        sin_model_pitch = math.sin(model_pitch)
        cos_model_yaw = math.cos(model_yaw)
        sin_model_yaw = math.sin(model_yaw)
        yaw = math.radians(-36)
        camera_pitch = math.radians(24)
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        cos_camera_pitch = math.cos(camera_pitch)
        sin_camera_pitch = math.sin(camera_pitch)

        def project(point: tuple[float, float, float]) -> tuple[QtCore.QPointF, float]:
            x, y, z = point
            x -= center_x
            y -= center_y
            z -= center_z
            yawed_x = x * cos_model_yaw + z * sin_model_yaw
            yawed_z = -x * sin_model_yaw + z * cos_model_yaw
            x, z = yawed_x, yawed_z
            pitched_y = y * cos_model_pitch - z * sin_model_pitch
            pitched_z = y * sin_model_pitch + z * cos_model_pitch
            rolled_x = x * cos_roll - pitched_y * sin_roll
            rolled_y = x * sin_roll + pitched_y * cos_roll
            x, y, z = rolled_x, rolled_y, pitched_z
            view_x = x * cos_yaw + z * sin_yaw
            view_z = -x * sin_yaw + z * cos_yaw
            view_y = y * cos_camera_pitch - view_z * sin_camera_pitch
            depth = y * sin_camera_pitch + view_z * cos_camera_pitch
            screen = QtCore.QPointF(
                origin.x() + view_x * scale,
                origin.y() - view_y * scale,
            )
            return screen, depth

        return _VehicleProjection(
            center=(center_x, center_y, center_z),
            span=span,
            project=project,
        )

    def _draw_vehicle_center_axes(
        self,
        painter: QtGui.QPainter,
        projection: _VehicleProjection,
    ) -> None:
        center_x, center_y, center_z = projection.center
        axis_length = projection.span * 0.34
        origin, _ = projection.project(projection.center)
        axes = (
            ((center_x + axis_length, center_y, center_z), QtGui.QColor("#ec7063"), "X"),
            ((center_x, center_y + axis_length, center_z), QtGui.QColor("#58d68d"), "Y"),
            ((center_x, center_y, center_z + axis_length), QtGui.QColor("#5dade2"), "Z"),
        )
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor("#101417"), 3))
        painter.setBrush(QtGui.QColor("#f4c95d"))
        painter.drawEllipse(origin, 4, 4)
        painter.restore()
        for end_point, color, label in axes:
            end, _ = projection.project(end_point)
            self._draw_arrow(painter, origin, end, color, label)

    def _draw_attitude_hud(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        text = self.attitude_overlay_text()
        font = QtGui.QFont(painter.font())
        font.setPointSize(max(8, font.pointSize() - 1))
        metrics = QtGui.QFontMetrics(font)
        items = (
            ("roll", f"Roll {_format_degrees(self._roll_degrees)} deg", QtGui.QColor("#f4c95d")),
            ("pitch", f"Pitch {_format_degrees(self._pitch_degrees)} deg", QtGui.QColor("#af7ac5")),
            ("yaw", f"Yaw {_format_degrees(self._yaw_degrees)} deg", QtGui.QColor("#5dade2")),
        )
        item_widths = [metrics.horizontalAdvance(label) + 28 for _, label, _ in items]
        natural_width = sum(item_widths) + 16
        available_width = max(64, rect.width() - 12)
        panel_width = min(available_width, max(metrics.horizontalAdvance(text) + 22, natural_width))
        panel_height = metrics.height() + 10
        panel = QtCore.QRectF(
            rect.left() + 6,
            rect.bottom() - panel_height - 6,
            panel_width,
            panel_height,
        )
        painter.save()
        painter.setFont(font)
        painter.setPen(QtGui.QPen(QtGui.QColor("#4a5660"), 1))
        painter.setBrush(QtGui.QColor(21, 26, 30, 215))
        painter.drawRoundedRect(panel, 4, 4)
        painter.setPen(QtGui.QColor("#f4f8fb"))
        if panel_width >= natural_width:
            x = panel.left() + 10
            for (kind, label, color), item_width in zip(items, item_widths, strict=True):
                center = QtCore.QPointF(x + 8, panel.center().y())
                self._draw_attitude_marker(painter, center, kind, color)
                painter.setPen(QtGui.QColor("#f4f8fb"))
                painter.drawText(
                    QtCore.QRectF(x + 22, panel.top(), item_width - 22, panel.height()),
                    QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                    label,
                )
                x += item_width
        else:
            painter.drawText(
                panel.adjusted(10, 0, -8, 0),
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                metrics.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, int(panel_width - 18)),
            )
        painter.restore()

    def _draw_attitude_marker(
        self,
        painter: QtGui.QPainter,
        center: QtCore.QPointF,
        kind: str,
        color: QtGui.QColor,
    ) -> None:
        painter.save()
        painter.setPen(QtGui.QPen(color, 2))
        if kind == "roll":
            direction = 1 if self._roll_degrees >= 0 else -1
            magnitude = 5 + abs(_clamp(self._roll_degrees / 18.0, -1.0, 1.0)) * 7
            start = QtCore.QPointF(center.x() - direction * 5, center.y())
            end = QtCore.QPointF(center.x() + direction * magnitude, center.y())
            painter.drawLine(start, end)
            self._draw_arrow_head(painter, end, math.atan2(start.y() - end.y(), end.x() - start.x()), color)
        elif kind == "pitch":
            direction = -1 if self._pitch_degrees >= 0 else 1
            magnitude = 5 + abs(_clamp(self._pitch_degrees / 18.0, -1.0, 1.0)) * 7
            start = QtCore.QPointF(center.x(), center.y() - direction * 5)
            end = QtCore.QPointF(center.x(), center.y() + direction * magnitude)
            painter.drawLine(start, end)
            self._draw_arrow_head(painter, end, math.atan2(start.y() - end.y(), end.x() - start.x()), color)
        else:
            radius = 7
            arc_rect = QtCore.QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            )
            span = 250 * 16 if self._yaw_degrees >= 0 else -250 * 16
            painter.drawArc(arc_rect, 35 * 16, span)
            end_angle = math.radians(35 + span / 16)
            end = QtCore.QPointF(
                center.x() + math.cos(end_angle) * radius,
                center.y() - math.sin(end_angle) * radius,
            )
            tangent_angle = end_angle + (math.pi / 2 if self._yaw_degrees >= 0 else -math.pi / 2)
            self._draw_arrow_head(painter, end, tangent_angle, color)
        painter.restore()

    def _draw_yaw_arrow(
        self,
        painter: QtGui.QPainter,
        *,
        center: QtCore.QPointF,
        radius: float,
        color: QtGui.QColor,
    ) -> None:
        painter.setPen(QtGui.QPen(color, 2))
        arc_rect = QtCore.QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        magnitude = min(abs(self._yaw_degrees), 180.0) / 180.0
        span_degrees = 36.0 + magnitude * 252.0
        span = int(span_degrees * 16)
        if self._yaw_degrees < 0:
            span *= -1
        painter.drawArc(arc_rect, 35 * 16, span)
        end_angle = math.radians(35 + span / 16)
        end = QtCore.QPointF(
            center.x() + math.cos(end_angle) * radius,
            center.y() - math.sin(end_angle) * radius,
        )
        tangent_angle = end_angle + (math.pi / 2 if self._yaw_degrees >= 0 else -math.pi / 2)
        self._draw_arrow_head(painter, end, tangent_angle, color)
        painter.setPen(QtGui.QColor("#dce7ee"))
        painter.drawText(
            QtCore.QRectF(center.x() + 22, center.y() - 10, 72, 22),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            f"Yaw {self._yaw_degrees:.1f}",
        )

    def _draw_arrow(
        self,
        painter: QtGui.QPainter,
        start: QtCore.QPointF,
        end: QtCore.QPointF,
        color: QtGui.QColor,
        label: str,
    ) -> None:
        painter.setPen(QtGui.QPen(color, 2))
        painter.drawLine(start, end)
        angle = math.atan2(start.y() - end.y(), end.x() - start.x())
        self._draw_arrow_head(painter, end, angle, color)
        painter.setPen(QtGui.QColor("#dce7ee"))
        painter.drawText(
            QtCore.QRectF(end.x() + 4, end.y() - 12, 80, 24),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            label,
        )

    def _draw_arrow_head(
        self,
        painter: QtGui.QPainter,
        tip: QtCore.QPointF,
        angle: float,
        color: QtGui.QColor,
    ) -> None:
        arrow_size = 7
        left = QtCore.QPointF(
            tip.x() - math.cos(angle - math.pi / 7) * arrow_size,
            tip.y() + math.sin(angle - math.pi / 7) * arrow_size,
        )
        right = QtCore.QPointF(
            tip.x() - math.cos(angle + math.pi / 7) * arrow_size,
            tip.y() + math.sin(angle + math.pi / 7) * arrow_size,
        )
        path = QtGui.QPainterPath(tip)
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()
        painter.fillPath(path, QtGui.QBrush(color))


class VehicleModelWindow(QtWidgets.QWidget):
    def __init__(
        self,
        model_info: GlbModelInfo,
        parent: QtWidgets.QWidget | None = None,
        *,
        playback_state: PlaybackState | None = None,
        ax_corrected: Sequence[float | None] = (),
        ay_corrected: Sequence[float | None] = (),
        yaw_rate: Sequence[float | None] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName("vehicleModelWindow")
        self._model_info = model_info
        self._rendering_enabled = True
        self._playback_state = playback_state
        self._ax_corrected = list(ax_corrected)
        self._ay_corrected = list(ay_corrected)
        self._yaw_rate = list(yaw_rate)
        self._cumulative_yaw_degrees: list[float] = []
        self._unsubscribe: Callable[[], None] | None = None
        self._rebuild_cumulative_yaw_degrees()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.model_label = QtWidgets.QLabel(self.model_status_text())
        self.model_label.setObjectName("vehicleModelStatus")
        self.viewport = VehicleModelViewport(model_info)
        viewport_layout = QtWidgets.QVBoxLayout(self.viewport)
        viewport_layout.setContentsMargins(10, 10, 10, 10)
        self.geometry_label = QtWidgets.QLabel(self.model_geometry_text())
        self.geometry_label.setObjectName("vehicleGeometryStatus")
        viewport_layout.addWidget(self.geometry_label)
        viewport_layout.addStretch(1)
        self.camera_label = QtWidgets.QLabel(self.camera_status_text())
        self.camera_label.setObjectName("vehicleCameraStatus")
        self.attitude_label = QtWidgets.QLabel(self.attitude_text())
        self.attitude_label.setObjectName("vehicleAttitudeStatus")
        self.qualitative_note = QtWidgets.QLabel(self.qualitative_note_text())
        self.qualitative_note.setObjectName("vehicleQualitativeNote")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.model_label)
        layout.addWidget(self.viewport, 1)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.attitude_label)
        layout.addWidget(self.qualitative_note)
        layout.addWidget(self.reliability_badge)
        if self._playback_state is not None:
            self._unsubscribe = self._playback_state.subscribe(self._handle_cursor_event)
            self._update_attitude(
                self._playback_state.current_sample,
                self._playback_state.current_seconds,
            )

    def set_model_info(self, model_info: GlbModelInfo) -> None:
        self._model_info = model_info
        self.viewport.set_model_info(model_info)
        self.model_label.setText(self.model_status_text())
        self.geometry_label.setText(self.model_geometry_text())
        self.camera_label.setText(self.camera_status_text())

    def set_acceleration(
        self,
        *,
        ax_corrected: Sequence[float | None],
        ay_corrected: Sequence[float | None],
        yaw_rate: Sequence[float | None] | None = None,
    ) -> None:
        self._ax_corrected = list(ax_corrected)
        self._ay_corrected = list(ay_corrected)
        if yaw_rate is not None:
            self._yaw_rate = list(yaw_rate)
            self._rebuild_cumulative_yaw_degrees()
        sample_index = 0 if self._playback_state is None else self._playback_state.current_sample
        current_seconds = None if self._playback_state is None else self._playback_state.current_seconds
        self._update_attitude(sample_index, current_seconds)

    @property
    def attitude_degrees(self) -> tuple[float, float, float]:
        return self.viewport.attitude_degrees

    @property
    def axis_labels(self) -> tuple[str, str, str]:
        return self.viewport.axis_labels

    @property
    def attitude_arrow_labels(self) -> tuple[str, str, str]:
        return self.viewport.attitude_arrow_labels

    def attitude_text(self) -> str:
        roll, pitch, yaw = self.attitude_degrees
        return (
            f"Attitude: roll {_format_degrees(roll)} deg | "
            f"pitch {_format_degrees(pitch)} deg | yaw {_format_degrees(yaw)} deg"
        )

    def axis_origin_text(self) -> str:
        return self.viewport.axis_origin_text()

    def attitude_overlay_text(self) -> str:
        return self.viewport.attitude_overlay_text()

    def overlay_status_text(self) -> str:
        axes = "/".join(self.axis_labels)
        return f"Axes: vehicle-center {axes} | Attitude HUD: Roll/Pitch/Yaw"

    @property
    def is_rendering_enabled(self) -> bool:
        return self._rendering_enabled

    @property
    def is_model_visible(self) -> bool:
        return (
            self._model_info.has_visible_geometry
            and self.viewport.isVisible()
            and self.geometry_label.isVisible()
        )

    @property
    def is_camera_framed(self) -> bool:
        return self._model_info.has_scene_bounds and self.is_model_visible

    def model_status_text(self) -> str:
        return (
            f"{self._model_info.path.name} | GLB v{self._model_info.version} | "
            f"{_format_kib(self._model_info.byte_length)}"
        )

    def model_geometry_text(self) -> str:
        mesh_word = "mesh" if self._model_info.mesh_count == 1 else "meshes"
        node_word = "node" if self._model_info.node_count == 1 else "nodes"
        return (
            f"Loaded geometry: {self._model_info.mesh_count} {mesh_word} | "
            f"{self._model_info.node_count} {node_word}"
        )

    def camera_status_text(self) -> str:
        framing = "Camera framed" if self.is_camera_framed else "Camera not framed"
        suffix = "viewport visible" if self.viewport.isVisible() else "viewport hidden"
        return f"{framing} | {suffix}"

    def qualitative_note_text(self) -> str:
        return "Qualitative visualization only"

    @property
    def is_model_preview_rendered(self) -> bool:
        return self.viewport.has_rendered_model and self.viewport.isVisible()

    @property
    def is_model_mesh_loaded(self) -> bool:
        return self.viewport.has_rendered_model

    @property
    def rendered_vertex_count(self) -> int:
        return self.viewport.rendered_vertex_count

    @property
    def rendered_triangle_count(self) -> int:
        return self.viewport.rendered_triangle_count

    def preview_status_text(self) -> str:
        return self.viewport.preview_status_text()

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def dispose(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        self._rendering_enabled = True
        self.camera_label.setText(self.camera_status_text())
        super().showEvent(event)

    def hideEvent(self, event: QtGui.QHideEvent) -> None:  # noqa: N802
        self._rendering_enabled = False
        self.camera_label.setText(self.camera_status_text())
        super().hideEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_attitude(event.sample_index, event.seconds)

    def _update_attitude(self, sample_index: int, seconds: float | None = None) -> None:
        ax = _sequence_value(self._ax_corrected, sample_index)
        ay = _sequence_value(self._ay_corrected, sample_index)
        roll = _clamp(ay * 12.0, -18.0, 18.0)
        pitch = _clamp(-ax * 12.0, -18.0, 18.0)
        yaw = self._integrated_yaw_degrees(sample_index, seconds)
        self.viewport.set_attitude(
            roll_degrees=roll,
            pitch_degrees=pitch,
            yaw_degrees=yaw,
        )
        if hasattr(self, "attitude_label"):
            self.attitude_label.setText(self.attitude_text())

    def _integrated_yaw_degrees(self, sample_index: int, seconds: float | None = None) -> float:
        if not self._yaw_rate:
            return 0.0
        if self._playback_state is None:
            return _wrap_degrees(_sequence_value(self._yaw_rate, sample_index))
        if len(self._cumulative_yaw_degrees) != self._playback_state.sample_count:
            self._rebuild_cumulative_yaw_degrees()
        if not self._cumulative_yaw_degrees:
            return 0.0

        clamped = min(max(sample_index, 0), self._playback_state.sample_count - 1)
        if seconds is None:
            seconds = self._playback_state.seconds_at(clamped)
        first_seconds = self._playback_state.seconds_at(0)
        last_seconds = self._playback_state.seconds_at(self._playback_state.sample_count - 1)
        clamped_seconds = _clamp(float(seconds), first_seconds, last_seconds)
        before_index, after_index = self._yaw_interval_indices_for_seconds(clamped_seconds)
        yaw_degrees = self._cumulative_yaw_degrees[before_index]
        if after_index > before_index:
            before_seconds = self._playback_state.seconds_at(before_index)
            after_seconds = self._playback_state.seconds_at(after_index)
            span_seconds = max(0.0, after_seconds - before_seconds)
            partial_seconds = max(0.0, clamped_seconds - before_seconds)
            if span_seconds > 0.0 and partial_seconds > 0.0:
                previous_rate = _sequence_value(self._yaw_rate, before_index)
                next_rate = _sequence_value(self._yaw_rate, after_index)
                fraction = _clamp(partial_seconds / span_seconds, 0.0, 1.0)
                interpolated_rate = previous_rate + (next_rate - previous_rate) * fraction
                yaw_degrees += (previous_rate + interpolated_rate) / 2 * partial_seconds
        return _wrap_degrees(yaw_degrees)

    def _rebuild_cumulative_yaw_degrees(self) -> None:
        if self._playback_state is None or not self._yaw_rate:
            self._cumulative_yaw_degrees = []
            return
        cumulative = [0.0] * self._playback_state.sample_count
        for index in range(1, self._playback_state.sample_count):
            previous_rate = _sequence_value(self._yaw_rate, index - 1)
            current_rate = _sequence_value(self._yaw_rate, index)
            delta_seconds = max(
                0.0,
                self._playback_state.seconds_at(index)
                - self._playback_state.seconds_at(index - 1),
            )
            cumulative[index] = cumulative[index - 1] + (
                previous_rate + current_rate
            ) / 2 * delta_seconds
        self._cumulative_yaw_degrees = cumulative

    def _yaw_interval_indices_for_seconds(self, seconds: float) -> tuple[int, int]:
        if self._playback_state is None:
            return (0, 0)
        last_index = self._playback_state.sample_count - 1
        if last_index <= 0 or seconds <= self._playback_state.seconds_at(0):
            return (0, 0)
        if seconds >= self._playback_state.seconds_at(last_index):
            return (last_index, last_index)

        low = 0
        high = last_index
        while low < high:
            mid = (low + high + 1) // 2
            if self._playback_state.seconds_at(mid) <= seconds:
                low = mid
            else:
                high = mid - 1
        return (low, min(low + 1, last_index))


def load_glb_info(path: Path) -> GlbModelInfo:
    version, byte_length, json_chunk, bin_chunk = _read_glb_chunks(path)
    document = _parse_glb_json(json_chunk)
    mesh_count, node_count, scene_min, scene_max = _glb_scene_summary(document)
    primitives = _glb_mesh_primitives(document, bin_chunk)
    mesh_scene_min, mesh_scene_max = _bounds_for_primitives(primitives)
    if mesh_scene_min is not None and mesh_scene_max is not None:
        scene_min = mesh_scene_min
        scene_max = mesh_scene_max
    return GlbModelInfo(
        path=path,
        version=version,
        byte_length=byte_length,
        json_chunk_length=len(json_chunk),
        bin_chunk_length=len(bin_chunk),
        mesh_count=mesh_count,
        node_count=node_count,
        scene_min=scene_min,
        scene_max=scene_max,
        primitives=primitives,
    )


def _format_kib(byte_length: int) -> str:
    return f"{byte_length / 1024:.1f} KB"


def _format_seconds(time_ms: int) -> str:
    return f"{int(time_ms) / 1000:.3f} s"


def _first_existing_channel(
    series: Mapping[str, Sequence[float | None]],
    names: Sequence[str],
) -> str:
    for name in names:
        if name in series:
            return name
    return ""


def _sample_value(values: Sequence[float | None] | None, sample_index: int) -> float | None:
    if not values:
        return None
    clamped = min(max(sample_index, 0), len(values) - 1)
    value = values[clamped]
    return None if value is None else float(value)


def _format_optional_float(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _format_g(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f} G"


def _format_percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f} %"


def _format_degrees_per_second(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f} deg/s"


def _single_scene_point(scene_pos: object) -> QtCore.QPointF | None:
    if isinstance(scene_pos, tuple | list):
        if not scene_pos:
            return None
        scene_pos = scene_pos[0]
    if not isinstance(scene_pos, QtCore.QPointF):
        return None
    return scene_pos


def _nearest_indexed_point(
    plot: pg.PlotWidget,
    scene_pos: QtCore.QPointF,
    points: Sequence[tuple[float, float] | None],
) -> tuple[int, tuple[float, float]] | None:
    best: tuple[int, tuple[float, float]] | None = None
    best_distance_squared: float | None = None
    view_box = plot.plotItem.vb

    for sample_index, point in enumerate(points):
        if point is None:
            continue
        point_scene = view_box.mapViewToScene(QtCore.QPointF(point[0], point[1]))
        dx = point_scene.x() - scene_pos.x()
        dy = point_scene.y() - scene_pos.y()
        distance_squared = dx * dx + dy * dy
        if best_distance_squared is None or distance_squared < best_distance_squared:
            best_distance_squared = distance_squared
            best = (sample_index, point)

    return best


def _gg_hover_text(*, seconds: float, ax_value: float, ay_value: float) -> str:
    return f"G-G | {seconds:.3f} s | ax {ax_value:.3f} g | ay {ay_value:.3f} g"


def _gps_hover_text(*, seconds: float, latitude: float, longitude: float) -> str:
    return f"GPS | {seconds:.3f} s | lat {latitude:.6f} | lon {longitude:.6f}"


def _coerce_gps_route_layer(layer: GPSRouteLayer | Mapping[str, object]) -> GPSRouteLayer:
    if isinstance(layer, GPSRouteLayer):
        return layer
    name = str(layer.get("name", "CSV"))
    latitude = layer.get("latitude", ())
    longitude = layer.get("longitude", ())
    if not isinstance(latitude, Sequence) or isinstance(latitude, str):
        latitude = ()
    if not isinstance(longitude, Sequence) or isinstance(longitude, str):
        longitude = ()
    return GPSRouteLayer(
        name=name,
        latitude=tuple(latitude),
        longitude=tuple(longitude),
    )


def _prepare_gps_route_layer(layer: GPSRouteLayer) -> _PreparedGPSRouteLayer:
    positions: list[tuple[float, float] | None] = []
    plot_latitudes: list[float] = []
    plot_longitudes: list[float] = []
    valid_count = 0

    for latitude_value, longitude_value in zip(layer.latitude, layer.longitude, strict=True):
        if not _is_valid_gps_position(latitude_value, longitude_value):
            positions.append(None)
            plot_latitudes.append(math.nan)
            plot_longitudes.append(math.nan)
            continue
        position = (float(latitude_value), float(longitude_value))
        positions.append(position)
        plot_latitudes.append(position[0])
        plot_longitudes.append(position[1])
        valid_count += 1

    return _PreparedGPSRouteLayer(
        name=layer.name,
        positions=tuple(positions),
        plot_latitudes=tuple(plot_latitudes),
        plot_longitudes=tuple(plot_longitudes),
        valid_count=valid_count,
    )


def _is_valid_gps_position(
    latitude: float | None,
    longitude: float | None,
) -> bool:
    if latitude is None or longitude is None:
        return False
    latitude = float(latitude)
    longitude = float(longitude)
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return False
    if not -90.0 <= latitude <= 90.0:
        return False
    if not -180.0 <= longitude <= 180.0:
        return False
    return not (abs(latitude) < 1e-9 and abs(longitude) < 1e-9)


def _default_tile_cache_dir() -> Path:
    qt_cache_dir = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.CacheLocation
    )
    if qt_cache_dir:
        return Path(qt_cache_dir) / "osm-tiles"
    return Path(tempfile.gettempdir()) / "mflog-analyzer" / "osm-tiles"


def _zoom_for_span(latitude_span: float, longitude_span: float) -> int:
    span = max(latitude_span, longitude_span)
    if span <= 0.0025:
        return 18
    if span <= 0.005:
        return 17
    if span <= 0.01:
        return 16
    if span <= 0.05:
        return 15
    if span <= 0.1:
        return 14
    if span <= 0.5:
        return 12
    if span <= 1.0:
        return 10
    if span <= 5.0:
        return 8
    return 6


def _tile_for_lat_lon(latitude: float, longitude: float, zoom: int) -> tuple[int, int]:
    clamped_latitude = min(max(latitude, -85.05112878), 85.05112878)
    clamped_longitude = min(max(longitude, -180.0), 180.0)
    lat_rad = math.radians(clamped_latitude)
    tile_count = 1 << zoom
    tile_x = int((clamped_longitude + 180.0) / 360.0 * tile_count)
    tile_y = int(
        (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * tile_count
    )
    return (
        min(max(tile_x, 0), tile_count - 1),
        min(max(tile_y, 0), tile_count - 1),
    )


def _tile_bounds(tile_x: int, tile_y: int, zoom: int) -> tuple[float, float, float, float]:
    tile_count = 1 << zoom
    west = tile_x / tile_count * 360.0 - 180.0
    east = (tile_x + 1) / tile_count * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / tile_count))))
    south = math.degrees(
        math.atan(math.sinh(math.pi * (1.0 - 2.0 * (tile_y + 1) / tile_count)))
    )
    return west, east, south, north


def _tile_range_for_bounds(
    *,
    south: float,
    north: float,
    west: float,
    east: float,
    zoom: int,
    padding: int = 0,
) -> tuple[int, int, int, int]:
    west_x, north_y = _tile_for_lat_lon(north, west, zoom)
    east_x, south_y = _tile_for_lat_lon(south, east, zoom)
    min_x, max_x = sorted((west_x, east_x))
    min_y, max_y = sorted((north_y, south_y))
    tile_count = 1 << zoom
    return (
        max(0, min_x - padding),
        min(tile_count - 1, max_x + padding),
        max(0, min_y - padding),
        min(tile_count - 1, max_y + padding),
    )


def _tile_count_in_range(tile_range: tuple[int, int, int, int]) -> int:
    min_x, max_x, min_y, max_y = tile_range
    return (max_x - min_x + 1) * (max_y - min_y + 1)


def _qimage_to_rgba_array(image: QtGui.QImage) -> np.ndarray:
    rgba = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    width = rgba.width()
    height = rgba.height()
    buffer = rgba.bits().tobytes()
    bytes_per_line = rgba.bytesPerLine()
    rows = np.frombuffer(buffer, dtype=np.uint8).reshape(height, bytes_per_line)
    return np.flipud(rows[:, : width * 4].reshape(height, width, 4)).copy()


def _sequence_value(values: Sequence[float | None], index: int) -> float:
    if not values:
        return 0.0
    clamped_index = min(max(index, 0), len(values) - 1)
    value = values[clamped_index]
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _wrap_degrees(value: float) -> float:
    wrapped = (value + 180.0) % 360.0 - 180.0
    if wrapped == -180.0 and value > 0:
        return 180.0
    return wrapped


def _format_degrees(value: float) -> str:
    cleaned = 0.0 if abs(value) < 0.05 else value
    return f"{cleaned:.1f}"


def _event_fields(event: object) -> tuple[str, str, int, str]:
    if isinstance(event, tuple):
        severity, name, time_ms, condition = event
        return str(severity), str(name), int(time_ms), str(condition)
    return (
        str(getattr(event, "severity")),
        str(getattr(event, "name")),
        int(getattr(event, "time_ms")),
        str(getattr(event, "condition")),
    )


def _circle_points(radius: float, point_count: int = 97) -> tuple[list[float], list[float]]:
    angles = [2 * math.pi * index / (point_count - 1) for index in range(point_count)]
    return (
        [math.cos(angle) * radius for angle in angles],
        [math.sin(angle) * radius for angle in angles],
    )


_GLB_JSON_CHUNK = 0x4E4F534A
_GLB_BIN_CHUNK = 0x004E4942
_GLTF_COMPONENT_FORMATS = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}
_GLTF_TYPE_COMPONENT_COUNTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def _read_glb_chunks(path: Path) -> tuple[int, int, bytes, bytes]:
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b"glTF":
            raise ValueError(f"{path} is not a GLB file")

        version, byte_length = struct.unpack("<II", header[4:12])
        json_chunk = b""
        bin_chunk = b""
        first_chunk = True

        while True:
            chunk_header = handle.read(8)
            if not chunk_header:
                break
            if len(chunk_header) != 8:
                raise ValueError(f"{path} has an incomplete GLB chunk header")
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            chunk_data = handle.read(chunk_length)
            if len(chunk_data) != chunk_length:
                raise ValueError(f"{path} has an incomplete GLB chunk")
            if first_chunk and chunk_type != _GLB_JSON_CHUNK:
                raise ValueError(f"{path} first GLB chunk is not JSON")
            first_chunk = False
            if chunk_type == _GLB_JSON_CHUNK:
                json_chunk = chunk_data
            elif chunk_type == _GLB_BIN_CHUNK and not bin_chunk:
                bin_chunk = chunk_data

    if not json_chunk:
        raise ValueError(f"{path} does not contain a GLB JSON chunk")
    return version, byte_length, json_chunk, bin_chunk


def _parse_glb_json(json_chunk: bytes) -> dict[str, Any]:
    return json.loads(json_chunk.rstrip(b" \x00\r\n\t").decode("utf-8"))


def _glb_scene_summary(
    document: dict[str, Any],
) -> tuple[int, int, tuple[float, float, float] | None, tuple[float, float, float] | None]:
    if not document:
        return 0, 0, None, None
    bounds = [
        (accessor["min"], accessor["max"])
        for accessor in document.get("accessors", [])
        if accessor.get("type") == "VEC3" and "min" in accessor and "max" in accessor
    ]
    scene_min = scene_max = None
    if bounds:
        scene_min = tuple(float(min(pair[0][axis] for pair in bounds)) for axis in range(3))
        scene_max = tuple(float(max(pair[1][axis] for pair in bounds)) for axis in range(3))
    return len(document.get("meshes", [])), len(document.get("nodes", [])), scene_min, scene_max


def _glb_mesh_primitives(
    document: dict[str, Any],
    bin_chunk: bytes,
) -> tuple[GlbMeshPrimitive, ...]:
    meshes = document.get("meshes", [])
    nodes = document.get("nodes", [])
    scenes = document.get("scenes", [])
    if not meshes or not nodes or not bin_chunk:
        return ()

    scene_index = int(document.get("scene", 0))
    if 0 <= scene_index < len(scenes):
        root_node_indices = scenes[scene_index].get("nodes", [])
    else:
        root_node_indices = []
    if not root_node_indices:
        root_node_indices = list(range(len(nodes)))

    primitives: list[GlbMeshPrimitive] = []

    def visit(node_index: int, parent_transform: np.ndarray, stack: set[int]) -> None:
        if node_index in stack or not 0 <= node_index < len(nodes):
            return
        node = nodes[node_index]
        if not isinstance(node, dict):
            return
        transform = parent_transform @ _node_transform(node)
        mesh_index = node.get("mesh")
        if isinstance(mesh_index, int) and 0 <= mesh_index < len(meshes):
            primitives.extend(
                _glb_node_mesh_primitives(document, bin_chunk, meshes[mesh_index], transform)
            )
        next_stack = {*stack, node_index}
        for child_index in node.get("children", []):
            if isinstance(child_index, int):
                visit(child_index, transform, next_stack)

    identity = np.identity(4, dtype=float)
    for root_node_index in root_node_indices:
        if isinstance(root_node_index, int):
            visit(root_node_index, identity, set())

    return tuple(primitives)


def _glb_node_mesh_primitives(
    document: dict[str, Any],
    bin_chunk: bytes,
    mesh: object,
    transform: np.ndarray,
) -> list[GlbMeshPrimitive]:
    if not isinstance(mesh, dict):
        return []

    primitives: list[GlbMeshPrimitive] = []
    for primitive in mesh.get("primitives", []):
        if not isinstance(primitive, dict) or primitive.get("mode", 4) != 4:
            continue
        attributes = primitive.get("attributes", {})
        position_accessor_index = (
            attributes.get("POSITION") if isinstance(attributes, dict) else None
        )
        if not isinstance(position_accessor_index, int):
            continue

        positions = _accessor_vec3_values(document, bin_chunk, position_accessor_index)
        if not positions:
            continue
        if isinstance(primitive.get("indices"), int):
            indices = _accessor_scalar_int_values(document, bin_chunk, primitive["indices"])
        else:
            indices = tuple(range(len(positions)))
        triangles = _triangles_from_indices(indices, len(positions))
        if not triangles:
            continue

        vertices = tuple(_transform_point(transform, position) for position in positions)
        primitives.append(GlbMeshPrimitive(vertices=vertices, triangles=triangles))

    return primitives


def _accessor_vec3_values(
    document: dict[str, Any],
    bin_chunk: bytes,
    accessor_index: int,
) -> tuple[tuple[float, float, float], ...]:
    values = _accessor_values(document, bin_chunk, accessor_index)
    vectors: list[tuple[float, float, float]] = []
    for value in values:
        if isinstance(value, tuple) and len(value) >= 3:
            vectors.append((float(value[0]), float(value[1]), float(value[2])))
    return tuple(vectors)


def _accessor_scalar_int_values(
    document: dict[str, Any],
    bin_chunk: bytes,
    accessor_index: int,
) -> tuple[int, ...]:
    values = _accessor_values(document, bin_chunk, accessor_index)
    indices: list[int] = []
    for value in values:
        if isinstance(value, tuple):
            if value:
                indices.append(int(value[0]))
        else:
            indices.append(int(value))
    return tuple(indices)


def _accessor_values(
    document: dict[str, Any],
    bin_chunk: bytes,
    accessor_index: int,
) -> tuple[float | int | tuple[float | int, ...], ...]:
    accessors = document.get("accessors", [])
    buffer_views = document.get("bufferViews", [])
    if not 0 <= accessor_index < len(accessors):
        return ()
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        return ()
    buffer_view_index = accessor.get("bufferView")
    if not isinstance(buffer_view_index, int) or not 0 <= buffer_view_index < len(buffer_views):
        return ()
    buffer_view = buffer_views[buffer_view_index]
    if not isinstance(buffer_view, dict) or int(buffer_view.get("buffer", 0)) != 0:
        return ()

    component_type = accessor.get("componentType")
    component_format = _GLTF_COMPONENT_FORMATS.get(component_type)
    component_count = _GLTF_TYPE_COMPONENT_COUNTS.get(str(accessor.get("type", "")))
    if component_format is None or component_count is None:
        return ()

    count = int(accessor.get("count", 0))
    component_size = struct.calcsize("<" + component_format)
    element_size = component_size * component_count
    stride = int(buffer_view.get("byteStride", element_size))
    byte_offset = int(buffer_view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    values: list[float | int | tuple[float | int, ...]] = []
    unpack_format = "<" + component_format * component_count

    for value_index in range(count):
        offset = byte_offset + value_index * stride
        if offset + element_size > len(bin_chunk):
            break
        unpacked = struct.unpack_from(unpack_format, bin_chunk, offset)
        if component_count == 1:
            values.append(unpacked[0])
        else:
            values.append(unpacked)

    return tuple(values)


def _triangles_from_indices(
    indices: Sequence[int],
    vertex_count: int,
) -> tuple[tuple[int, int, int], ...]:
    triangles: list[tuple[int, int, int]] = []
    for index in range(0, len(indices) - 2, 3):
        triangle = (int(indices[index]), int(indices[index + 1]), int(indices[index + 2]))
        if all(0 <= vertex_index < vertex_count for vertex_index in triangle):
            triangles.append(triangle)
    return tuple(triangles)


def _node_transform(node: dict[str, Any]) -> np.ndarray:
    matrix = node.get("matrix")
    if isinstance(matrix, list) and len(matrix) == 16:
        return np.array(matrix, dtype=float).reshape((4, 4), order="F")

    translation = np.identity(4, dtype=float)
    if isinstance(node.get("translation"), list) and len(node["translation"]) >= 3:
        translation[:3, 3] = [float(value) for value in node["translation"][:3]]

    rotation = _quaternion_matrix(node.get("rotation"))

    scale = np.identity(4, dtype=float)
    if isinstance(node.get("scale"), list) and len(node["scale"]) >= 3:
        scale[0, 0] = float(node["scale"][0])
        scale[1, 1] = float(node["scale"][1])
        scale[2, 2] = float(node["scale"][2])

    return translation @ rotation @ scale


def _quaternion_matrix(rotation: object) -> np.ndarray:
    if not isinstance(rotation, list) or len(rotation) < 4:
        return np.identity(4, dtype=float)
    x, y, z, w = (float(value) for value in rotation[:4])
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm <= 1e-12:
        return np.identity(4, dtype=float)
    x /= norm
    y /= norm
    z /= norm
    w /= norm
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0],
            [0, 0, 0, 1],
        ],
        dtype=float,
    )


def _transform_point(
    transform: np.ndarray,
    point: tuple[float, float, float],
) -> tuple[float, float, float]:
    transformed = transform @ np.array([point[0], point[1], point[2], 1.0], dtype=float)
    w = transformed[3] if abs(transformed[3]) > 1e-12 else 1.0
    return (float(transformed[0] / w), float(transformed[1] / w), float(transformed[2] / w))


def _bounds_for_primitives(
    primitives: Sequence[GlbMeshPrimitive],
) -> tuple[tuple[float, float, float] | None, tuple[float, float, float] | None]:
    vertices = [vertex for primitive in primitives for vertex in primitive.vertices]
    if not vertices:
        return None, None
    return (
        tuple(float(min(vertex[axis] for vertex in vertices)) for axis in range(3)),
        tuple(float(max(vertex[axis] for vertex in vertices)) for axis in range(3)),
    )
