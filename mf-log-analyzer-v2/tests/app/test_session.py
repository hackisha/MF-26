import polars as pl

from mf_log_analyzer_v2.app.session import PlaybackSession
from mf_log_analyzer_v2.core.models import LogTable


def test_playback_session_seek_and_tick():
    frame = pl.DataFrame({"Timestamp": [0.0, 1.0, 2.0]})
    log = LogTable(file_name="sample.csv", frame=frame, time_channel="Timestamp")
    session = PlaybackSession(log=log)

    session.seek(1.5)
    session.playback_speed = 2.0
    session.play()
    session.tick(0.25)

    assert session.current_time_sec == 2.0
    assert session.is_playing is False
