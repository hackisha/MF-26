"""pyqtgraph time-series analysis window."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from typing import Callable

import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from mflog_proto.playback import CursorEvent, CursorKind, PlaybackState


SeriesMap = Mapping[str, tuple[Sequence[float], Sequence[float | None]]]


class TimeSeriesWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        parent: QtWidgets.QWidget | None = None,
        *,
        line_color: str | None = None,
        line_width: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("timeSeriesWindow")
        self._playback_state = playback_state
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._series_points: dict[str, tuple[list[float], list[float]]] = {}
        self._disposed = False
        self._line_color = line_color
        self._line_width = float(line_width)
        self._visual_style = {
            "plot_background": "#192025",
            "axis_pen": "#7f8d95",
            "axis_text": "#c4d1d8",
            "legend_background": "#1d2429",
            "cursor": "#f4c95d",
        }
        self.last_tooltip_text = ""
        self._unsubscribe: Callable[[], None] | None = playback_state.subscribe(
            self._handle_cursor_event
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.plot = pg.PlotWidget(background=self._visual_style["plot_background"])
        self.plot.setObjectName("timeSeriesPlot")
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        for axis_name in ("left", "bottom"):
            axis = self.plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(self._visual_style["axis_pen"]))
            axis.setTextPen(pg.mkPen(self._visual_style["axis_text"]))
        self.legend = self.plot.addLegend(
            offset=(10, 10),
            brush=QtGui.QBrush(QtGui.QColor(self._visual_style["legend_background"])),
            pen=pg.mkPen("#56636d"),
        )
        self.plot.scene().sigMouseMoved.connect(self._handle_mouse_moved)
        self.plot.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
        self.cursor_line = pg.InfiniteLine(
            pos=playback_state.current_seconds,
            angle=90,
            movable=False,
            pen=pg.mkPen(self._visual_style["cursor"], width=2),
        )
        self.plot.addItem(self.cursor_line)

        self.hover_label = QtWidgets.QLabel("Hover | -")
        self.hover_label.setObjectName("hoverLabel")

        layout.addWidget(self.plot, 1)
        layout.addWidget(self.hover_label)

    @property
    def channel_count(self) -> int:
        return len(self._curves)

    @property
    def channel_ids(self) -> tuple[str, ...]:
        return tuple(self._curves)

    def set_series(self, series: SeriesMap) -> None:
        prepared_series: list[tuple[str, list[float], list[float]]] = []
        for channel_id, (x_values, y_values) in series.items():
            numeric_x, numeric_y = _drop_none_pairs(x_values, y_values)
            _require_sorted_x_values(channel_id, numeric_x)
            prepared_series.append((channel_id, numeric_x, numeric_y))

        for curve in self._curves.values():
            self.plot.removeItem(curve)
        self._curves.clear()
        self._series_points.clear()

        for index, (channel_id, numeric_x, numeric_y) in enumerate(prepared_series):
            self._series_points[channel_id] = (numeric_x, numeric_y)
            curve = self.plot.plot(
                numeric_x,
                numeric_y,
                pen=self._pen_for_index(index),
                name=channel_id,
            )
            self._curves[channel_id] = curve

    def set_graph_style(self, *, line_color: str | None, line_width: float) -> None:
        self._line_color = line_color
        self._line_width = float(line_width)
        for index, curve in enumerate(self._curves.values()):
            curve.setPen(self._pen_for_index(index))

    def curve_style(self, channel_id: str) -> tuple[str, float]:
        curve = self._curves[channel_id]
        pen = curve.opts["pen"]
        return pen.color().name(), pen.widthF()

    def visual_style_summary(self) -> dict[str, str]:
        return dict(self._visual_style)

    def publish_hover(
        self,
        *,
        sample_index: int,
        channel_id: str | None = None,
        value: float | None = None,
    ) -> None:
        self._playback_state.publish_hover(
            sample_index=sample_index,
            channel_id=channel_id,
            value=value,
        )

    def seek_to_seconds(self, seconds: float) -> None:
        self._playback_state.set_seconds(seconds)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self.cursor_line.setValue(event.seconds)
            return

        detail = _hover_detail_text(event.channel_id, event.seconds, event.value)
        self.last_tooltip_text = detail
        self.hover_label.setText(f"Hover | {detail}")

    def _handle_mouse_moved(self, scene_pos: object) -> None:
        if isinstance(scene_pos, tuple | list):
            if not scene_pos:
                return
            scene_pos = scene_pos[0]
        if not isinstance(scene_pos, QtCore.QPointF):
            return
        if not self.plot.sceneBoundingRect().contains(scene_pos):
            return

        view_point = self.plot.plotItem.vb.mapSceneToView(scene_pos)
        nearest_point = self._nearest_point_to(scene_pos, view_point.x())
        if nearest_point is None:
            return

        channel_id, seconds, value = nearest_point
        self._show_hover_tooltip(scene_pos, channel_id, seconds, value)
        self._playback_state.publish_hover(
            sample_index=self._playback_state.sample_at_seconds(seconds),
            channel_id=channel_id,
            value=value,
        )

    def _show_hover_tooltip(
        self,
        scene_pos: QtCore.QPointF,
        channel_id: str,
        seconds: float,
        value: float,
    ) -> None:
        self.last_tooltip_text = _hover_detail_text(channel_id, seconds, value)
        widget_pos = self.plot.mapFromScene(scene_pos)
        global_pos = self.plot.mapToGlobal(widget_pos)
        QtWidgets.QToolTip.showText(global_pos, self.last_tooltip_text, self.plot)

    def _handle_mouse_clicked(self, event: object) -> None:
        scene_pos = getattr(event, "scenePos", lambda: None)()
        if not isinstance(scene_pos, QtCore.QPointF):
            return
        if not self.plot.sceneBoundingRect().contains(scene_pos):
            return
        view_point = self.plot.plotItem.vb.mapSceneToView(scene_pos)
        self.seek_to_seconds(view_point.x())

    def _nearest_point_to(
        self,
        scene_pos: QtCore.QPointF,
        seconds: float,
    ) -> tuple[str, float, float] | None:
        best_point: tuple[str, float, float] | None = None
        best_distance_squared: float | None = None

        for channel_id, (x_values, y_values) in self._series_points.items():
            for point_index in _candidate_indices(x_values, seconds):
                point_scene = self.plot.plotItem.vb.mapViewToScene(
                    QtCore.QPointF(x_values[point_index], y_values[point_index])
                )
                dx = point_scene.x() - scene_pos.x()
                dy = point_scene.y() - scene_pos.y()
                distance_squared = dx * dx + dy * dy
                if best_distance_squared is None or distance_squared < best_distance_squared:
                    best_distance_squared = distance_squared
                    best_point = (
                        channel_id,
                        x_values[point_index],
                        y_values[point_index],
                    )

        return best_point

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        try:
            self.plot.setUpdatesEnabled(False)
            self.plot.viewport().setUpdatesEnabled(False)
            self.plot.hide()
        except RuntimeError:
            pass
        try:
            self.plot.scene().sigMouseMoved.disconnect(self._handle_mouse_moved)
        except (RuntimeError, TypeError):
            pass
        try:
            self.plot.scene().sigMouseClicked.disconnect(self._handle_mouse_clicked)
        except (RuntimeError, TypeError):
            pass
        try:
            self.plot.clear()
        except RuntimeError:
            pass
        self._curves.clear()
        self._series_points.clear()

    def _pen_for_index(self, index: int) -> QtGui.QPen:
        color = self._line_color if self._line_color is not None else _palette_color(index)
        return pg.mkPen(color, width=self._line_width)


def _drop_none_pairs(
    x_values: Sequence[float],
    y_values: Sequence[float | None],
) -> tuple[list[float], list[float]]:
    x_output: list[float] = []
    y_output: list[float] = []
    for x_value, y_value in zip(x_values, y_values, strict=True):
        if y_value is None:
            continue
        x_output.append(float(x_value))
        y_output.append(float(y_value))
    return x_output, y_output


def _require_sorted_x_values(channel_id: str, x_values: Sequence[float]) -> None:
    if any(left > right for left, right in zip(x_values, x_values[1:])):
        raise ValueError(f"x values for {channel_id} must be sorted in ascending time order")


def _candidate_indices(x_values: Sequence[float], seconds: float) -> tuple[int, ...]:
    if not x_values:
        return ()

    insertion_index = bisect_left(x_values, seconds)
    if insertion_index <= 0:
        return (0,)
    if insertion_index >= len(x_values):
        return (len(x_values) - 1,)
    return (insertion_index - 1, insertion_index)


def _palette_color(index: int) -> str:
    colors = ("#f4c95d", "#5dade2", "#58d68d", "#ec7063", "#af7ac5", "#f5b041")
    return colors[index % len(colors)]


def _hover_detail_text(channel_id: str | None, seconds: float, value: float | None) -> str:
    parts = []
    if channel_id is not None:
        parts.append(channel_id)
    parts.append(f"{seconds:.3f} s")
    if value is not None:
        unit = _unit_for_channel(channel_id)
        unit_suffix = f" {unit}" if unit else ""
        parts.append(f"{value:.3f}{unit_suffix}")
    return " | ".join(parts)


def _unit_for_channel(channel_id: str | None) -> str:
    if channel_id is None:
        return ""
    units = {
        "RPM": "rpm",
        "TPS": "%",
        "TPS_percent": "%",
        "GPS speed": "kph",
        "VSS": "kph",
        "VSS / GPS speed": "kph",
        "Battery voltage": "V",
        "ax": "g",
        "ay": "g",
        "AX_CORRECTED_G": "g",
        "AY_CORRECTED_G": "g",
        "roll rate": "deg/s",
        "pitch rate": "deg/s",
        "yaw rate": "deg/s",
    }
    return units.get(channel_id, "")
