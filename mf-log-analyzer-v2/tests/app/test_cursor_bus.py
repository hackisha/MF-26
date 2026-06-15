from mf_log_analyzer_v2.app.cursor_bus import CursorBus


def test_cursor_bus_publishes_playback_and_hover_times():
    bus = CursorBus()
    events = []
    bus.subscribe(lambda event: events.append((event.kind, event.time_sec)))

    bus.set_playback_time(12.3)
    bus.set_hover_time(13.7)
    bus.clear_hover_time()

    assert events == [("playback", 12.3), ("hover", 13.7), ("hover", None)]


def test_cursor_bus_stores_playback_and_hover_times():
    bus = CursorBus()

    bus.set_playback_time(12.3)
    bus.set_hover_time(13.7)

    assert bus.playback_time_sec == 12.3
    assert bus.hover_time_sec == 13.7

    bus.clear_hover_time()

    assert bus.playback_time_sec == 12.3
    assert bus.hover_time_sec is None


def test_cursor_bus_publishes_over_subscriber_copy():
    bus = CursorBus()
    events = []

    def late_subscriber(event):
        events.append(("late", event.kind, event.time_sec))

    def adding_subscriber(event):
        events.append(("adding", event.kind, event.time_sec))
        bus.subscribe(late_subscriber)

    bus.subscribe(adding_subscriber)

    bus.set_playback_time(1.0)
    bus.set_hover_time(2.0)

    assert events == [
        ("adding", "playback", 1.0),
        ("adding", "hover", 2.0),
        ("late", "hover", 2.0),
    ]


def test_cursor_bus_unsubscribes_callback():
    bus = CursorBus()
    events = []

    def subscriber(event):
        events.append((event.kind, event.time_sec))

    bus.subscribe(subscriber)
    bus.unsubscribe(subscriber)

    bus.set_playback_time(1.0)

    assert events == []


def test_cursor_bus_unsubscribe_absent_callback_is_noop():
    bus = CursorBus()
    events = []

    def subscriber(event):
        events.append((event.kind, event.time_sec))

    bus.unsubscribe(subscriber)
    bus.subscribe(subscriber)
    bus.unsubscribe(subscriber)
    bus.unsubscribe(subscriber)

    bus.set_hover_time(2.0)

    assert events == []
