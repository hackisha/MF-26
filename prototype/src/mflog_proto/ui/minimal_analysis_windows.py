"""Minimal non-time-series analysis windows for the prototype."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import tempfile
from typing import Protocol, Sequence
import urllib.error
import urllib.request

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from mflog_proto.benchmark.metrics import EnvironmentInfo
from mflog_proto.playback import CursorEvent, CursorKind, PlaybackState


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

    @property
    def has_visible_geometry(self) -> bool:
        return self.mesh_count > 0 and self.node_count > 0

    @property
    def has_scene_bounds(self) -> bool:
        return self.scene_min is not None and self.scene_max is not None


@dataclass(frozen=True)
class MapTileImage:
    image: QtGui.QImage
    west: float
    east: float
    south: float
    north: float


class MapTileProvider(Protocol):
    def tile_for_bounds(
        self,
        *,
        latitudes: Sequence[float],
        longitudes: Sequence[float],
    ) -> MapTileImage | None:
        """Return a map tile image covering or near the requested GPS bounds."""


class OpenStreetMapTileProvider:
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
        center_latitude = (south + north) / 2
        center_longitude = (west + east) / 2
        zoom = _zoom_for_span(abs(north - south), abs(east - west))
        tile_x, tile_y = _tile_for_lat_lon(center_latitude, center_longitude, zoom)
        image = self._load_tile(zoom, tile_x, tile_y)
        if image is None:
            return None

        tile_west, tile_east, tile_south, tile_north = _tile_bounds(tile_x, tile_y, zoom)
        return MapTileImage(
            image=image,
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
        self._tile_provider = tile_provider if tile_provider is not None else OpenStreetMapTileProvider()
        self._positions: list[tuple[float, float] | None] = []
        self._current_position: tuple[float, float] | None = None
        self._route_background_point_count = 0
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
        self.map_tile_item = pg.ImageItem(axisOrder="row-major")
        self.route_background_item = pg.PlotDataItem(
            pen=pg.mkPen(QtGui.QColor(93, 173, 226, 90), width=5)
        )
        self.track_item = pg.PlotDataItem(pen=pg.mkPen("#5dade2", width=1.5))
        self.current_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#f4c95d", width=2),
            brush=pg.mkBrush("#f4c95d"),
            size=11,
        )
        self.map_tile_item.setZValue(-10)
        self.map_tile_item.setVisible(False)
        self.route_background_item.setZValue(0)
        self.track_item.setZValue(5)
        self.current_item.setZValue(10)
        self.plot.addItem(self.map_tile_item)
        self.plot.addItem(self.route_background_item)
        self.plot.addItem(self.track_item)
        self.plot.addItem(self.current_item)
        self.map_background_label = QtWidgets.QLabel(self.map_background_text())
        self.map_background_label.setObjectName("gpsMapBackgroundStatus")
        self.hover_label = QtWidgets.QLabel("Hover | -")
        self.hover_label.setObjectName("hoverLabel")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.map_background_label)
        layout.addWidget(self.hover_label)
        layout.addWidget(self.reliability_badge)

    @property
    def point_count(self) -> int:
        return sum(position is not None for position in self._positions)

    @property
    def route_background_point_count(self) -> int:
        return self._route_background_point_count

    @property
    def current_position(self) -> tuple[float, float] | None:
        return self._current_position

    @property
    def map_background_enabled(self) -> bool:
        return self._map_background_enabled

    @property
    def map_tile_loaded(self) -> bool:
        return self._map_tile_loaded

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

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def set_track(
        self,
        *,
        latitude: Sequence[float | None],
        longitude: Sequence[float | None],
    ) -> None:
        self._positions = []
        plot_longitudes: list[float] = []
        plot_latitudes: list[float] = []
        valid_count = 0
        for latitude_value, longitude_value in zip(latitude, longitude, strict=True):
            if not _is_valid_gps_position(latitude_value, longitude_value):
                self._positions.append(None)
                plot_latitudes.append(math.nan)
                plot_longitudes.append(math.nan)
                continue
            position = (float(latitude_value), float(longitude_value))
            self._positions.append(position)
            plot_latitudes.append(position[0])
            plot_longitudes.append(position[1])
            valid_count += 1

        self._route_background_point_count = valid_count
        self.route_background_item.setData(plot_longitudes, plot_latitudes)
        self.track_item.setData(plot_longitudes, plot_latitudes)
        self._refresh_map_background()
        self._update_current_position(self._playback_state.current_sample)

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
            return
        clamped = min(max(sample_index, 0), len(self._positions) - 1)
        self._current_position = self._positions[clamped]
        if self._current_position is None:
            self.current_item.setData([])
        else:
            latitude, longitude = self._current_position
            self.current_item.setData([{"pos": (longitude, latitude)}])

    def _refresh_map_background(self) -> None:
        if not self._map_background_enabled:
            return

        positions = [position for position in self._positions if position is not None]
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

    def _handle_mouse_moved(self, scene_pos: object) -> None:
        scene_pos = _single_scene_point(scene_pos)
        if scene_pos is None or not self.plot.sceneBoundingRect().contains(scene_pos):
            return
        plot_positions = [
            None if position is None else (position[1], position[0])
            for position in self._positions
        ]
        nearest = _nearest_indexed_point(self.plot, scene_pos, plot_positions)
        if nearest is None:
            return
        sample_index, (longitude, latitude) = nearest
        detail = _gps_hover_text(
            seconds=self._playback_state.seconds_at(sample_index),
            latitude=latitude,
            longitude=longitude,
        )
        self._show_hover_tooltip(scene_pos, detail)
        self._playback_state.publish_hover(
            sample_index=sample_index,
            channel_id="GPS",
            value=None,
        )

    def _show_hover_tooltip(self, scene_pos: QtCore.QPointF, detail: str) -> None:
        self.last_tooltip_text = detail
        self.hover_label.setText(f"Hover | {detail}")
        widget_pos = self.plot.mapFromScene(scene_pos)
        global_pos = self.plot.mapToGlobal(widget_pos)
        QtWidgets.QToolTip.showText(global_pos, detail, self.plot)


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
    def __init__(self, model_info: GlbModelInfo, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vehicleModelViewport")
        self._model_info = model_info
        self.setMinimumHeight(160)

    @property
    def has_rendered_model(self) -> bool:
        return self._model_info.has_visible_geometry and self._model_info.has_scene_bounds

    def preview_status_text(self) -> str:
        return "Rendered GLB preview" if self.has_rendered_model else "No visible GLB geometry"

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

        self._draw_bounds_preview(painter, rect.adjusted(18, 18, -18, -18))

    def _draw_bounds_preview(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        assert self._model_info.scene_min is not None
        assert self._model_info.scene_max is not None
        min_x, min_y, min_z = self._model_info.scene_min
        max_x, max_y, max_z = self._model_info.scene_max
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        span_z = max(max_z - min_z, 1e-6)
        scale = min(rect.width() / (span_x + span_y * 0.35), rect.height() / (span_z + span_y * 0.25)) * 0.72
        origin = QtCore.QPointF(rect.center().x(), rect.center().y())

        def project(point: tuple[float, float, float]) -> QtCore.QPointF:
            x, y, z = point
            px = (x - center_x) * scale + (y - center_y) * scale * 0.25
            py = -(z - center_z) * scale - (y - center_y) * scale * 0.18
            return QtCore.QPointF(origin.x() + px, origin.y() + py)

        corners = [
            (min_x, min_y, min_z),
            (max_x, min_y, min_z),
            (max_x, max_y, min_z),
            (min_x, max_y, min_z),
            (min_x, min_y, max_z),
            (max_x, min_y, max_z),
            (max_x, max_y, max_z),
            (min_x, max_y, max_z),
        ]
        projected = [project(corner) for corner in corners]
        edges = (
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        )

        painter.setPen(QtGui.QPen(QtGui.QColor("#5dade2"), 2))
        for left, right in edges:
            painter.drawLine(projected[left], projected[right])

        painter.setBrush(QtGui.QBrush(QtGui.QColor(244, 201, 93, 120)))
        painter.setPen(QtGui.QPen(QtGui.QColor("#f4c95d"), 1))
        painter.drawEllipse(projected[0], 3, 3)
        painter.drawEllipse(projected[6], 3, 3)
        painter.setPen(QtGui.QColor("#c8d2dc"))
        painter.drawText(
            rect.adjusted(4, 4, -4, -4),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop,
            self.preview_status_text(),
        )


class VehicleModelWindow(QtWidgets.QWidget):
    def __init__(self, model_info: GlbModelInfo, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vehicleModelWindow")
        self._model_info = model_info
        self._rendering_enabled = True

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
        self.qualitative_note = QtWidgets.QLabel(self.qualitative_note_text())
        self.qualitative_note.setObjectName("vehicleQualitativeNote")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.model_label)
        layout.addWidget(self.viewport, 1)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.qualitative_note)
        layout.addWidget(self.reliability_badge)

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

    def preview_status_text(self) -> str:
        return self.viewport.preview_status_text()

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        self._rendering_enabled = True
        self.camera_label.setText(self.camera_status_text())
        super().showEvent(event)

    def hideEvent(self, event: QtGui.QHideEvent) -> None:  # noqa: N802
        self._rendering_enabled = False
        self.camera_label.setText(self.camera_status_text())
        super().hideEvent(event)


def load_glb_info(path: Path) -> GlbModelInfo:
    with path.open("rb") as handle:
        header = handle.read(12)
        first_chunk_header = handle.read(8)
        json_chunk = b""
    if len(header) != 12 or header[:4] != b"glTF":
        raise ValueError(f"{path} is not a GLB file")
    version, byte_length = struct.unpack("<II", header[4:12])
    json_chunk_length = 0
    bin_chunk_length = 0
    if len(first_chunk_header) == 8:
        chunk_length, chunk_type = struct.unpack("<II", first_chunk_header)
        if chunk_type != 0x4E4F534A:
            raise ValueError(f"{path} first GLB chunk is not JSON")
        json_chunk_length = chunk_length
        with path.open("rb") as handle:
            handle.seek(20)
            json_chunk = handle.read(json_chunk_length)
            handle.seek(20 + json_chunk_length)
            second_chunk_header = handle.read(8)
        if len(second_chunk_header) == 8:
            bin_chunk_length = struct.unpack("<II", second_chunk_header)[0]
    mesh_count, node_count, scene_min, scene_max = _glb_scene_summary(json_chunk)
    return GlbModelInfo(
        path=path,
        version=version,
        byte_length=byte_length,
        json_chunk_length=json_chunk_length,
        bin_chunk_length=bin_chunk_length,
        mesh_count=mesh_count,
        node_count=node_count,
        scene_min=scene_min,
        scene_max=scene_max,
    )


def _format_kib(byte_length: int) -> str:
    return f"{byte_length / 1024:.1f} KB"


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
    if span <= 0.01:
        return 15
    if span <= 0.05:
        return 14
    if span <= 0.1:
        return 13
    if span <= 0.5:
        return 11
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


def _qimage_to_rgba_array(image: QtGui.QImage) -> np.ndarray:
    rgba = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    width = rgba.width()
    height = rgba.height()
    buffer = rgba.bits().tobytes()
    bytes_per_line = rgba.bytesPerLine()
    rows = np.frombuffer(buffer, dtype=np.uint8).reshape(height, bytes_per_line)
    return rows[:, : width * 4].reshape(height, width, 4).copy()


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


def _glb_scene_summary(
    json_chunk: bytes,
) -> tuple[int, int, tuple[float, float, float] | None, tuple[float, float, float] | None]:
    if not json_chunk:
        return 0, 0, None, None
    document = json.loads(json_chunk.decode("utf-8"))
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
