"""Main application shell for the PySide6 prototype."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import math
from pathlib import Path
import sys
from typing import Any, Callable, Sequence

from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

from mflog_proto.analysis.dynamics import compute_dynamics_summary
from mflog_proto.analysis.event_reviews import (
    EventReview,
    EventReviewState,
    build_event_reviews,
)
from mflog_proto.analysis.kinematics import compute_ideal_path
from mflog_proto.analysis.reference_route import (
    ReferenceRoute,
    load_reference_route,
    save_reference_route,
)
from mflog_proto.analysis.segments import (
    AnalysisSegment,
    SegmentSummary,
    compute_segment_summary,
)
from mflog_proto.benchmark.metrics import collect_environment
from mflog_proto.data.column_store import ColumnStore
from mflog_proto.data.csv_loader import CsvLoadOptions, load_csv
from mflog_proto.data.derived import compute_basic_derived_channels
from mflog_proto.diagnostics.app_logging import log_exception
from mflog_proto.persistence.project_state import (
    ProjectState,
    WindowState,
    load_project_state,
    save_project_state,
)
from mflog_proto.playback import CursorEvent, CursorKind, PlaybackState
from mflog_proto.reporting.html_report import render_html_report, write_html_report
from mflog_proto.ui.minimal_analysis_windows import (
    BenchmarkSummaryWindow,
    CurrentValuesWindow,
    DataAnalysisWindow,
    DocumentsWindow,
    EventReviewWindow,
    ExportReportWindow,
    GaugeIndicatorsWindow,
    GGDiagramWindow,
    GPSMapWindow,
    GPSRouteLayer,
    MapTileProvider,
    SegmentAnalysisWindow,
    TireTemperatureWindow,
    VehicleDynamicsWindow,
    VehicleModelWindow,
    VideoSyncWindow,
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
class IdealPathSettings:
    enabled: bool = False
    wheelbase_m: float = 1.6
    steering_ratio: float = 1.0
    steering_channel: str = "Auto"


@dataclass(frozen=True)
class SidebarSettings:
    search_visible: bool = True
    add_button_visible: bool = True
    sort_mode: str = "Default"
    density: str = "Comfortable"
    width_px: int = 260


@dataclass(frozen=True)
class AnalysisPresetMode:
    windows: tuple[str, ...]
    channels: tuple[str, ...] = ()
    focus_window: str = ""


def _drawn_playback_icon(kind: str) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    color = QtGui.QColor("#f4f8fb")
    accent = QtGui.QColor("#f4c95d")
    painter.setPen(QtCore.Qt.PenStyle.NoPen)

    def draw_polygon(points: Sequence[tuple[float, float]], brush: QtGui.QColor = color) -> None:
        painter.setBrush(brush)
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in points]))

    def draw_rect(x: float, y: float, width: float, height: float, brush: QtGui.QColor = color) -> None:
        painter.setBrush(brush)
        painter.drawRoundedRect(QtCore.QRectF(x, y, width, height), 0.8, 0.8)

    if kind == "play":
        draw_polygon(((8, 6), (8, 18), (18, 12)))
    elif kind == "pause":
        draw_rect(7, 6, 3.8, 12)
        draw_rect(13.2, 6, 3.8, 12)
    elif kind == "stop":
        draw_rect(8, 8, 8, 8)
    elif kind == "skip_backward":
        draw_rect(5, 6, 2.2, 12)
        draw_polygon(((18, 6), (11, 12), (18, 18)))
        draw_polygon(((12, 6), (5, 12), (12, 18)))
    elif kind == "skip_forward":
        draw_polygon(((6, 6), (13, 12), (6, 18)))
        draw_polygon(((12, 6), (19, 12), (12, 18)))
        draw_rect(19, 6, 2.2, 12)
    elif kind == "prev_event":
        draw_polygon(((12, 6), (5, 12), (12, 18)))
        draw_polygon(((17, 7.2), (21, 12), (17, 16.8), (13, 12)), accent)
    elif kind == "next_event":
        draw_polygon(((7, 7.2), (11, 12), (7, 16.8), (3, 12)), accent)
        draw_polygon(((12, 6), (19, 12), (12, 18)))
    else:
        draw_rect(8, 8, 8, 8)

    painter.end()
    return QtGui.QIcon(pixmap)


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


def _clamp_analysis_opacity(value: float) -> float:
    return max(0.35, min(1.0, float(value)))


class _AnalysisTitleBar(QtWidgets.QFrame):
    def __init__(
        self,
        sub_window: QtWidgets.QMdiSubWindow,
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("analysisWindowTitleBar")
        self.setProperty("active", False)
        self.setFixedHeight(28)
        self._sub_window = sub_window
        self._drag_offset = QtCore.QPoint()
        self._dragging = False
        self.setStyleSheet(
            """
            QFrame#analysisWindowTitleBar {
                background: #334450;
                border-bottom: 1px solid #6b7d87;
            }
            QFrame#analysisWindowTitleBar[active="true"] {
                background: #405665;
            }
            QLabel#analysisWindowTitleLabel {
                background: transparent;
                color: #f4f8fb;
                font-weight: 600;
                padding-left: 7px;
            }
            QToolButton {
                background: transparent;
                border: none;
                color: #f4f8fb;
                font-weight: 700;
            }
            QToolButton:hover {
                background: #4f6675;
            }
            QToolButton#analysisWindowCloseButton:hover {
                background: #9f4d4d;
            }
            QFrame#analysisWindowOpacityPopup {
                background: #f3f5f6;
                border: 1px solid #b9c4ca;
            }
            QLabel#analysisWindowOpacityIcon,
            QLabel#analysisWindowOpacityValue {
                color: #1f2a30;
                background: transparent;
                font-weight: 700;
            }
            QSlider#analysisWindowOpacitySlider::groove:horizontal {
                height: 5px;
                background: #a6a8aa;
                border: none;
            }
            QSlider#analysisWindowOpacitySlider::sub-page:horizontal {
                background: #178297;
            }
            QSlider#analysisWindowOpacitySlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: #178297;
                border: 2px solid #ffffff;
            }
            """
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 4, 0)
        layout.setSpacing(2)

        self._title_label = QtWidgets.QLabel(title)
        self._title_label.setObjectName("analysisWindowTitleLabel")
        self._title_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft
        )

        self._minimize_button = self._make_button(
            object_name="analysisWindowMinimizeButton",
            text="-",
            tooltip="Minimize",
        )
        self._restore_button = self._make_button(
            object_name="analysisWindowRestoreButton",
            text="[]",
            tooltip="Maximize / restore",
        )
        self._opacity_button = self._make_button(
            object_name="analysisWindowOpacityButton",
            text="O",
            tooltip="Window opacity",
        )
        self._opacity_popup = self._build_opacity_popup()
        self._close_button = self._make_button(
            object_name="analysisWindowCloseButton",
            text="x",
            tooltip="Close",
        )

        layout.addWidget(self._title_label, 1)
        layout.addWidget(self._opacity_button)
        layout.addWidget(self._minimize_button)
        layout.addWidget(self._restore_button)
        layout.addWidget(self._close_button)

        self._opacity_button.clicked.connect(self._toggle_opacity_popup)
        self._minimize_button.clicked.connect(sub_window.showMinimized)
        self._restore_button.clicked.connect(self._toggle_maximized)
        self._close_button.clicked.connect(sub_window.close)
        self.update_restore_button()

    def set_active(self, active: bool) -> None:
        if self.property("active") == active:
            return
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_opacity_value(self, opacity: float) -> None:
        value = round(_clamp_analysis_opacity(opacity) * 100)
        blocker = QtCore.QSignalBlocker(self.opacity_slider)
        self.opacity_slider.setValue(value)
        del blocker
        self.opacity_value_label.setText(f"{value}%")

    def update_restore_button(self) -> None:
        is_maximized = (
            self._sub_window.isMaximized()
            or bool(self._sub_window.windowState() & QtCore.Qt.WindowState.WindowMaximized)
        )
        self._restore_button.setText("[]" if is_maximized else "[ ]")

    def _build_opacity_popup(self) -> QtWidgets.QFrame:
        popup = QtWidgets.QFrame(self, QtCore.Qt.WindowType.Popup)
        popup.setObjectName("analysisWindowOpacityPopup")
        popup.setFixedSize(260, 54)
        layout = QtWidgets.QHBoxLayout(popup)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)

        icon = QtWidgets.QLabel("O")
        icon.setObjectName("analysisWindowOpacityIcon")
        icon.setFixedWidth(18)
        icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName("analysisWindowOpacitySlider")
        self.opacity_slider.setRange(35, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("Window opacity")
        self.opacity_value_label = QtWidgets.QLabel("100%")
        self.opacity_value_label.setObjectName("analysisWindowOpacityValue")
        self.opacity_value_label.setFixedWidth(42)
        self.opacity_value_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(icon)
        layout.addWidget(self.opacity_slider, 1)
        layout.addWidget(self.opacity_value_label)
        self.opacity_slider.valueChanged.connect(self._set_window_opacity_from_slider)
        return popup

    def _toggle_opacity_popup(self) -> None:
        if self._opacity_popup.isVisible():
            self._opacity_popup.hide()
            return
        self._opacity_popup.adjustSize()
        below_button = self._opacity_button.mapToGlobal(
            QtCore.QPoint(
                -self._opacity_popup.width() + self._opacity_button.width(),
                self._opacity_button.height() + 4,
            )
        )
        self._opacity_popup.move(below_button)
        self._opacity_popup.show()
        self._opacity_popup.raise_()

    def _set_window_opacity_from_slider(self, value: int) -> None:
        self.opacity_value_label.setText(f"{value}%")
        setter = getattr(self._sub_window, "set_analysis_opacity", None)
        if callable(setter):
            setter(value / 100.0)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self._sub_window.pos()
            mdi_area = self._sub_window.mdiArea()
            if mdi_area is not None:
                mdi_area.setActiveSubWindow(self._sub_window)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._sub_window.isMaximized():
                return
            self._sub_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _toggle_maximized(self) -> None:
        if self._sub_window.isMaximized():
            self._sub_window.showNormal()
        else:
            self._sub_window.showMaximized()
        self.update_restore_button()

    def _make_button(
        self,
        *,
        object_name: str,
        text: str,
        tooltip: str,
    ) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self)
        button.setObjectName(object_name)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedSize(28, 24)
        button.setAutoRaise(True)
        return button


class _AnalysisResizeHandle(QtWidgets.QFrame):
    HANDLE_SIZE = 8
    CORNER_SIZE = 14

    def __init__(
        self,
        sub_window: QtWidgets.QMdiSubWindow,
        *,
        name: str,
        horizontal: int,
        vertical: int,
        cursor_shape: QtCore.Qt.CursorShape,
        parent: QtWidgets.QWidget,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(f"analysisWindowResizeHandle{name}")
        self.setCursor(QtGui.QCursor(cursor_shape))
        self.setMouseTracking(True)
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
            }
            QFrame:hover {
                background: rgba(244, 201, 93, 55);
            }
            """
        )
        self._sub_window = sub_window
        self._horizontal = horizontal
        self._vertical = vertical
        self._dragging = False
        self._press_global_pos = QtCore.QPoint()
        self._press_geometry = QtCore.QRect()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._sub_window.isMaximized():
                return
            mdi_area = self._sub_window.mdiArea()
            if mdi_area is not None:
                mdi_area.setActiveSubWindow(self._sub_window)
            self._dragging = True
            self._press_global_pos = event.globalPosition().toPoint()
            self._press_geometry = self._sub_window.geometry()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._press_global_pos
        self._sub_window.setGeometry(self._resized_geometry(delta))
        event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _resized_geometry(self, delta: QtCore.QPoint) -> QtCore.QRect:
        geometry = QtCore.QRect(self._press_geometry)
        min_width = max(self._sub_window.minimumWidth(), 220)
        min_height = max(self._sub_window.minimumHeight(), 150)
        fixed_right = self._press_geometry.x() + self._press_geometry.width()
        fixed_bottom = self._press_geometry.y() + self._press_geometry.height()

        if self._horizontal > 0:
            geometry.setWidth(max(min_width, self._press_geometry.width() + delta.x()))
        elif self._horizontal < 0:
            width = max(min_width, self._press_geometry.width() - delta.x())
            geometry.setX(fixed_right - width)
            geometry.setWidth(width)

        if self._vertical > 0:
            geometry.setHeight(max(min_height, self._press_geometry.height() + delta.y()))
        elif self._vertical < 0:
            height = max(min_height, self._press_geometry.height() - delta.y())
            geometry.setY(fixed_bottom - height)
            geometry.setHeight(height)

        return geometry


