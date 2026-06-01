from __future__ import annotations

import polars as pl
from PySide6.QtCore import QCoreApplication, QEvent

from mf_log_analyzer_v2.app.cursor_bus import CursorBus
from mf_log_analyzer_v2.core.models import LogTable
from mf_log_analyzer_v2.ui.time_series_window import TimeSeriesWindow


def build_log_table() -> LogTable:
    return LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame(
            {
                "Timestamp": [0.0, 0.1, 0.2],
                "RPM": [1000.0, 1200.0, 1400.0],
            }
        ),
        time_channel="Timestamp",
    )


def test_time_series_window_updates_cursor_lines_from_bus(qtbot):
    log = build_log_table()
    bus = CursorBus()

    window = TimeSeriesWindow(log, ["RPM"], bus)
    qtbot.addWidget(window)

    bus.set_playback_time(0.1)
    bus.set_hover_time(0.2)

    assert window.playback_line.value() == 0.1
    assert window.hover_line.value() == 0.2


def test_time_series_window_clear_hover_hides_hover_line(qtbot):
    log = build_log_table()
    bus = CursorBus()

    window = TimeSeriesWindow(log, ["RPM"], bus)
    qtbot.addWidget(window)

    bus.set_hover_time(0.2)
    bus.clear_hover_time()

    assert not window.hover_line.isVisible()


def test_time_series_window_unsubscribes_from_cursor_bus_on_close(qtbot):
    log = build_log_table()
    bus = CursorBus()

    window = TimeSeriesWindow(log, ["RPM"], bus)
    qtbot.addWidget(window)

    assert len(bus._subscribers) == 1

    window.close()

    assert len(bus._subscribers) == 0


def test_time_series_window_unsubscribes_from_cursor_bus_on_delete_later(qtbot):
    log = build_log_table()
    bus = CursorBus()

    window = TimeSeriesWindow(log, ["RPM"], bus)

    assert len(bus._subscribers) == 1

    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert len(bus._subscribers) == 0
