"""Minimal non-time-series analysis windows for the prototype."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import struct
from typing import Sequence

import pyqtgraph as pg
from PySide6 import QtGui, QtWidgets

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


class GGDiagramWindow(QtWidgets.QWidget):
    def __init__(self, playback_state: PlaybackState, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ggDiagramWindow")
        self._playback_state = playback_state
        self._points: list[tuple[float, float] | None] = []
        self._current_point: tuple[float, float] | None = None
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.plot = pg.PlotWidget(background="#1f2428")
        self.plot.setObjectName("ggDiagramPlot")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("bottom", "AX_CORRECTED_G")
        self.plot.setLabel("left", "AY_CORRECTED_G")
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
        self.plot.addItem(self.cloud_item)
        self.plot.addItem(self.current_item)
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.reliability_badge)

    @property
    def point_count(self) -> int:
        return sum(point is not None for point in self._points)

    @property
    def current_point(self) -> tuple[float, float] | None:
        return self._current_point

    def reliability_text(self) -> str:
        return self.reliability_badge.text()

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
        self.viewport = QtWidgets.QFrame()
        self.viewport.setObjectName("vehicleModelViewport")
        self.viewport.setMinimumHeight(160)
        self.viewport.setStyleSheet(
            "QFrame#vehicleModelViewport { background: #161a1d; border: 1px solid #3a4046; }"
        )
        viewport_layout = QtWidgets.QVBoxLayout(self.viewport)
        viewport_layout.setContentsMargins(10, 10, 10, 10)
        self.geometry_label = QtWidgets.QLabel(self.model_geometry_text())
        self.geometry_label.setObjectName("vehicleGeometryStatus")
        viewport_layout.addWidget(self.geometry_label)
        viewport_layout.addStretch(1)
        self.camera_label = QtWidgets.QLabel(self.camera_status_text())
        self.camera_label.setObjectName("vehicleCameraStatus")
        self.reliability_badge = QtWidgets.QLabel("Reliability: info")
        self.reliability_badge.setObjectName("reliabilityBadge")
        layout.addWidget(self.model_label)
        layout.addWidget(self.viewport, 1)
        layout.addWidget(self.camera_label)
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