class _AnalysisWindowFrame(QtWidgets.QFrame):
    def __init__(
        self,
        sub_window: QtWidgets.QMdiSubWindow,
        title: str,
        content: QtWidgets.QWidget,
    ) -> None:
        super().__init__()
        self.setObjectName("analysisWindowFrame")
        self.setProperty("active", False)
        self.title_bar = _AnalysisTitleBar(sub_window, title, self)
        self.content = content
        self._resize_handles = self._make_resize_handles(sub_window)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addWidget(content, 1)
        self._update_resize_handle_geometry()

    def set_active(self, active: bool) -> None:
        if self.property("active") == active:
            return
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_resize_handle_geometry()

    def _make_resize_handles(
        self,
        sub_window: QtWidgets.QMdiSubWindow,
    ) -> dict[str, _AnalysisResizeHandle]:
        specs: tuple[tuple[str, int, int, QtCore.Qt.CursorShape], ...] = (
            ("TopLeft", -1, -1, QtCore.Qt.CursorShape.SizeFDiagCursor),
            ("Top", 0, -1, QtCore.Qt.CursorShape.SizeVerCursor),
            ("TopRight", 1, -1, QtCore.Qt.CursorShape.SizeBDiagCursor),
            ("Right", 1, 0, QtCore.Qt.CursorShape.SizeHorCursor),
            ("BottomRight", 1, 1, QtCore.Qt.CursorShape.SizeFDiagCursor),
            ("Bottom", 0, 1, QtCore.Qt.CursorShape.SizeVerCursor),
            ("BottomLeft", -1, 1, QtCore.Qt.CursorShape.SizeBDiagCursor),
            ("Left", -1, 0, QtCore.Qt.CursorShape.SizeHorCursor),
        )
        return {
            name: _AnalysisResizeHandle(
                sub_window,
                name=name,
                horizontal=horizontal,
                vertical=vertical,
                cursor_shape=cursor_shape,
                parent=self,
            )
            for name, horizontal, vertical, cursor_shape in specs
        }

    def _update_resize_handle_geometry(self) -> None:
        width = self.width()
        height = self.height()
        side = _AnalysisResizeHandle.HANDLE_SIZE
        corner = _AnalysisResizeHandle.CORNER_SIZE
        self._resize_handles["TopLeft"].setGeometry(0, 0, corner, corner)
        self._resize_handles["Top"].setGeometry(corner, 0, max(0, width - corner * 2), side)
        self._resize_handles["TopRight"].setGeometry(width - corner, 0, corner, corner)
        self._resize_handles["Right"].setGeometry(width - side, corner, side, max(0, height - corner * 2))
        self._resize_handles["BottomRight"].setGeometry(
            width - corner,
            height - corner,
            corner,
            corner,
        )
        self._resize_handles["Bottom"].setGeometry(
            corner,
            height - side,
            max(0, width - corner * 2),
            side,
        )
        self._resize_handles["BottomLeft"].setGeometry(0, height - corner, corner, corner)
        self._resize_handles["Left"].setGeometry(0, corner, side, max(0, height - corner * 2))
        for handle in self._resize_handles.values():
            handle.raise_()


class _AnalysisSubWindow(QtWidgets.QMdiSubWindow):
    analysisOpacityChanged = QtCore.Signal(float)

    def __init__(self, content: QtWidgets.QWidget, title: str) -> None:
        super().__init__()
        self._analysis_widget = content
        self._analysis_opacity = 1.0
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(content)
        content.setGraphicsEffect(self._opacity_effect)
        self._frame = _AnalysisWindowFrame(self, title, content)
        self.setObjectName("analysisSubWindow")
        self.setWindowTitle(title)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
        self.setWidget(self._frame)
        self.set_analysis_opacity(1.0, emit_changed=False)

    def widget(self) -> QtWidgets.QWidget:  # type: ignore[override]
        return self._analysis_widget

    def frame_widget(self) -> _AnalysisWindowFrame:
        return self._frame

    def analysis_opacity(self) -> float:
        return self._analysis_opacity

    def set_analysis_opacity(self, opacity: float, *, emit_changed: bool = True) -> None:
        value = _clamp_analysis_opacity(opacity)
        if math.isclose(value, self._analysis_opacity, rel_tol=0.0, abs_tol=0.001):
            self._frame.title_bar.set_opacity_value(value)
            return
        self._analysis_opacity = value
        self._opacity_effect.setOpacity(value)
        self._frame.title_bar.set_opacity_value(value)
        if emit_changed:
            self.analysisOpacityChanged.emit(value)

    def setWindowTitle(self, title: str) -> None:  # noqa: N802
        super().setWindowTitle(title)
        if hasattr(self, "_frame"):
            self._frame.title_bar.set_title(title)

    def set_title_active(self, active: bool) -> None:
        self._frame.title_bar.set_active(active)
        self._frame.set_active(active)

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            self._frame.title_bar.update_restore_button()


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
    "Vehicle Dynamics",
    "Segment Analysis",
    "Event Review",
    "GPS Map",
    "G-G Diagram",
    "Gauge Indicators",
    "Tire Temperature",
    "Video Sync",
    "3D Vehicle Model",
    "Current Values Table",
    "Benchmark Summary",
    "Export Report",
    "Documents",
)

SIDEBAR_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "Time-Series Graph": ("시계열", "그래프", "plot", "센서"),
    "Data Analysis": ("데이터", "분석", "통계", "요약"),
    "Vehicle Dynamics": ("차량동역학", "동역학", "거동", "yaw", "understeer"),
    "Segment Analysis": ("구간", "랩", "코너", "세그먼트"),
    "Event Review": ("이벤트", "이상", "경고", "리뷰"),
    "GPS Map": ("지도", "gps", "경로", "트랙", "위치"),
    "G-G Diagram": ("gg", "g-g", "가속도", "한계원"),
    "Gauge Indicators": ("게이지", "속도계", "rpm", "속도"),
    "Tire Temperature": ("타이어", "온도", "타이어온도"),
    "Video Sync": ("영상", "비디오", "고프로", "gopro", "sync"),
    "3D Vehicle Model": ("3d", "모델", "차량모델", "glb"),
    "Current Values Table": ("현재값", "센서값", "값", "테이블"),
    "Benchmark Summary": ("벤치마크", "성능", "환경"),
    "Export Report": ("리포트", "보고서", "내보내기", "html"),
    "Documents": ("문서", "자료", "docs"),
}

SIDEBAR_GROUPS: dict[str, tuple[str, ...]] = {
    "시각화": (
        "Time-Series Graph",
        "GPS Map",
        "G-G Diagram",
        "Gauge Indicators",
        "Tire Temperature",
        "Video Sync",
        "3D Vehicle Model",
        "Current Values Table",
    ),
    "분석": ("Data Analysis", "Vehicle Dynamics", "Segment Analysis", "Event Review"),
    "리포트": ("Benchmark Summary", "Export Report"),
    "문서": ("Documents",),
}


WORKSPACE_LAYOUT_PRESETS: dict[str, tuple[str, ...]] = {
    "Drive Review": (
        "Time-Series Graph",
        "GPS Map",
        "G-G Diagram",
        "Vehicle Dynamics",
    ),
    "GPS / Line": (
        "GPS Map",
        "Time-Series Graph",
        "Segment Analysis",
    ),
    "Dynamics": (
        "G-G Diagram",
        "Vehicle Dynamics",
        "3D Vehicle Model",
        "Time-Series Graph",
    ),
    "Sensor Debug": (
        "Time-Series Graph",
        "Current Values Table",
        "Data Analysis",
        "Event Review",
    ),
}

PRESET_TAB_MODES: tuple[AnalysisPresetMode, ...] = (
    AnalysisPresetMode(
        windows=("Time-Series Graph", "GPS Map", "G-G Diagram", "Vehicle Dynamics"),
        channels=(
            "RPM",
            "TPS_percent",
            "VSS / GPS speed",
            "AX_CORRECTED_G",
            "AY_CORRECTED_G",
            "yaw rate",
        ),
        focus_window="Time-Series Graph",
    ),
    AnalysisPresetMode(
        windows=("GPS Map", "Time-Series Graph", "Segment Analysis"),
        channels=("GPS speed", "VSS / GPS speed", "yaw rate"),
        focus_window="GPS Map",
    ),
    AnalysisPresetMode(
        windows=(
            "Time-Series Graph",
            "Data Analysis",
            "Current Values Table",
            "Event Review",
        ),
        channels=("Battery voltage", "VSS / GPS speed", "RPM"),
        focus_window="Time-Series Graph",
    ),
    AnalysisPresetMode(
        windows=(
            "Time-Series Graph",
            "Data Analysis",
            "Event Review",
            "Current Values Table",
        ),
        channels=("RPM", "TPS_percent", "Battery voltage", "yaw rate"),
        focus_window="Time-Series Graph",
    ),
    AnalysisPresetMode(
        windows=("Time-Series Graph", "Data Analysis", "Event Review"),
        channels=("TPS_percent", "RPM", "VSS / GPS speed"),
        focus_window="Time-Series Graph",
    ),
    AnalysisPresetMode(
        windows=("Time-Series Graph", "Current Values Table", "Event Review"),
        channels=("Battery voltage", "RPM", "TPS_percent"),
        focus_window="Time-Series Graph",
    ),
    AnalysisPresetMode(
        windows=("Time-Series Graph", "G-G Diagram", "Vehicle Dynamics"),
        channels=(
            "AX_CORRECTED_G",
            "AY_CORRECTED_G",
            "roll rate",
            "pitch rate",
            "yaw rate",
        ),
        focus_window="G-G Diagram",
    ),
    AnalysisPresetMode(
        windows=("Data Analysis", "Vehicle Dynamics", "Segment Analysis", "Export Report"),
        channels=("RPM", "VSS / GPS speed", "AX_CORRECTED_G", "AY_CORRECTED_G"),
        focus_window="Data Analysis",
    ),
    AnalysisPresetMode(
        windows=("Documents", "Export Report", "Benchmark Summary"),
        focus_window="Documents",
    ),
    AnalysisPresetMode(
        windows=("Time-Series Graph", "GPS Map", "G-G Diagram", "Current Values Table"),
        channels=("RPM", "TPS_percent"),
        focus_window="Time-Series Graph",
    ),
)

