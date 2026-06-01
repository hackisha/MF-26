from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from mf_log_analyzer_v2.app.cursor_bus import CursorBus, CursorEvent
from mf_log_analyzer_v2.core.models import LogTable


class TimeSeriesWindow(QWidget):
    def __init__(self, log: LogTable, channels: list[str], cursor_bus: CursorBus) -> None:
        super().__init__()
        self.log = log
        self.channels = channels
        self.cursor_bus = cursor_bus

        self.plot_widget = pg.PlotWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        time_values = self.log.values(self.log.time_channel)
        for channel in self.channels:
            self.plot_widget.plot(time_values, self.log.values(channel), name=channel)

        self.playback_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#d97706", width=2),
        )
        self.hover_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#2563eb", width=1, style=Qt.PenStyle.DashLine),
        )
        self.hover_line.hide()

        self.plot_widget.addItem(self.playback_line)
        self.plot_widget.addItem(self.hover_line)
        self.cursor_bus.subscribe(self._handle_cursor_event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind == "playback" and event.time_sec is not None:
            self.playback_line.setValue(event.time_sec)
        elif event.kind == "hover":
            if event.time_sec is None:
                self.hover_line.hide()
                return
            self.hover_line.show()
            self.hover_line.setValue(event.time_sec)
