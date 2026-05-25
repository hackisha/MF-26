import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6 import QtCore
import pytest

from mflog_proto.playback import PlaybackState
from mflog_proto.ui.time_series_window import TimeSeriesWindow


_RETAINED_DISPOSED_WINDOWS: list[TimeSeriesWindow] = []


def test_time_series_window_renders_channels_and_tracks_playback_cursor(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2, 0.3])
    window = TimeSeriesWindow(playback_state=playback)
    qtbot.addWidget(window)

    window.set_series(
        {
            "RPM": ([0.0, 0.1, 0.2, 0.3], [1000.0, 2000.0, 3000.0, 4000.0]),
            "TPS": ([0.0, 0.1, 0.2, 0.3], [10.0, 20.0, 30.0, 40.0]),
        }
    )
    playback.set_sample(2)

    assert window.channel_count == 2
    assert window.cursor_line.value() == 0.2


def test_time_series_window_updates_hover_status_from_mouse_sample(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = TimeSeriesWindow(playback_state=playback)
    qtbot.addWidget(window)

    window.publish_hover(sample_index=1, channel_id="RPM", value=2000.0)

    assert window.hover_label.text() == "Hover | RPM | 0.100 s | 2000.000"


def test_time_series_window_requires_sorted_series_x_values(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = TimeSeriesWindow(playback_state=playback)
    qtbot.addWidget(window)

    with pytest.raises(ValueError, match="RPM.*sorted"):
        window.set_series({"RPM": ([0.0, 0.2, 0.1], [1000.0, 3000.0, 2000.0])})


def test_time_series_window_dispose_unsubscribes_from_playback(qapp):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = TimeSeriesWindow(playback_state=playback)

    assert playback.subscriber_count == 1

    window.dispose()
    _RETAINED_DISPOSED_WINDOWS.append(window)

    assert playback.subscriber_count == 0


def test_time_series_window_publishes_hover_from_plot_mouse_signal(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = TimeSeriesWindow(playback_state=playback)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    window.set_series({"RPM": ([0.0, 0.1, 0.2], [1000.0, 2000.0, 3000.0])})
    window.plot.setXRange(0.0, 0.2)
    window.plot.setYRange(1000.0, 3000.0)
    qtbot.waitExposed(window)

    scene_pos = window.plot.plotItem.vb.mapViewToScene(QtCore.QPointF(0.1, 2000.0))
    window.plot.scene().sigMouseMoved.emit(scene_pos)

    assert window.hover_label.text() == "Hover | RPM | 0.100 s | 2000.000"