PRESET_TAB_WINDOW_SETS: tuple[tuple[str, ...], ...] = tuple(
    mode.windows for mode in PRESET_TAB_MODES
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
        self.ideal_path_settings = IdealPathSettings()
        self.reference_route = ReferenceRoute(name="Reference route", points=())
        self.reference_route_path: Path | None = None
        self.video_path: Path | None = None
        self.video_offset_ms = 0
        self.video_muted = True
        self.sidebar_settings = SidebarSettings()
        self.vehicle_model_path = _root_asset_path("car.glb")
        self.vehicle_model_info = load_glb_info(self.vehicle_model_path)
        self.gps_route_layers: dict[str, GPSRouteLayer] = {}
        self.active_gps_route_name = ""
        self.window_opacity_defaults: dict[str, float] = {}
        self._map_tile_provider = map_tile_provider
        self.playback_state = PlaybackState([0.0])
        self.sensor_series = _blank_sensor_series(self.playback_state.sample_count)
        self.available_sensor_channels: set[str] = set()
        self.playback_events: tuple[PlaybackMarker, ...] = ()
        self.event_reviews: tuple[EventReview, ...] = ()
        self.analysis_segments: tuple[AnalysisSegment, ...] = ()
        self.report_output_path: Path | None = None
        self.selected_sidebar_group = "시각화"
        self.session_row_count = 0
        self.session_sampling_interval_ms = 0
        self._syncing_event_marker_selection = False
        self._syncing_time_series_channel_checks = False
        self._syncing_ideal_path_controls = False
        self._syncing_reference_route_windows = False
        self._syncing_preset_tabs = False
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
            reference_route_path=self.reference_route_path,
            reference_route_name=self.reference_route.name,
            video_path=self.video_path,
            video_offset_ms=self.video_offset_ms,
            video_muted=self.video_muted,
            visualization_settings=_visualization_settings_to_dict(
                self.visualization_settings
            ),
            ideal_path_settings=_ideal_path_settings_to_dict(self.ideal_path_settings),
            sidebar_settings=_sidebar_settings_to_dict(self.sidebar_settings),
            event_reviews=self.event_reviews,
            analysis_segments=self.analysis_segments,
            selected_sidebar_group=self.selected_sidebar_group,
            report_output_path=self.report_output_path,
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
        self.visualization_settings = _visualization_settings_from_dict(
            state.visualization_settings,
            fallback=self.visualization_settings,
        )
        self.ideal_path_settings = _ideal_path_settings_from_dict(
            state.ideal_path_settings,
            fallback=self.ideal_path_settings,
        )
        self.sidebar_settings = _sidebar_settings_from_dict(
            state.sidebar_settings,
            fallback=self.sidebar_settings,
        )
        self._sync_settings_controls_from_state()
        self.selected_channels = list(state.selected_channels)
        self.event_reviews = (
            state.event_reviews
            if state.event_reviews
            else _event_reviews_from_markers(self.playback_events)
        )
        self.analysis_segments = state.analysis_segments
        self.selected_sidebar_group = state.selected_sidebar_group
        self.report_output_path = state.report_output_path
        self._populate_time_series_channel_list()
        if state.vehicle_model_path is not None:
            self.load_vehicle_model_path(state.vehicle_model_path)
        self.reference_route_path = state.reference_route_path
        if self.reference_route_path is not None and self.reference_route_path.exists():
            if not self.load_reference_route_path(self.reference_route_path):
                self._set_empty_restored_reference_route(state)
        else:
            self._set_empty_restored_reference_route(state)
        self.video_path = state.video_path
        self.video_offset_ms = state.video_offset_ms
        self.video_muted = state.video_muted
        self._sync_video_sync_controls()
        self._select_sidebar_group(self.selected_sidebar_group)
        self._restore_preset_tabs(state)
        self._clear_workspace()

        for window_state in state.open_windows:
            sub_window = self.add_analysis_window(window_state.title)
            sub_window.move(window_state.x, window_state.y)
            sub_window.resize(window_state.width, window_state.height)
            sub_window.set_analysis_opacity(window_state.opacity)

        self.set_playback_seconds(state.playback_seconds)

    def _set_empty_restored_reference_route(self, state: ProjectState) -> None:
        self.set_reference_route(
            ReferenceRoute(
                name=state.reference_route_name or "Reference route",
                points=(),
            )
        )

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
                    opacity=(
                        sub_window.analysis_opacity()
                        if isinstance(sub_window, _AnalysisSubWindow)
                        else 1.0
                    ),
                )
            )
        return windows

    def _restore_preset_tabs(self, state: ProjectState) -> None:
        if not state.preset_tab_order:
            return
        self._syncing_preset_tabs = True
        try:
            while self.preset_tabs.count():
                self.preset_tabs.removeTab(0)
            seen = set(state.preset_tab_order)
            for tab_title in state.preset_tab_order:
                index = self.preset_tabs.addTab(tab_title)
                self.preset_tabs.setTabToolTip(index, _preset_tab_tooltip_for_title(tab_title))
            for tab_title in DEFAULT_PRESET_TABS:
                if tab_title not in seen:
                    index = self.preset_tabs.addTab(tab_title)
                    self.preset_tabs.setTabToolTip(index, _preset_tab_tooltip_for_title(tab_title))
            if self.preset_tabs.count():
                self.preset_tabs.setCurrentIndex(
                    min(max(state.active_tab_index, 0), self.preset_tabs.count() - 1)
                )
        finally:
            self._syncing_preset_tabs = False

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

    def workspace_preset_names(self) -> tuple[str, ...]:
        return ()

    def preset_tab_window_sets(self) -> tuple[tuple[str, ...], ...]:
        return PRESET_TAB_WINDOW_SETS

    def preset_tab_window_titles(self, index: int) -> tuple[str, ...]:
        mode = self.preset_tab_mode(index)
        if mode is None:
            return ()
        return mode.windows

    def preset_tab_mode(self, index: int) -> AnalysisPresetMode | None:
        if index < 0:
            return None
        mode_index = index
        if hasattr(self, "preset_tabs") and index < self.preset_tabs.count():
            tab_title = self.preset_tabs.tabText(index)
            try:
                mode_index = DEFAULT_PRESET_TABS.index(tab_title)
            except ValueError:
                mode_index = index
        if mode_index < 0 or mode_index >= len(PRESET_TAB_MODES):
            return None
        return PRESET_TAB_MODES[mode_index]

    def apply_preset_tab(self, index: int) -> None:
        if self._syncing_preset_tabs or not hasattr(self, "workspace"):
            return
        mode = self.preset_tab_mode(index)
        if mode is None:
            return
        self._apply_analysis_preset_mode(mode)

    def _apply_analysis_preset_mode(self, mode: AnalysisPresetMode) -> None:
        self._apply_preset_time_series_channels(mode.channels)
        target_windows = self._open_and_arrange_analysis_windows(
            mode.windows,
            focus_title=mode.focus_window,
        )
        focus_title = (
            mode.focus_window
            or (target_windows[0].windowTitle() if target_windows else "")
        )
        if focus_title:
            self._select_sidebar_group_for_window(focus_title)

    def _apply_preset_time_series_channels(self, channel_ids: Sequence[str]) -> None:
        if not channel_ids:
            return
        selected = [
            channel_id for channel_id in channel_ids if channel_id in self.sensor_series
        ]
        if not selected:
            return
        self.selected_channels = selected
        self._populate_time_series_channel_list()
        self._apply_time_series_channels_to_open_windows()

    def apply_workspace_preset(self, preset_name: str) -> None:
        titles = WORKSPACE_LAYOUT_PRESETS.get(preset_name)
        if titles is None:
            raise KeyError(preset_name)
        self._open_and_arrange_analysis_windows(titles)

    def _open_and_arrange_analysis_windows(
        self,
        titles: Sequence[str],
        *,
        focus_title: str = "",
    ) -> list[QtWidgets.QMdiSubWindow]:
        target_windows: list[QtWidgets.QMdiSubWindow] = []
        for title in titles:
            sub_window = self._find_analysis_sub_window(title)
            if sub_window is None:
                sub_window = self.add_analysis_window(title)
            target_windows.append(sub_window)

        self._arrange_analysis_windows(target_windows)
        if target_windows:
            focus_window = next(
                (
                    sub_window
                    for sub_window in target_windows
                    if sub_window.windowTitle() == focus_title
                ),
                target_windows[0],
            )
            self.workspace.setActiveSubWindow(focus_window)
            self._update_properties_for_active_window(focus_window)
        return target_windows

    def tile_analysis_windows(self) -> None:
        self._arrange_analysis_windows(self.workspace.subWindowList())

    def _find_analysis_sub_window(self, title: str) -> QtWidgets.QMdiSubWindow | None:
        for sub_window in self.workspace.subWindowList():
            if sub_window.windowTitle() == title:
                return sub_window
        return None

    def add_analysis_window(self, title: str) -> QtWidgets.QMdiSubWindow:
        if title == "Time-Series Graph":
            widget = self._build_time_series_window()
        elif title == "Data Analysis":
            widget = self._build_data_analysis_window()
        elif title == "Vehicle Dynamics":
            widget = self._build_vehicle_dynamics_window()
        elif title == "Segment Analysis":
            widget = self._build_segment_analysis_window()
        elif title == "Event Review":
            widget = self._build_event_review_window()
        elif title == "Export Report":
            widget = self._build_export_report_window()
        elif title == "Documents":
            widget = self._build_documents_window()
        elif title == "G-G Diagram":
            widget = self._build_gg_diagram_window()
        elif title == "GPS Map":
            widget = self._build_gps_map_window()
        elif title == "Current Values Table":
            widget = self._build_current_values_window()
        elif title == "Gauge Indicators":
            widget = self._build_gauge_indicators_window()
        elif title == "Tire Temperature":
            widget = self._build_tire_temperature_window()
        elif title == "Video Sync":
            widget = self._build_video_sync_window()
        elif title == "Benchmark Summary":
            widget = BenchmarkSummaryWindow(collect_environment())
        elif title == "3D Vehicle Model":
            widget = self._build_vehicle_model_window()
        else:
            widget = self._build_placeholder_window(title)

        sub_window = _AnalysisSubWindow(widget, title)
        sub_window.analysisOpacityChanged.connect(
            lambda opacity, window_title=title: self._remember_window_opacity(
                window_title,
                opacity,
            )
        )
        sub_window.set_analysis_opacity(
            self.window_opacity_defaults.get(title, 1.0),
            emit_changed=False,
        )
        self.workspace.addSubWindow(sub_window)
        sub_window.setWindowFlag(QtCore.Qt.WindowType.WindowMinMaxButtonsHint, True)
        sub_window.setWindowFlag(QtCore.Qt.WindowType.WindowCloseButtonHint, True)
        sub_window.resize(self._default_analysis_window_size(title))
        self._position_new_analysis_window(sub_window)
        sub_window.show()
        self.workspace.setActiveSubWindow(sub_window)
        self._update_properties_for_active_window(sub_window)
        return sub_window

    def _remember_window_opacity(self, title: str, opacity: float) -> None:
        self.window_opacity_defaults[title] = _clamp_analysis_opacity(opacity)

    def _position_new_analysis_window(self, sub_window: QtWidgets.QMdiSubWindow) -> None:
        window_count = max(0, len(self.workspace.subWindowList()) - 1)
        offset = 26 * (window_count % 8)
        workspace_rect = self.workspace.viewport().rect()
        if workspace_rect.width() <= 0 or workspace_rect.height() <= 0:
            sub_window.move(offset, offset)
            return
        max_x = max(0, workspace_rect.width() - sub_window.width() - 12)
        max_y = max(0, workspace_rect.height() - sub_window.height() - 12)
        sub_window.move(min(offset, max_x), min(offset, max_y))

    def _default_analysis_window_size(self, title: str) -> QtCore.QSize:
        if title == "Time-Series Graph":
            return QtCore.QSize(520, 290)
        if title == "Gauge Indicators":
            return QtCore.QSize(440, 230)
        if title == "Tire Temperature":
            return QtCore.QSize(430, 380)
        if title == "Video Sync":
            return QtCore.QSize(620, 420)
        if title in {"GPS Map", "G-G Diagram"}:
            return QtCore.QSize(560, 340)
        if title == "3D Vehicle Model":
            return QtCore.QSize(560, 330)
        if title == "Vehicle Dynamics":
            return QtCore.QSize(460, 300)
        return QtCore.QSize(460, 280)

    def _arrange_analysis_windows(
        self,
        sub_windows: Sequence[QtWidgets.QMdiSubWindow],
    ) -> None:
        windows = [sub_window for sub_window in sub_windows if shiboken6.isValid(sub_window)]
        if not windows:
            return

        viewport = self.workspace.viewport().rect()
        available_width = viewport.width() if viewport.width() > 0 else 960
        available_height = viewport.height() if viewport.height() > 0 else 560
        columns = max(1, math.ceil(math.sqrt(len(windows))))
        rows = math.ceil(len(windows) / columns)
        gap = 10
        tile_width = max(320, int((available_width - gap * (columns + 1)) / columns))
        tile_height = max(220, int((available_height - gap * (rows + 1)) / rows))

        for index, sub_window in enumerate(windows):
            if sub_window.isMaximized() or sub_window.isMinimized():
                sub_window.showNormal()
            row = index // columns
            column = index % columns
            sub_window.setGeometry(
                gap + column * (tile_width + gap),
                gap + row * (tile_height + gap),
                tile_width,
                tile_height,
            )

    def _build_time_series_window(self) -> TimeSeriesWindow:
        widget = TimeSeriesWindow(
            self.playback_state,
            line_color=self.visualization_settings.graph_line_color,
            line_width=self.visualization_settings.graph_line_width,
        )
        widget.set_series(self._time_series_plot_series())
        return widget

    def _time_series_plot_series(self) -> dict[str, tuple[list[float], list[float]]]:
        x_values = [
            self.playback_state.seconds_at(index)
            for index in range(self.playback_state.sample_count)
        ]
        return {
            channel_id: (x_values, self.sensor_series[channel_id])
            for channel_id in self._selected_time_series_channels()
            if channel_id in self.sensor_series
        }

    def _selected_time_series_channels(self) -> tuple[str, ...]:
        selected = [
            channel_id
            for channel_id in self.selected_channels
            if channel_id in self.sensor_series
        ]
        if selected:
            return tuple(selected)

        defaults = [
            channel_id
            for channel_id in ("RPM", "TPS_percent")
            if channel_id in self.sensor_series
        ]
        if defaults:
            return tuple(defaults)
        return tuple(_time_series_channel_options(self.sensor_series)[:4])

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
        self._apply_ideal_path_to_gps_window(widget)
        widget.set_reference_route(self.reference_route)
        widget.referenceRouteChanged.connect(self._handle_gps_reference_route_changed)
        if hasattr(self, "reference_route_edit_checkbox"):
            widget.set_reference_route_edit_enabled(
                self.reference_route_edit_checkbox.isChecked()
            )
        return widget

    def _build_vehicle_model_window(self) -> VehicleModelWindow:
        return VehicleModelWindow(
            self.vehicle_model_info,
            playback_state=self.playback_state,
            ax_corrected=self.sensor_series["AX_CORRECTED_G"],
            ay_corrected=self.sensor_series["AY_CORRECTED_G"],
            yaw_rate=self.sensor_series["yaw rate"],
        )

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

    def _build_gauge_indicators_window(self) -> GaugeIndicatorsWindow:
        return GaugeIndicatorsWindow(self.playback_state, self.sensor_series)

    def _build_tire_temperature_window(self) -> TireTemperatureWindow:
        return TireTemperatureWindow(self.playback_state, self.sensor_series)

    def _build_video_sync_window(self) -> VideoSyncWindow:
        widget = VideoSyncWindow(
            self.playback_state,
            video_path=self.video_path,
            video_offset_ms=self.video_offset_ms,
            video_muted=self.video_muted,
        )
        for button in (widget.load_button, widget.clear_button):
            try:
                button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
        widget.load_button.clicked.connect(self._open_video_sync_dialog)
        widget.clear_button.clicked.connect(self.clear_video_sync)
        widget.videoOffsetChanged.connect(self.set_video_sync_offset_ms)
        widget.videoMutedChanged.connect(self.set_video_sync_muted)
        return widget

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

    def _build_vehicle_dynamics_window(self) -> VehicleDynamicsWindow:
        return VehicleDynamicsWindow(self._vehicle_dynamics_summary())

    def _vehicle_dynamics_summary(self):
        timestamps = [
            self.playback_state.seconds_at(index)
            for index in range(self.playback_state.sample_count)
        ]
        return compute_dynamics_summary(
            timestamps_seconds=timestamps,
            sensors=self.sensor_series,
            g_limit_radius=self.visualization_settings.gg_limit_radius,
            wheelbase_m=self.ideal_path_settings.wheelbase_m,
            steering_ratio=self.ideal_path_settings.steering_ratio,
            steering_channel=self.ideal_path_settings.steering_channel,
            available_channels=self.available_sensor_channels,
        )

    def _build_event_review_window(self) -> EventReviewWindow:
        widget = EventReviewWindow(self.event_reviews, self.seek_to_time_ms)
        widget.reviewChanged.connect(self._update_event_review)
        return widget

    def _build_segment_analysis_window(self) -> SegmentAnalysisWindow:
        widget = SegmentAnalysisWindow(
            self.playback_state,
            self._segment_summaries(),
        )
        widget.segmentAdded.connect(self._add_analysis_segment)
        return widget

    def _build_export_report_window(self) -> ExportReportWindow:
        widget = ExportReportWindow(self.report_output_path)
        widget.exportRequested.connect(self.export_report_file)
        return widget

    def _build_documents_window(self) -> DocumentsWindow:
        return DocumentsWindow(_project_document_paths())

    def _update_event_review(self, row_index: int, patch: object) -> None:
        if not isinstance(patch, dict):
            return
        if row_index < 0 or row_index >= len(self.event_reviews):
            return
        review = self.event_reviews[row_index]
        state = patch.get("state", review.state)
        if not isinstance(state, EventReviewState):
            try:
                state = EventReviewState(str(state))
            except ValueError:
                state = EventReviewState.UNREVIEWED
        updated = EventReview(
            name=review.name,
            time_ms=review.time_ms,
            severity=review.severity,
            sensor=review.sensor,
            value=review.value,
            condition=review.condition,
            state=state,
            note=str(patch.get("note", review.note)),
        )
        reviews = list(self.event_reviews)
        reviews[row_index] = updated
        self.event_reviews = tuple(reviews)
        self._refresh_event_review_windows()

    def _refresh_event_review_windows(self) -> None:
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, EventReviewWindow):
                widget.refresh_reviews(self.event_reviews)

    def _add_analysis_segment(self, segment: object) -> None:
        if not isinstance(segment, AnalysisSegment):
            return
        self.analysis_segments = (*self.analysis_segments, segment.normalized())
        self._refresh_segment_analysis_windows()

    def _refresh_segment_analysis_windows(self) -> None:
        summaries = self._segment_summaries()
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, SegmentAnalysisWindow):
                widget.refresh_summaries(summaries)

    def _segment_summaries(self) -> tuple[SegmentSummary, ...]:
        timestamps = [
            self.playback_state.seconds_at(index)
            for index in range(self.playback_state.sample_count)
        ]
        return tuple(
            compute_segment_summary(segment, timestamps, self.sensor_series)
            for segment in self.analysis_segments
        )

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
                elif action_title == "Export Report":
                    action.triggered.connect(self._export_report_dialog)

    def _build_central_workspace(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("centralWorkspaceContainer")
        central_layout = QtWidgets.QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.preset_tabs = QtWidgets.QTabBar()
        self.preset_tabs.setObjectName("presetTabs")
        self.preset_tabs.setExpanding(False)
        self.preset_tabs.setMovable(True)
        for index, tab_title in enumerate(DEFAULT_PRESET_TABS):
            self.preset_tabs.addTab(tab_title)
            self.preset_tabs.setTabToolTip(index, _preset_tab_tooltip(index))

        self.workspace_command_bar = QtWidgets.QFrame()
        self.workspace_command_bar.setObjectName("workspaceCommandBar")
        command_layout = QtWidgets.QHBoxLayout(self.workspace_command_bar)
        command_layout.setContentsMargins(8, 5, 8, 5)
        command_layout.setSpacing(6)
        self.workspace_command_bar_title = QtWidgets.QLabel("Window tools")
        self.workspace_command_bar_title.setObjectName("workspaceCommandLabel")
        command_layout.addWidget(self.workspace_command_bar_title)
        self.workspace_preset_buttons: dict[str, QtWidgets.QToolButton] = {}
        command_layout.addStretch(1)
        self.tile_workspace_button = QtWidgets.QToolButton()
        self.tile_workspace_button.setObjectName("tileWorkspaceButton")
        self.tile_workspace_button.setText("Tile")
        self.tile_workspace_button.setToolTip("Tile open analysis windows")
        self.tile_workspace_button.clicked.connect(self.tile_analysis_windows)
        command_layout.addWidget(self.tile_workspace_button)

        self.workspace = QtWidgets.QMdiArea()
        self.workspace.setObjectName("workspace")
        self.workspace.setViewMode(QtWidgets.QMdiArea.ViewMode.SubWindowView)
        self.workspace.setBackground(QtGui.QBrush(QtGui.QColor("#202326")))
        self.workspace.subWindowActivated.connect(self._update_properties_for_active_window)
        self.preset_tabs.tabBarClicked.connect(self.apply_preset_tab)

        central_layout.addWidget(self.preset_tabs)
        central_layout.addWidget(self.workspace_command_bar)
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
        self.analysis_list.hide()
        self.analysis_list.itemDoubleClicked.connect(
            lambda item: self.add_analysis_window(item.text())
        )

        self.analysis_tree = QtWidgets.QTreeWidget()
        self.analysis_tree.setObjectName("analysisTree")
        self.analysis_tree.setHeaderHidden(True)
        self.analysis_tree.itemDoubleClicked.connect(self._handle_sidebar_tree_item_activated)

        self.add_window_button = QtWidgets.QPushButton("추가")
        self.add_window_button.setObjectName("addWindowButton")
        self.add_window_button.clicked.connect(self._add_selected_analysis_window)

        layout.addWidget(self.sidebar_search)
        layout.addWidget(self.analysis_tree, 1)
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
        self.properties_panel.setMinimumWidth(300)

        content = QtWidgets.QWidget()
        content.setObjectName("propertiesPanelContent")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.properties_selection_label = QtWidgets.QLabel("선택 창: -")
        self.properties_selection_label.setObjectName("propertiesSelectionLabel")
        self.properties_scope_label = QtWidgets.QLabel(
            "적용 범위: 선택한 창 종류와 이후 새로 여는 같은 종류의 창"
        )
        self.properties_scope_label.setObjectName("propertiesScopeLabel")
        self.properties_scope_label.setWordWrap(True)
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
        self.ideal_path_enabled_checkbox = QtWidgets.QCheckBox("Show ideal path")
        self.ideal_path_enabled_checkbox.setObjectName("idealPathEnabledCheckbox")
        self.ideal_path_enabled_checkbox.setChecked(self.ideal_path_settings.enabled)
        self.ideal_path_enabled_checkbox.toggled.connect(
            self._update_ideal_path_settings_from_controls
        )
        self.ideal_path_wheelbase_spin = QtWidgets.QDoubleSpinBox()
        self.ideal_path_wheelbase_spin.setObjectName("idealPathWheelbaseSpin")
        self.ideal_path_wheelbase_spin.setRange(0.5, 5.0)
        self.ideal_path_wheelbase_spin.setSingleStep(0.05)
        self.ideal_path_wheelbase_spin.setDecimals(2)
        self.ideal_path_wheelbase_spin.setSuffix(" m")
        self.ideal_path_wheelbase_spin.setValue(self.ideal_path_settings.wheelbase_m)
        self.ideal_path_wheelbase_spin.valueChanged.connect(
            self._update_ideal_path_settings_from_controls
        )
        self.ideal_path_steering_ratio_spin = QtWidgets.QDoubleSpinBox()
        self.ideal_path_steering_ratio_spin.setObjectName("idealPathSteeringRatioSpin")
        self.ideal_path_steering_ratio_spin.setRange(0.1, 30.0)
        self.ideal_path_steering_ratio_spin.setSingleStep(0.1)
        self.ideal_path_steering_ratio_spin.setDecimals(2)
        self.ideal_path_steering_ratio_spin.setValue(self.ideal_path_settings.steering_ratio)
        self.ideal_path_steering_ratio_spin.valueChanged.connect(
            self._update_ideal_path_settings_from_controls
        )
        self.ideal_path_steering_channel_combo = QtWidgets.QComboBox()
        self.ideal_path_steering_channel_combo.setObjectName("idealPathSteeringChannelCombo")
        self.ideal_path_steering_channel_combo.currentTextChanged.connect(
            self._update_ideal_path_settings_from_controls
        )
        self.reference_route_edit_checkbox = QtWidgets.QCheckBox("Edit route")
        self.reference_route_edit_checkbox.setObjectName("referenceRouteEditCheckbox")
        self.reference_route_edit_checkbox.toggled.connect(
            self._update_reference_route_controls
        )
        self.reference_route_name_edit = QtWidgets.QLineEdit(self.reference_route.name)
        self.reference_route_name_edit.setObjectName("referenceRouteNameEdit")
        self.reference_route_name_edit.editingFinished.connect(
            self._rename_reference_route_from_controls
        )
        self.reference_route_load_button = QtWidgets.QPushButton("Load route...")
        self.reference_route_load_button.setObjectName("referenceRouteLoadButton")
        self.reference_route_load_button.clicked.connect(
            self._open_reference_route_load_dialog
        )
        self.reference_route_save_button = QtWidgets.QPushButton("Save route...")
        self.reference_route_save_button.setObjectName("referenceRouteSaveButton")
        self.reference_route_save_button.clicked.connect(
            self._open_reference_route_save_dialog
        )
        self.reference_route_clear_button = QtWidgets.QPushButton("Clear")
        self.reference_route_clear_button.setObjectName("referenceRouteClearButton")
        self.reference_route_clear_button.clicked.connect(self.clear_reference_route)
        self.reference_route_points_label = QtWidgets.QLabel("0 points")
        self.reference_route_points_label.setObjectName("referenceRoutePointsLabel")
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
        self.time_series_channel_list = QtWidgets.QListWidget()
        self.time_series_channel_list.setObjectName("timeSeriesChannelList")
        self.time_series_channel_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self.time_series_channel_list.setMinimumWidth(180)
        self.time_series_channel_list.setMaximumHeight(220)
        self.time_series_channel_list.itemChanged.connect(
            self._update_time_series_channels_from_controls
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

        self.video_sync_path_edit = QtWidgets.QLineEdit()
        self.video_sync_path_edit.setObjectName("videoSyncPathEdit")
        self.video_sync_path_edit.setReadOnly(True)
        self.video_sync_load_button = QtWidgets.QPushButton("Load Video...")
        self.video_sync_load_button.setObjectName("videoSyncLoadButton")
        self.video_sync_load_button.clicked.connect(self._open_video_sync_dialog)
        self.video_sync_clear_button = QtWidgets.QPushButton("Clear")
        self.video_sync_clear_button.setObjectName("videoSyncClearButton")
        self.video_sync_clear_button.clicked.connect(self.clear_video_sync)
        self.video_sync_offset_spin = QtWidgets.QSpinBox()
        self.video_sync_offset_spin.setObjectName("videoSyncOffsetSpin")
        self.video_sync_offset_spin.setRange(-3_600_000, 3_600_000)
        self.video_sync_offset_spin.setSuffix(" ms")
        self.video_sync_offset_spin.setValue(self.video_offset_ms)
        self.video_sync_offset_spin.valueChanged.connect(self.set_video_sync_offset_ms)
        self.video_sync_mute_checkbox = QtWidgets.QCheckBox("Mute")
        self.video_sync_mute_checkbox.setObjectName("videoSyncMuteCheckbox")
        self.video_sync_mute_checkbox.setChecked(self.video_muted)
        self.video_sync_mute_checkbox.toggled.connect(self.set_video_sync_muted)
        self.video_sync_status_label = QtWidgets.QLabel("No video loaded")
        self.video_sync_status_label.setObjectName("videoSyncStatusLabel")
        self.video_sync_status_label.setWordWrap(True)

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
                ("채널", self.time_series_channel_list),
                ("선 색상", self.graph_line_color_combo),
                ("선 굵기", self.graph_line_width_spin),
            ),
        )
        self.gps_properties_page = self._make_properties_page(
            "gpsPropertiesPage",
            (
                ("GPS", self.gps_map_background_checkbox),
                ("Ideal path", self.ideal_path_enabled_checkbox),
                ("Wheelbase", self.ideal_path_wheelbase_spin),
                ("Steering ratio", self.ideal_path_steering_ratio_spin),
                ("Steering channel", self.ideal_path_steering_channel_combo),
                ("Ref edit", self.reference_route_edit_checkbox),
                ("Ref name", self.reference_route_name_edit),
                ("Ref load", self.reference_route_load_button),
                ("Ref save", self.reference_route_save_button),
                ("Ref clear", self.reference_route_clear_button),
                ("Ref points", self.reference_route_points_label),
            ),
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
        self.video_sync_properties_page = self._make_properties_page(
            "videoSyncPropertiesPage",
            (
                ("Video file", self.video_sync_path_edit),
                ("Load", self.video_sync_load_button),
                ("Clear", self.video_sync_clear_button),
                ("Offset", self.video_sync_offset_spin),
                ("Audio", self.video_sync_mute_checkbox),
                ("Status", self.video_sync_status_label),
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
            self.video_sync_properties_page,
            self.read_only_properties_page,
        ):
            self.properties_stack.addWidget(page)

        layout.addWidget(self.properties_selection_label)
        layout.addWidget(self.properties_scope_label)
        layout.addWidget(self.properties_stack, 1)

        self.properties_panel.setWidget(content)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.properties_panel)
        self._populate_time_series_channel_list()
        self._populate_ideal_path_steering_channel_combo()
        self._update_properties_for_active_window()

    def _make_properties_page(
        self,
        object_name: str,
        rows: tuple[tuple[str, QtWidgets.QWidget], ...],
    ) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setObjectName(object_name)
        page_layout = QtWidgets.QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(6)

        group = QtWidgets.QFrame()
        group.setObjectName("settingsGroupFrame")
        group_layout = QtWidgets.QVBoxLayout(group)
        group_layout.setContentsMargins(6, 6, 6, 6)
        group_layout.setSpacing(6)
        for label, widget in rows:
            if isinstance(widget, QtWidgets.QLabel) and not widget.objectName():
                widget.setObjectName("settingsValueLabel")
                widget.setWordWrap(True)

            row = QtWidgets.QFrame()
            row.setObjectName("settingsRow")
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(6, 6, 6, 6)
            row_layout.setSpacing(4)

            label_widget = QtWidgets.QLabel(label)
            label_widget.setObjectName("settingsRowLabel")
            label_widget.setMinimumWidth(64)
            label_widget.setMaximumWidth(68)
            label_widget.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
            )
            label_widget.setWordWrap(True)
            row_layout.addWidget(label_widget)
            row_layout.addWidget(widget, 1)
            group_layout.addWidget(row)

        page_layout.addWidget(group)
        page_layout.addStretch(1)
        return page

    def _update_properties_for_active_window(
        self,
        sub_window: QtWidgets.QMdiSubWindow | None = None,
    ) -> None:
        if sub_window is None:
            sub_window = self.workspace.activeSubWindow()
        if sub_window is not None and not shiboken6.isValid(sub_window):
            sub_window = None
        self._sync_analysis_title_bars(sub_window)

        if not hasattr(self, "properties_stack"):
            return

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
            elif isinstance(selected_widget, VideoSyncWindow):
                selected_page = self.video_sync_properties_page
                self._sync_video_sync_controls()
            else:
                selected_page = self.read_only_properties_page

        self.properties_selection_label.setText(f"선택 창: {selected_title}")
        self.properties_stack.setCurrentWidget(selected_page)

    def _sync_analysis_title_bars(
        self,
        active_sub_window: QtWidgets.QMdiSubWindow | None,
    ) -> None:
        if not hasattr(self, "workspace"):
            return
        for sub_window in self.workspace.subWindowList():
            if isinstance(sub_window, _AnalysisSubWindow):
                sub_window.set_title_active(sub_window is active_sub_window)

    def _update_visualization_settings_from_controls(self, *_args: object) -> None:
        self.visualization_settings = VisualizationSettings(
            gps_map_background_enabled=self.gps_map_background_checkbox.isChecked(),
            graph_line_color=_graph_line_color(self.graph_line_color_combo.currentText()),
            graph_line_width=float(self.graph_line_width_spin.value()),
            gg_limit_radius=float(self.gg_limit_radius_spin.value()),
        )
        self._apply_visualization_settings_to_open_windows()

    def _update_time_series_channels_from_controls(self, *_args: object) -> None:
        if self._syncing_time_series_channel_checks:
            return
        self.selected_channels = [
            _time_series_channel_id_from_item(self.time_series_channel_list.item(index))
            for index in range(self.time_series_channel_list.count())
            if (
                self.time_series_channel_list.item(index).checkState()
                == QtCore.Qt.CheckState.Checked
            )
        ]
        self._refresh_time_series_channel_item_labels()
        self._apply_time_series_channels_to_open_windows()

    def _populate_time_series_channel_list(self) -> None:
        if not hasattr(self, "time_series_channel_list"):
            return
        selected = set(self._selected_time_series_channels())
        self._syncing_time_series_channel_checks = True
        try:
            self.time_series_channel_list.clear()
            for channel_id in _time_series_channel_options(self.sensor_series):
                checked = channel_id in selected
                item = QtWidgets.QListWidgetItem(
                    _time_series_channel_item_label(channel_id, checked)
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, channel_id)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    QtCore.Qt.CheckState.Checked
                    if checked
                    else QtCore.Qt.CheckState.Unchecked
                )
                self.time_series_channel_list.addItem(item)
        finally:
            self._syncing_time_series_channel_checks = False

    def _refresh_time_series_channel_item_labels(self) -> None:
        self._syncing_time_series_channel_checks = True
        try:
            for index in range(self.time_series_channel_list.count()):
                item = self.time_series_channel_list.item(index)
                channel_id = _time_series_channel_id_from_item(item)
                checked = item.checkState() == QtCore.Qt.CheckState.Checked
                item.setText(_time_series_channel_item_label(channel_id, checked))
        finally:
            self._syncing_time_series_channel_checks = False

    def _populate_ideal_path_steering_channel_combo(self) -> None:
        if not hasattr(self, "ideal_path_steering_channel_combo"):
            return
        options = _steering_channel_options(self.sensor_series)
        current = self.ideal_path_settings.steering_channel
        self._syncing_ideal_path_controls = True
        try:
            self.ideal_path_steering_channel_combo.clear()
            self.ideal_path_steering_channel_combo.addItems(options)
            if current in options:
                self.ideal_path_steering_channel_combo.setCurrentText(current)
            elif "Auto" in options:
                self.ideal_path_steering_channel_combo.setCurrentText("Auto")
        finally:
            self._syncing_ideal_path_controls = False

    def _update_ideal_path_settings_from_controls(self, *_args: object) -> None:
        if self._syncing_ideal_path_controls:
            return
        self.ideal_path_settings = IdealPathSettings(
            enabled=self.ideal_path_enabled_checkbox.isChecked(),
            wheelbase_m=float(self.ideal_path_wheelbase_spin.value()),
            steering_ratio=float(self.ideal_path_steering_ratio_spin.value()),
            steering_channel=self.ideal_path_steering_channel_combo.currentText(),
        )
        self._apply_ideal_path_settings_to_open_windows()

    def set_reference_route(self, route: ReferenceRoute) -> None:
        self.reference_route = route
        self.reference_route_path = route.source_path
        if hasattr(self, "reference_route_name_edit"):
            self.reference_route_name_edit.setText(route.name)
        self._apply_reference_route_to_open_windows()
        self._refresh_reference_route_status()

    def clear_reference_route(self) -> None:
        self.set_reference_route(ReferenceRoute(name=self.reference_route.name, points=()))

    def load_video_sync_path(self, path: Path | str) -> None:
        self.video_path = Path(path)
        self._apply_video_sync_to_open_windows(path=True, offset=False, muted=False)
        self._sync_video_sync_controls()

    def clear_video_sync(self) -> None:
        self.video_path = None
        self._apply_video_sync_to_open_windows(path=True, offset=False, muted=False)
        self._sync_video_sync_controls()

    def set_video_sync_offset_ms(self, offset_ms: int) -> None:
        self.video_offset_ms = int(offset_ms)
        self._apply_video_sync_to_open_windows(path=False, offset=True, muted=False)
        self._sync_video_sync_controls()

    def set_video_sync_muted(self, muted: bool) -> None:
        self.video_muted = bool(muted)
        self._apply_video_sync_to_open_windows(path=False, offset=False, muted=True)
        self._sync_video_sync_controls()

    def _open_video_sync_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load video",
            str(Path.cwd()),
            "Video files (*.mp4 *.mov *.m4v *.avi);;All files (*.*)",
        )
        if path:
            self.load_video_sync_path(path)

    def _apply_video_sync_to_open_windows(
        self,
        *,
        path: bool = True,
        offset: bool = True,
        muted: bool = True,
    ) -> None:
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, VideoSyncWindow):
                if path:
                    widget.set_video_path(self.video_path)
                if offset:
                    widget.set_video_offset_ms(self.video_offset_ms, notify=False)
                if muted:
                    widget.set_video_muted(self.video_muted, notify=False)

    def _sync_video_sync_controls(self) -> None:
        if not hasattr(self, "video_sync_path_edit"):
            return
        self.video_sync_path_edit.setText(
            "" if self.video_path is None else str(self.video_path)
        )
        self.video_sync_offset_spin.blockSignals(True)
        self.video_sync_offset_spin.setValue(self.video_offset_ms)
        self.video_sync_offset_spin.blockSignals(False)
        self.video_sync_mute_checkbox.blockSignals(True)
        self.video_sync_mute_checkbox.setChecked(self.video_muted)
        self.video_sync_mute_checkbox.blockSignals(False)
        if self.video_path is None:
            status_text = "No video loaded"
        elif not self.video_path.exists():
            status_text = f"Video missing: {self.video_path}"
        else:
            status_text = f"Video: {self.video_path.name}"
        self.video_sync_status_label.setText(status_text)

    def _sync_settings_controls_from_state(self) -> None:
        if not hasattr(self, "gps_map_background_checkbox"):
            return

        _set_checked_without_signal(
            self.gps_map_background_checkbox,
            self.visualization_settings.gps_map_background_enabled,
        )
        _set_combo_text_without_signal(
            self.graph_line_color_combo,
            _graph_line_color_name(self.visualization_settings.graph_line_color),
        )
        _set_spin_value_without_signal(
            self.graph_line_width_spin,
            self.visualization_settings.graph_line_width,
        )
        _set_spin_value_without_signal(
            self.gg_limit_radius_spin,
            self.visualization_settings.gg_limit_radius,
        )

        _set_checked_without_signal(
            self.ideal_path_enabled_checkbox,
            self.ideal_path_settings.enabled,
        )
        _set_spin_value_without_signal(
            self.ideal_path_wheelbase_spin,
            self.ideal_path_settings.wheelbase_m,
        )
        _set_spin_value_without_signal(
            self.ideal_path_steering_ratio_spin,
            self.ideal_path_settings.steering_ratio,
        )
        self._populate_ideal_path_steering_channel_combo()
        _set_combo_text_without_signal(
            self.ideal_path_steering_channel_combo,
            self.ideal_path_settings.steering_channel,
        )

        _set_checked_without_signal(
            self.sidebar_search_visible_checkbox,
            self.sidebar_settings.search_visible,
        )
        _set_checked_without_signal(
            self.sidebar_add_button_visible_checkbox,
            self.sidebar_settings.add_button_visible,
        )
        _set_combo_text_without_signal(self.sidebar_sort_combo, self.sidebar_settings.sort_mode)
        _set_combo_text_without_signal(self.sidebar_density_combo, self.sidebar_settings.density)
        _set_spin_value_without_signal(self.sidebar_width_spin, self.sidebar_settings.width_px)

        self._apply_sidebar_settings()
        self._apply_visualization_settings_to_open_windows()
        self._apply_ideal_path_settings_to_open_windows()

    def load_reference_route_path(self, path: Path) -> bool:
        try:
            route = load_reference_route(path)
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(f"Reference route load failed: {exc}", 5000)
            return False
        self.set_reference_route(route)
        self.statusBar().showMessage(f"Loaded reference route: {path.name}", 5000)
        return True

    def save_reference_route_path(self, path: Path) -> bool:
        route = ReferenceRoute(
            name=self.reference_route.name,
            points=self.reference_route.points,
            created_at=self.reference_route.created_at,
            metadata=dict(self.reference_route.metadata),
            source_path=path,
        )
        try:
            save_reference_route(path, route)
        except OSError as exc:
            self.statusBar().showMessage(f"Reference route save failed: {exc}", 5000)
            return False
        self.reference_route = route
        self.reference_route_path = path
        self._apply_reference_route_to_open_windows()
        self._refresh_reference_route_status()
        self.statusBar().showMessage(f"Saved reference route: {path.name}", 5000)
        return True

    def _handle_gps_reference_route_changed(self, route: object) -> None:
        if self._syncing_reference_route_windows or not isinstance(route, ReferenceRoute):
            return
        source_path = (
            route.source_path if route.source_path is not None else self.reference_route_path
        )
        self.reference_route = ReferenceRoute(
            name=route.name,
            points=route.points,
            created_at=route.created_at,
            metadata=dict(route.metadata),
            source_path=source_path,
        )
        self.reference_route_path = source_path
        if hasattr(self, "reference_route_name_edit"):
            self.reference_route_name_edit.setText(self.reference_route.name)
        self._apply_reference_route_to_open_windows()
        self._refresh_reference_route_status()

    def _open_reference_route_load_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load reference route",
            str(Path.cwd()),
            "MF route (*.mflogroute);;JSON (*.json);;All files (*.*)",
        )
        if path:
            self.load_reference_route_path(Path(path))

    def _open_reference_route_save_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save reference route",
            str(self.reference_route_path or Path.cwd() / "reference.mflogroute"),
            "MF route (*.mflogroute);;JSON (*.json);;All files (*.*)",
        )
        if path:
            self.save_reference_route_path(Path(path))

    def _rename_reference_route_from_controls(self) -> None:
        name = self.reference_route_name_edit.text().strip() or "Reference route"
        self.set_reference_route(
            ReferenceRoute(
                name=name,
                points=self.reference_route.points,
                created_at=self.reference_route.created_at,
                metadata=dict(self.reference_route.metadata),
                source_path=self.reference_route_path,
            )
        )

    def _update_reference_route_controls(self, *_args: object) -> None:
        self._apply_reference_route_to_open_windows()

    def _apply_reference_route_to_open_windows(self) -> None:
        edit_enabled = (
            hasattr(self, "reference_route_edit_checkbox")
            and self.reference_route_edit_checkbox.isChecked()
        )
        self._syncing_reference_route_windows = True
        try:
            for sub_window in self.workspace.subWindowList():
                widget = sub_window.widget()
                if isinstance(widget, GPSMapWindow):
                    widget.set_reference_route(self.reference_route)
                    widget.set_reference_route_edit_enabled(edit_enabled)
        finally:
            self._syncing_reference_route_windows = False

    def _refresh_reference_route_status(self) -> None:
        if hasattr(self, "reference_route_points_label"):
            self.reference_route_points_label.setText(
                f"{len(self.reference_route.points)} points"
            )

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
                self._apply_ideal_path_to_gps_window(widget)
            elif isinstance(widget, GGDiagramWindow):
                widget.set_limit_circle_radius(self.visualization_settings.gg_limit_radius)
            elif isinstance(widget, VehicleDynamicsWindow):
                widget.set_summary(self._vehicle_dynamics_summary())

    def _apply_ideal_path_settings_to_open_windows(self) -> None:
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, GPSMapWindow):
                self._apply_ideal_path_to_gps_window(widget)
            elif isinstance(widget, VehicleDynamicsWindow):
                widget.set_summary(self._vehicle_dynamics_summary())

    def _apply_ideal_path_to_gps_window(self, widget: GPSMapWindow) -> None:
        if not self.ideal_path_settings.enabled:
            widget.clear_ideal_path()
            return

        steering_channel = _selected_steering_channel(
            self.ideal_path_settings.steering_channel,
            self.sensor_series,
        )
        steering_values = self.sensor_series.get(steering_channel, [])
        result = compute_ideal_path(
            timestamps=[
                self.playback_state.seconds_at(index)
                for index in range(self.playback_state.sample_count)
            ],
            speed_kph=self._ideal_path_speed_series(),
            steering_angle_deg=steering_values,
            latitude=self.sensor_series.get("latitude", []),
            longitude=self.sensor_series.get("longitude", []),
            wheelbase_m=self.ideal_path_settings.wheelbase_m,
            steering_ratio=self.ideal_path_settings.steering_ratio,
        )
        widget.set_ideal_path(
            latitude=result.latitude,
            longitude=result.longitude,
            status=result.status,
        )

    def _ideal_path_speed_series(self) -> Sequence[float | None]:
        for channel_id in ("GPS speed", "VSS / GPS speed", "VSS", "VSS_kmh"):
            if channel_id in self.sensor_series:
                return self.sensor_series[channel_id]
        return []

    def _apply_time_series_channels_to_open_windows(self) -> None:
        plot_series = self._time_series_plot_series()
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, TimeSeriesWindow):
                widget.set_series(plot_series)

    def _set_playback_button_icon(self, button: QtWidgets.QPushButton, icon_name: str) -> None:
        button.setText("")
        button.setIcon(_drawn_playback_icon(icon_name))
        button.setIconSize(QtCore.QSize(18, 18))
        button.setProperty("playbackIcon", icon_name)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def _configure_playback_icon_button(
        self,
        button: QtWidgets.QPushButton,
        *,
        icon_name: str,
        tooltip: str,
    ) -> None:
        button.setProperty("playbackSymbol", True)
        button.setFixedSize(34, 28)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        self._set_playback_button_icon(button, icon_name)

    def _build_playback_dock(self) -> None:
        self.playback_dock = QtWidgets.QDockWidget("CSV Playback", self)
        self.playback_dock.setObjectName("playbackDock")
        self.playback_dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
        self.playback_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

        content = QtWidgets.QFrame()
        content.setObjectName("playbackDockContent")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self.playback_dock_divider = QtWidgets.QFrame()
        self.playback_dock_divider.setObjectName("playbackDockDivider")
        self.playback_dock_divider.setFixedHeight(3)

        self.playback_status_strip = QtWidgets.QFrame()
        self.playback_status_strip.setObjectName("playbackStatusStrip")
        status_row = QtWidgets.QHBoxLayout(self.playback_status_strip)
        status_row.setContentsMargins(8, 2, 8, 2)
        status_row.setSpacing(8)
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

        self.playback_controls_row = QtWidgets.QFrame()
        self.playback_controls_row.setObjectName("playbackTransportStrip")
        control_row = QtWidgets.QHBoxLayout(self.playback_controls_row)
        control_row.setContentsMargins(8, 4, 8, 4)
        control_row.setSpacing(4)
        self.open_csv_button = QtWidgets.QPushButton("Open CSV...")
        self.open_csv_button.setObjectName("playbackOpenCsvButton")
        self.open_csv_button.setToolTip("CSV 파일을 열어 재생 세션을 시작합니다.")
        self.open_csv_button.clicked.connect(self._open_csv_dialog)
        self.home_button = QtWidgets.QPushButton()
        self.home_button.setObjectName("playbackHomeButton")
        self._configure_playback_icon_button(
            self.home_button,
            icon_name="skip_backward",
            tooltip="처음으로 이동",
        )
        self.home_button.clicked.connect(lambda: self.seek_to_time_ms(0))
        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setObjectName("playbackStopButton")
        self._configure_playback_icon_button(
            self.stop_button,
            icon_name="stop",
            tooltip="정지하고 처음으로 이동",
        )
        self.stop_button.clicked.connect(self._stop_playback)
        self.end_button = QtWidgets.QPushButton()
        self.end_button.setObjectName("playbackEndButton")
        self._configure_playback_icon_button(
            self.end_button,
            icon_name="skip_forward",
            tooltip="끝으로 이동",
        )
        self.end_button.clicked.connect(
            lambda: self.seek_to_time_ms(self.playback_state.total_time_ms)
        )
        self.prev_event_button = QtWidgets.QPushButton()
        self.prev_event_button.setObjectName("playbackPrevEventButton")
        self._configure_playback_icon_button(
            self.prev_event_button,
            icon_name="prev_event",
            tooltip="이전 이벤트",
        )
        self.prev_event_button.clicked.connect(self.seek_previous_event)
        self.play_pause_button = QtWidgets.QPushButton()
        self.play_pause_button.setObjectName("playbackPlayPauseButton")
        self._configure_playback_icon_button(
            self.play_pause_button,
            icon_name="play",
            tooltip="재생 / 일시 정지",
        )
        self.play_pause_button.clicked.connect(self._toggle_playback)
        self.next_event_button = QtWidgets.QPushButton()
        self.next_event_button.setObjectName("playbackNextEventButton")
        self._configure_playback_icon_button(
            self.next_event_button,
            icon_name="next_event",
            tooltip="다음 이벤트",
        )
        self.next_event_button.clicked.connect(self.seek_next_event)
        self.speed_combo = QtWidgets.QComboBox()
        self.speed_combo.setObjectName("playbackSpeedCombo")
        self.speed_combo.addItems(("0.25x", "0.5x", "1x", "2x", "4x"))
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._set_playback_speed_from_text)
        for widget in (
            self.open_csv_button,
            self.home_button,
            self.stop_button,
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

        self.playback_lower_strip = QtWidgets.QFrame()
        self.playback_lower_strip.setObjectName("playbackLowerStrip")
        lower_row = QtWidgets.QHBoxLayout(self.playback_lower_strip)
        lower_row.setContentsMargins(8, 5, 8, 5)
        lower_row.setSpacing(8)

        self.playback_event_section = QtWidgets.QFrame()
        self.playback_event_section.setObjectName("playbackEventSection")
        event_section_layout = QtWidgets.QVBoxLayout(self.playback_event_section)
        event_section_layout.setContentsMargins(8, 4, 10, 4)
        event_section_layout.setSpacing(4)
        self.playback_event_section_title = QtWidgets.QLabel("Events")
        self.playback_event_section_title.setObjectName("playbackSectionTitle")
        self.event_marker_list = QtWidgets.QListWidget()
        self.event_marker_list.setObjectName("eventMarkerList")
        self.event_marker_list.setMaximumHeight(58)
        self.event_marker_list.currentItemChanged.connect(self._seek_to_event_item)
        event_section_layout.addWidget(self.playback_event_section_title)
        event_section_layout.addWidget(self.event_marker_list, 1)

        self.playback_sensor_section = QtWidgets.QFrame()
        self.playback_sensor_section.setObjectName("playbackSensorSection")
        sensor_section_layout = QtWidgets.QVBoxLayout(self.playback_sensor_section)
        sensor_section_layout.setContentsMargins(8, 4, 0, 4)
        sensor_section_layout.setSpacing(4)
        self.playback_sensor_section_title = QtWidgets.QLabel("Current sensors")
        self.playback_sensor_section_title.setObjectName("playbackSectionTitle")
        self.sensor_card_container = QtWidgets.QWidget()
        self.sensor_card_container.setObjectName("sensorCardContainer")
        self.sensor_card_layout = QtWidgets.QHBoxLayout(self.sensor_card_container)
        self.sensor_card_layout.setContentsMargins(0, 0, 0, 0)
        self.sensor_card_layout.setSpacing(6)
        self.sensor_card_value_labels: dict[str, QtWidgets.QLabel] = {}
        self._build_sensor_cards()
        self.sensor_card_scroll_area = QtWidgets.QScrollArea()
        self.sensor_card_scroll_area.setObjectName("sensorCardScrollArea")
        self.sensor_card_scroll_area.setWidgetResizable(True)
        self.sensor_card_scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.sensor_card_scroll_area.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.sensor_card_scroll_area.setMinimumHeight(72)
        self.sensor_card_scroll_area.setWidget(self.sensor_card_container)
        sensor_section_layout.addWidget(self.playback_sensor_section_title)
        sensor_section_layout.addWidget(self.sensor_card_scroll_area, 1)
        lower_row.addWidget(self.playback_event_section, 1)
        lower_row.addWidget(self.playback_sensor_section, 2)

        self.playback_warning_label = QtWidgets.QLabel()
        self.playback_warning_label.setObjectName("playbackWarningLabel")

        layout.addWidget(self.playback_dock_divider)
        layout.addWidget(self.playback_status_strip)
        layout.addWidget(self.playback_controls_row)
        layout.addWidget(self.playback_lower_strip)
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
            if not query or query in _analysis_item_search_text(item)
        ]
        if self.sidebar_settings.sort_mode == "A-Z":
            items = sorted(items)

        self.analysis_list.clear()
        for item in items:
            self.analysis_list.addItem(item)
        self._populate_analysis_tree(set(items))

    def _populate_analysis_tree(self, visible_items: set[str]) -> None:
        if not hasattr(self, "analysis_tree"):
            return
        self.analysis_tree.clear()
        for group_name, group_items in SIDEBAR_GROUPS.items():
            children = [item for item in group_items if item in visible_items]
            if not children:
                continue
            group_item = QtWidgets.QTreeWidgetItem([group_name])
            group_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, "")
            group_item.setExpanded(True)
            self.analysis_tree.addTopLevelItem(group_item)
            for title in children:
                child = QtWidgets.QTreeWidgetItem([title])
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, title)
                group_item.addChild(child)

    def sidebar_item_titles(self, group_name: str) -> list[str]:
        for index in range(self.analysis_tree.topLevelItemCount()):
            group_item = self.analysis_tree.topLevelItem(index)
            if group_item.text(0) == group_name:
                return [
                    group_item.child(child_index).text(0)
                    for child_index in range(group_item.childCount())
                ]
        return []

    def _handle_sidebar_tree_item_activated(
        self,
        item: QtWidgets.QTreeWidgetItem,
        _column: int,
    ) -> None:
        title = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        if title:
            parent = item.parent()
            if parent is not None:
                self.selected_sidebar_group = parent.text(0)
            self.add_analysis_window(title)

    def _select_sidebar_group(self, group_name: str) -> None:
        if not hasattr(self, "analysis_tree"):
            return
        for index in range(self.analysis_tree.topLevelItemCount()):
            group_item = self.analysis_tree.topLevelItem(index)
            if group_item.text(0) == group_name:
                self.analysis_tree.setCurrentItem(group_item)
                self.selected_sidebar_group = group_name
                return

    def _select_sidebar_group_for_window(self, title: str) -> None:
        if not hasattr(self, "analysis_tree"):
            return
        for group_index in range(self.analysis_tree.topLevelItemCount()):
            group_item = self.analysis_tree.topLevelItem(group_index)
            for child_index in range(group_item.childCount()):
                child_item = group_item.child(child_index)
                if child_item.text(0) == title:
                    self.analysis_tree.setCurrentItem(group_item)
                    self.selected_sidebar_group = group_item.text(0)
                    return

    def _add_selected_analysis_window(self) -> None:
        tree_item = self.analysis_tree.currentItem() if hasattr(self, "analysis_tree") else None
        if tree_item is not None:
            title = str(tree_item.data(0, QtCore.Qt.ItemDataRole.UserRole))
            if title:
                parent = tree_item.parent()
                if parent is not None:
                    self.selected_sidebar_group = parent.text(0)
                self.add_analysis_window(title)
                return

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

    def _export_report_dialog(self) -> None:
        default_path = self.report_output_path or Path.cwd() / "mflog-report.html"
        path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Report",
            str(default_path),
            "HTML Report (*.html);;All files (*.*)",
        )
        if path:
            self.export_report_file(Path(path))

    def save_project_file(self, project_path: Path) -> ProjectState:
        try:
            state = self.capture_project_state(csv_path=self.loaded_csv_path)
            save_project_state(project_path, state)
        except OSError as exc:
            log_path = log_exception(exc, context=f"save project: {project_path}")
            self.playback_warning_label.setText(f"Project save failed. Log: {log_path.name}")
            raise
        self.statusBar().showMessage(f"Project saved: {project_path.name}")
        return state

    def open_project_file(self, project_path: Path) -> bool:
        try:
            state = _resolve_project_state_paths(
                load_project_state(project_path),
                project_path.parent,
            )
        except (OSError, ValueError) as exc:
            log_path = log_exception(exc, context=f"open project: {project_path}")
            self.playback_warning_label.setText(f"Project open failed. Log: {log_path.name}")
            raise
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

    def export_report_file(self, output_path: Path) -> None:
        try:
            html = render_html_report(
                session={
                    "file_name": (
                        self.loaded_csv_path.name
                        if self.loaded_csv_path is not None
                        else "No CSV"
                    ),
                    "row_count": self.session_row_count,
                    "duration_seconds": self.playback_state.total_time_ms / 1000.0,
                    "sample_ms": self.session_sampling_interval_ms,
                    "event_count": len(self.playback_events),
                },
                selected_channels=tuple(self._selected_time_series_channels()),
                event_reviews=self.event_reviews,
                segment_summaries=self._segment_summaries(),
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            write_html_report(output_path, html)
        except OSError as exc:
            log_path = log_exception(exc, context=f"export report: {output_path}")
            self.playback_warning_label.setText(f"Report export failed. Log: {log_path.name}")
            raise

        self.report_output_path = output_path
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, ExportReportWindow):
                widget.set_output_path(output_path)
        self.statusBar().showMessage(f"Report exported: {output_path.name}")

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
            available_sensor_channels=_available_sensor_channels_from_store(result.store),
            events=_detect_playback_markers(result.store, timestamps),
            row_count=result.store.row_count,
            sampling_interval_ms=_estimate_sampling_interval_ms(timestamps),
            autosave_warning=warning,
        )
        self.complete_data_load_for_pending_project(csv_path)

    def _configure_playback_session(
        self,
        *,
        csv_path: Path,
        timestamps: list[float],
        sensor_series: dict[str, list[float]],
        events: tuple[PlaybackMarker, ...],
        row_count: int,
        sampling_interval_ms: int,
        available_sensor_channels: set[str] | None = None,
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
        self.available_sensor_channels = (
            set(sensor_series)
            if available_sensor_channels is None
            else set(available_sensor_channels)
        )
        self._populate_time_series_channel_list()
        self._populate_ideal_path_steering_channel_combo()
        self._remember_gps_route(csv_path, sensor_series)
        self.playback_events = events
        self.event_reviews = _event_reviews_from_markers(events)
        self.analysis_segments = ()
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
            sub_window.set_analysis_opacity(window_state.opacity)

    def _toggle_playback(self) -> None:
        if self.playback_state.is_playing:
            self.playback_state.pause()
            self.playback_timer.stop()
        else:
            self.playback_state.play()
            self._playback_elapsed.restart()
            self.playback_timer.start()
        self._update_playback_dock_status()

    def _stop_playback(self) -> None:
        if self.playback_state.is_playing:
            self.playback_state.pause()
        self.playback_timer.stop()
        self.seek_to_time_ms(0)
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
        self._set_playback_button_icon(self.play_pause_button, "play")

    def sensor_card_value(self, channel_id: str) -> str:
        return self.sensor_card_value_labels[channel_id].text()

    def _set_playback_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.home_button,
            self.stop_button,
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
        self._set_playback_button_icon(
            self.play_pause_button,
            "pause" if self.playback_state.is_playing else "play",
        )
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
                color: #edf3f7;
            }
            QWidget#centralWorkspaceContainer {
                background: #202326;
                color: #edf3f7;
            }
            QMdiArea#workspace {
                background: #0f1418;
                border-top: 1px solid #3f4a52;
                border-left: 1px solid #303a41;
                border-right: 1px solid #303a41;
            }
            QMdiSubWindow {
                background: #1d2429;
                border: 1px solid #6f838e;
            }
            QMdiSubWindow::title {
                background: #334450;
                color: #f4f8fb;
                padding: 4px 8px;
                border-bottom: 1px solid #6b7d87;
            }
            QMdiSubWindow::title:active {
                background: #405665;
                color: #ffffff;
            }
            QMdiSubWindow::close-button,
            QMdiSubWindow::normal-button,
            QMdiSubWindow::minimize-button {
                background: #334450;
                border: none;
                width: 22px;
                height: 20px;
            }
            QMdiSubWindow::close-button:hover {
                background: #9f4d4d;
            }
            QMdiSubWindow::normal-button:hover,
            QMdiSubWindow::minimize-button:hover {
                background: #4f6675;
            }
            QMenuBar, QMenu, QDockWidget, QStatusBar, QTabBar::tab {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                background: #2b2f33;
                color: #edf3f7;
            }
            QDockWidget {
                background: #181d21;
                color: #edf3f7;
                border: 1px solid #4f5e68;
            }
            QDockWidget::title {
                background: #252c31;
                color: #ffffff;
                padding: 6px 8px;
                border-bottom: 1px solid #56636d;
                font-weight: 700;
            }
            QDockWidget#leftSidebar {
                border-right: 1px solid #62717b;
            }
            QDockWidget#playbackDock {
                border-top: 3px solid #f4c95d;
            }
            QSplitter::handle {
                background: #303a41;
                border: 1px solid #4a5660;
            }
            QTabBar#presetTabs {
                background: #202326;
                color: #edf3f7;
                border-bottom: 1px solid #3a4046;
            }
            QTabBar#presetTabs::tab {
                background: #242a2f;
                color: #edf3f7;
            }
            QTabBar#presetTabs::tab:hover {
                background: #303941;
                color: #ffffff;
            }
            QTabBar#presetTabs::tab:selected {
                background: #3a4046;
                color: #f4c95d;
            }
            QMenu::item {
                color: #edf3f7;
                background: transparent;
                padding: 5px 24px 5px 18px;
            }
            QMenu::item:selected {
                color: #ffffff;
                background: #3d5566;
            }
            QDockWidget#propertiesPanel {
                background: #1a1f22;
                color: #f4f8fb;
                border-left: 1px solid #4a5660;
            }
            QDockWidget#propertiesPanel::title {
                background: #252b30;
                color: #ffffff;
                padding: 6px;
                border-bottom: 1px solid #4a5660;
            }
            QWidget#propertiesPanelContent {
                background: #1a1f22;
            }
            QLabel#propertiesSelectionLabel {
                color: #ffffff;
                font-weight: 700;
                padding: 5px 8px;
                background: #252b30;
                border: 1px solid #4a5660;
            }
            QTabBar::tab {
                padding: 8px 12px;
                border-right: 1px solid #3a4046;
            }
            QTabBar::tab:selected {
                background: #3a4046;
                color: #f4c95d;
            }
            QFrame#workspaceCommandBar {
                background: #242a2f;
                border-top: 1px solid #38434b;
                border-bottom: 1px solid #4a5660;
            }
            QFrame#workspaceCommandBar QLabel#workspaceCommandLabel {
                color: #f4c95d;
                font-weight: 700;
                padding-right: 4px;
            }
            QFrame#workspaceCommandBar QToolButton {
                background: #303941;
                color: #f2f6f8;
                border: 1px solid #56636d;
                padding: 5px 9px;
                font-weight: 600;
            }
            QFrame#workspaceCommandBar QToolButton:hover {
                background: #3d5566;
                border: 1px solid #f4c95d;
            }
            QLineEdit, QListWidget, QTreeWidget, QComboBox, QAbstractSpinBox, QTableWidget {
                background: #11161a;
                color: #f2f6f8;
                border: 1px solid #5a6872;
                padding: 6px;
            }
            QAbstractItemView::item:selected {
                background: #3d5566;
                color: #ffffff;
                border-left: 3px solid #f4c95d;
            }
            QHeaderView::section {
                background: #26313a;
                color: #f2f6f8;
                border: 1px solid #5a6872;
                padding: 5px 6px;
            }
            QLineEdit:focus, QListWidget:focus, QTreeWidget:focus, QComboBox:focus, QAbstractSpinBox:focus {
                border: 2px solid #f4c95d;
            }
            QLineEdit:disabled, QListWidget:disabled, QTreeWidget:disabled, QComboBox:disabled,
            QAbstractSpinBox:disabled, QPushButton:disabled {
                background: #2d3338;
                color: #b8c3ca;
                border: 1px solid #4b555d;
            }
            QListWidget::item {
                color: #f2f6f8;
                padding: 4px 6px;
            }
            QListWidget::item:selected, QListWidget::item:hover {
                background: #314251;
                color: #ffffff;
            }
            QListWidget::indicator {
                width: 17px;
                height: 17px;
                border: 1px solid #b9c8d1;
                border-radius: 4px;
                margin-left: 3px;
                margin-right: 6px;
                background: #26313a;
            }
            QListWidget::indicator:unchecked {
                background: #26313a;
                border: 1px solid #b9c8d1;
            }
            QListWidget::indicator:checked {
                background: #f4c95d;
                border: 2px solid #ffffff;
            }
            QListWidget::indicator:disabled {
                background: #2b3034;
                border: 1px solid #4b555d;
            }
            QScrollBar:vertical {
                background: #182126;
                border-left: 1px solid #3f4a52;
                width: 13px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #c7d1d8;
                border: 1px solid #edf3f7;
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ffffff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
                height: 0;
            }
            QScrollBar:horizontal {
                background: #182126;
                border-top: 1px solid #3f4a52;
                height: 13px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #c7d1d8;
                border: 1px solid #edf3f7;
                border-radius: 5px;
                min-width: 30px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #ffffff;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
                width: 0;
            }
            QComboBox QAbstractItemView {
                background: #10161a;
                color: #f2f6f8;
                selection-background-color: #3d5566;
                selection-color: #ffffff;
                border: 1px solid #5a6872;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                color: #f2f6f8;
                background: #10161a;
                min-height: 26px;
                padding: 5px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #314251;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #3d5566;
                color: #ffffff;
            }
            QFrame#settingsGroupFrame {
                background: #151a1e;
                border: 1px solid #56636d;
            }
            QFrame#settingsRow {
                background: #20262a;
                border: 1px solid #39454d;
            }
            QLabel#settingsRowLabel {
                color: #f4c95d;
                font-weight: 700;
            }
            QLabel#settingsValueLabel {
                color: #f4f8fb;
                font-weight: 600;
            }
            QLabel#propertiesScopeLabel {
                color: #c7d1d8;
                background: #20262a;
                border: 1px solid #46545e;
                padding: 6px 8px;
            }
            QCheckBox {
                color: #f2f6f8;
                spacing: 8px;
            }
            QCheckBox:disabled {
                color: #b8c3ca;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1px solid #b9c8d1;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background: #26313a;
            }
            QCheckBox::indicator:checked {
                background: #f4c95d;
                border: 2px solid #ffffff;
            }
            QCheckBox::indicator:disabled {
                background: #2b3034;
                border: 1px solid #4b555d;
            }
            QComboBox::drop-down {
                border-left: 1px solid #5a6872;
                width: 24px;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #f2f6f8;
                margin-right: 7px;
            }
            QComboBox::down-arrow:disabled {
                border-top: 6px solid #8f9aa2;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #101418;
                border: 1px solid #3f4a52;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                background: #f4c95d;
                border: 1px solid #ffffff;
            }
            QFrame#playbackDockContent {
                background: #10161a;
                border: none;
            }
            QFrame#playbackDockDivider {
                background: #f4c95d;
                border: none;
            }
            QFrame#playbackStatusStrip {
                background: transparent;
                border: none;
                border-bottom: 1px solid #39454d;
            }
            QFrame#playbackStatusStrip QLabel {
                color: #e8f0f5;
                font-weight: 600;
            }
            QFrame#playbackTransportStrip {
                background: #151d22;
                border: none;
                border-bottom: 1px solid #39454d;
            }
            QFrame#playbackLowerStrip {
                background: transparent;
                border: none;
            }
            QFrame#playbackEventSection {
                background: transparent;
                border: none;
                border-right: 1px solid #39454d;
            }
            QFrame#playbackSensorSection {
                background: transparent;
                border: none;
            }
            QLabel#playbackSectionTitle {
                color: #f4c95d;
                background: transparent;
                font-weight: 700;
                padding: 0 0 3px 0;
            }
            QPushButton[playbackSymbol="true"] {
                background: #222d35;
                color: #f4f8fb;
                border: 1px solid #65757f;
                border-radius: 3px;
                padding: 0;
                min-width: 34px;
                max-width: 34px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton[playbackSymbol="true"]:hover {
                background: #334a58;
                border: 1px solid #f4c95d;
            }
            QPushButton[playbackIcon="play"],
            QPushButton[playbackIcon="pause"] {
                background: #315b73;
                border: 1px solid #7aa7bf;
            }
            QPushButton[playbackSymbol="true"]:disabled {
                background: #1b2228;
                border: 1px solid #3b464e;
            }
            QFrame#sensorCard {
                background: #10161a;
                border: none;
                border-left: 1px solid #4a5660;
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
                border: 1px solid #5d8dad;
                padding: 7px 10px;
            }
            QPushButton:hover {
                background: #4a7fa1;
            }
            QLabel {
                font-family: "Malgun Gothic", "Segoe UI", sans-serif;
                color: #edf3f7;
            }
            QWidget#timeSeriesWindow, QWidget#ggDiagramWindow, QWidget#gpsMapWindow,
            QWidget#currentValuesWindow, QWidget#dataAnalysisWindow,
            QWidget#documentsWindow, QWidget#benchmarkSummaryWindow,
            QWidget#vehicleModelWindow, QWidget#vehicleDynamicsWindow,
            QWidget#tireTemperatureWindow {
                background: #151a1e;
            }
            QLabel#hoverLabel, QLabel#reliabilityBadge, QLabel#gpsMapBackgroundStatus,
            QLabel#gpsIdealPathStatus,
            QLabel#vehicleCameraStatus, QLabel#vehicleQualitativeNote,
            QLabel#vehicleAttitudeStatus, QLabel#dataAnalysisSummary,
            QLabel#documentsSummary, QLabel#benchmarkSummaryText {
                color: #dce7ee;
                background: #20262a;
                border: 1px solid #39454d;
                padding: 4px 6px;
            }
            QFrame#analysisWindowFrame {
                background: #151d22;
                border: 1px solid #6f838e;
            }
            QFrame#analysisWindowFrame QWidget {
                background: #10161a;
            }
            QFrame#analysisWindowFrame[active="true"] {
                background: #182126;
                border: 2px solid #f4c95d;
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
        "steering angle": [
            8.0 * math.sin(index / 12.0) for index in range(sample_count)
        ],
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
        "steering angle",
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
    series = {
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
        "steering angle": _numeric_series(
            store,
            sample_count,
            "SteeringAngle_deg",
            "Steering_Angle_deg",
            "STEERING_ANGLE_DEG",
            "steering angle",
            "SteeringAngle",
            "Steering",
            "SAS_Angle",
        ),
        "latitude": _numeric_series(store, sample_count, "Latitude", "latitude"),
        "longitude": _numeric_series(store, sample_count, "Longitude", "longitude"),
    }
    for channel_id, values in _raw_numeric_sensor_series(store, sample_count).items():
        series.setdefault(channel_id, values)
    return series


