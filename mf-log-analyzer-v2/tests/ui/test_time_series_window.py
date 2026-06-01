from __future__ import annotations

import polars as pl

from mf_log_analyzer_v2.app.cursor_bus import CursorBus
from mf_log_analyzer_v2.core.models import LogTable
from mf_log_analyzer_v2.ui.time_series_window import TimeSeriesWindow


def test_time_series_window_updates_cursor_lines_from_bus(qtbot):
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame(
            {
                "Timestamp": [0.0, 0.1, 0.2],
                "RPM": [1000.0, 1200.0, 1400.0],
            }
        ),
        time_channel="Timestamp",
    )
    bus = CursorBus()

    window = TimeSeriesWindow(log, ["RPM"], bus)
    qtbot.addWidget(window)

    bus.set_playback_time(0.1)
    bus.set_hover_time(0.2)

    assert window.playback_line.value() == 0.1
    assert window.hover_line.value() == 0.2
