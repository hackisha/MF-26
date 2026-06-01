from mf_log_analyzer_v2.app.cursor_bus import CursorBus


def test_cursor_bus_publishes_playback_and_hover_times():
    bus = CursorBus()
    events = []
    bus.subscribe(lambda event: events.append((event.kind, event.time_sec)))

    bus.set_playback_time(12.3)
    bus.set_hover_time(13.7)
    bus.clear_hover_time()

    assert events == [("playback", 12.3), ("hover", 13.7), ("hover", None)]