def _available_sensor_channels_from_store(store: ColumnStore) -> set[str]:
    available = set(store.raw_column_names)
    available.update(store.standard_sources)
    available.update(compute_basic_derived_channels(store))

    if _store_values(store, "GPS_Speed_KPH", "VSS_kmh", "VSS", "GPS speed") is not None:
        available.update({"GPS speed", "VSS / GPS speed"})
    if _store_values(store, "AX_CORRECTED_G", "AX_RAW_G", "ax_g", "ax") is not None:
        available.update({"AX_CORRECTED_G", "ax"})
    if _store_values(store, "AY_CORRECTED_G", "AY_RAW_G", "ay_g", "ay") is not None:
        available.update({"AY_CORRECTED_G", "ay"})
    if _store_values(store, "gz_dps", "yaw rate") is not None:
        available.add("yaw rate")
    if (
        _store_values(
            store,
            "SteeringAngle_deg",
            "Steering_Angle_deg",
            "STEERING_ANGLE_DEG",
            "steering angle",
            "SteeringAngle",
            "Steering",
            "SAS_Angle",
        )
        is not None
    ):
        available.add("steering angle")

    return available


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


def _raw_numeric_sensor_series(store: ColumnStore, sample_count: int) -> dict[str, list[float]]:
    output: dict[str, list[float]] = {}
    for column_id in store.raw_column_names:
        if column_id.lower() in {"time", "timestamp"}:
            continue
        raw_values = _store_values(store, column_id)
        if raw_values is None:
            continue
        values: list[float] = []
        saw_numeric = False
        for raw_value in raw_values[:sample_count]:
            parsed = _parse_float(raw_value)
            if parsed is None:
                values.append(0.0)
            else:
                values.append(parsed)
                saw_numeric = True
        if not saw_numeric:
            continue
        if len(values) < sample_count:
            values.extend(0.0 for _index in range(sample_count - len(values)))
        output[column_id] = values
    return output


