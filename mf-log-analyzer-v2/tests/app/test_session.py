import polars as pl

from mf_log_analyzer_v2.app.session import PlaybackSession
from mf_log_analyzer_v2.core.models import LogTable


def make_log(timestamps: list[float]) -> LogTable:
    frame = pl.DataFrame({"Timestamp": timestamps})
    return LogTable(file_name="sample.csv", frame=frame, time_channel="Timestamp")


def test_initial_current_time_sec_comes_from_log_start():
    session = PlaybackSession(log=make_log([5.0, 6.0, 7.0]))

    assert session.current_time_sec == 5.0


def test_seek_clamps_below_and_above_time_range():
    session = PlaybackSession(log=make_log([10.0, 11.0, 12.0]))

    session.seek(9.0)

    assert session.current_time_sec == 10.0

    session.seek(13.0)

    assert session.current_time_sec == 12.0


def test_tick_does_nothing_while_paused():
    session = PlaybackSession(log=make_log([0.0, 1.0, 2.0]))
    session.seek(1.0)

    session.tick(0.5)

    assert session.current_time_sec == 1.0
    assert session.is_playing is False


def test_playing_tick_advances_before_end_and_remains_playing():
    session = PlaybackSession(log=make_log([0.0, 1.0, 2.0]))

    session.play()
    session.tick(0.5)

    assert session.current_time_sec == 0.5
    assert session.is_playing is True


def test_playback_session_seek_and_tick():
    log = make_log([0.0, 1.0, 2.0])
    session = PlaybackSession(log=log)

    session.seek(1.5)
    session.playback_speed = 2.0
    session.play()
    session.tick(0.25)

    assert session.current_time_sec == 2.0
    assert session.is_playing is False


def test_tick_clamps_at_end_and_auto_pauses():
    session = PlaybackSession(log=make_log([0.0, 1.0, 2.0]))
    session.seek(1.75)

    session.play()
    session.tick(1.0)

    assert session.current_time_sec == 2.0
    assert session.is_playing is False