def _time_series_channel_options(sensor_series: dict[str, list[float]]) -> list[str]:
    preferred = (
        "RPM",
        "TPS_percent",
        "GPS speed",
        "VSS / GPS speed",
        "Gear",
        "Battery voltage",
        "AX_CORRECTED_G",
        "AY_CORRECTED_G",
        "ax",
        "ay",
        "roll rate",
        "pitch rate",
        "yaw rate",
        "steering angle",
    )
    options: list[str] = []
    for channel_id in preferred:
        if channel_id in sensor_series and channel_id not in options:
            options.append(channel_id)
    for channel_id in sorted(sensor_series):
        if channel_id in {"latitude", "longitude"}:
            continue
        if channel_id not in options:
            options.append(channel_id)
    return options


def _time_series_channel_item_label(channel_id: str, checked: bool) -> str:
    return f"✓ {channel_id}" if checked else channel_id


def _time_series_channel_id_from_item(item: QtWidgets.QListWidgetItem) -> str:
    channel_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
    if channel_id is not None:
        return str(channel_id)
    return item.text().removeprefix("✓ ").strip()


def _steering_channel_options(sensor_series: dict[str, list[float]]) -> list[str]:
    preferred = (
        "Auto",
        "steering angle",
        "SteeringAngle_deg",
        "Steering_Angle_deg",
        "STEERING_ANGLE_DEG",
        "SteeringAngle",
        "Steering",
        "SAS_Angle",
    )
    options: list[str] = []
    for channel_id in preferred:
        if channel_id == "Auto" or channel_id in sensor_series:
            if channel_id not in options:
                options.append(channel_id)
    for channel_id in _time_series_channel_options(sensor_series):
        if channel_id not in options:
            options.append(channel_id)
    return options


def _selected_steering_channel(
    selected_channel: str,
    sensor_series: dict[str, list[float]],
) -> str:
    if selected_channel and selected_channel != "Auto" and selected_channel in sensor_series:
        return selected_channel
    for candidate in (
        "steering angle",
        "SteeringAngle_deg",
        "Steering_Angle_deg",
        "STEERING_ANGLE_DEG",
        "SteeringAngle",
        "Steering",
        "SAS_Angle",
    ):
        if candidate in sensor_series:
            return candidate
    return ""


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


def _event_reviews_from_markers(markers: Sequence[PlaybackMarker]) -> tuple[EventReview, ...]:
    return build_event_reviews(
        {
            "name": marker.name,
            "time_ms": marker.time_ms,
            "severity": marker.severity,
            "sensor": marker.sensor,
            "value": marker.value,
            "condition": marker.condition,
        }
        for marker in markers
    )


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


def _graph_line_color_name(color: str | None) -> str:
    if color is None:
        return "Default"
    for name in ("Yellow", "Blue", "Green", "Red"):
        if _graph_line_color(name) == color:
            return name
    return "Default"


def _visualization_settings_to_dict(settings: VisualizationSettings) -> dict[str, Any]:
    return {
        "gps_map_background_enabled": settings.gps_map_background_enabled,
        "graph_line_color": settings.graph_line_color,
        "graph_line_width": settings.graph_line_width,
        "gg_limit_radius": settings.gg_limit_radius,
    }


def _visualization_settings_from_dict(
    data: dict[str, Any],
    *,
    fallback: VisualizationSettings,
) -> VisualizationSettings:
    if not data:
        return fallback
    return VisualizationSettings(
        gps_map_background_enabled=bool(
            data.get("gps_map_background_enabled", fallback.gps_map_background_enabled)
        ),
        graph_line_color=(
            None
            if data.get("graph_line_color", fallback.graph_line_color) in (None, "")
            else str(data.get("graph_line_color", fallback.graph_line_color))
        ),
        graph_line_width=float(data.get("graph_line_width", fallback.graph_line_width)),
        gg_limit_radius=float(data.get("gg_limit_radius", fallback.gg_limit_radius)),
    )


def _ideal_path_settings_to_dict(settings: IdealPathSettings) -> dict[str, Any]:
    return {
        "enabled": settings.enabled,
        "wheelbase_m": settings.wheelbase_m,
        "steering_ratio": settings.steering_ratio,
        "steering_channel": settings.steering_channel,
    }


def _ideal_path_settings_from_dict(
    data: dict[str, Any],
    *,
    fallback: IdealPathSettings,
) -> IdealPathSettings:
    if not data:
        return fallback
    return IdealPathSettings(
        enabled=bool(data.get("enabled", fallback.enabled)),
        wheelbase_m=float(data.get("wheelbase_m", fallback.wheelbase_m)),
        steering_ratio=float(data.get("steering_ratio", fallback.steering_ratio)),
        steering_channel=str(data.get("steering_channel", fallback.steering_channel)),
    )


def _sidebar_settings_to_dict(settings: SidebarSettings) -> dict[str, Any]:
    return {
        "search_visible": settings.search_visible,
        "add_button_visible": settings.add_button_visible,
        "sort_mode": settings.sort_mode,
        "density": settings.density,
        "width_px": settings.width_px,
    }


def _sidebar_settings_from_dict(
    data: dict[str, Any],
    *,
    fallback: SidebarSettings,
) -> SidebarSettings:
    if not data:
        return fallback
    return SidebarSettings(
        search_visible=bool(data.get("search_visible", fallback.search_visible)),
        add_button_visible=bool(data.get("add_button_visible", fallback.add_button_visible)),
        sort_mode=str(data.get("sort_mode", fallback.sort_mode)),
        density=str(data.get("density", fallback.density)),
        width_px=int(data.get("width_px", fallback.width_px)),
    )


def _set_checked_without_signal(widget: QtWidgets.QCheckBox, checked: bool) -> None:
    widget.blockSignals(True)
    try:
        widget.setChecked(bool(checked))
    finally:
        widget.blockSignals(False)


def _set_combo_text_without_signal(widget: QtWidgets.QComboBox, text: str) -> None:
    widget.blockSignals(True)
    try:
        if widget.findText(text) >= 0:
            widget.setCurrentText(text)
    finally:
        widget.blockSignals(False)


def _set_spin_value_without_signal(
    widget: QtWidgets.QAbstractSpinBox,
    value: float | int,
) -> None:
    widget.blockSignals(True)
    try:
        if isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
    finally:
        widget.blockSignals(False)


def _analysis_item_search_text(title: str) -> str:
    aliases = SIDEBAR_SEARCH_ALIASES.get(title, ())
    return " ".join((title, *aliases)).lower()


def _preset_tab_tooltip(index: int) -> str:
    if index < 0 or index >= len(PRESET_TAB_MODES):
        return ""
    mode = PRESET_TAB_MODES[index]
    channels = ", ".join(mode.channels) if mode.channels else "default"
    return f"windows: {', '.join(mode.windows)}\nchannels: {channels}"


def _preset_tab_tooltip_for_title(tab_title: str) -> str:
    try:
        return _preset_tab_tooltip(DEFAULT_PRESET_TABS.index(tab_title))
    except ValueError:
        return tab_title


def _resolve_project_state_paths(state: ProjectState, base_dir: Path) -> ProjectState:
    return replace(
        state,
        csv_path=_resolve_optional_project_path(state.csv_path, base_dir),
        vehicle_model_path=_resolve_optional_project_path(state.vehicle_model_path, base_dir),
        reference_route_path=_resolve_optional_project_path(
            state.reference_route_path,
            base_dir,
        ),
        video_path=_resolve_optional_project_path(state.video_path, base_dir),
        report_output_path=_resolve_optional_project_path(state.report_output_path, base_dir),
    )


def _resolve_optional_project_path(path: Path | None, base_dir: Path) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return base_dir / path


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
