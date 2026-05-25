import pytest

from mflog_proto.playback import (
    CursorBus,
    CursorEvent,
    CursorKind,
    PlaybackState,
)


def test_playback_state_clamps_sample_and_reports_seconds():
    state = PlaybackState(timestamps=[0.0, 0.1, 0.2])

    assert state.current_sample == 0
    assert state.current_seconds == 0.0

    state.set_sample(99)

    assert state.current_sample == 2
    assert state.current_seconds == 0.2
    assert state.current_time_ms == 200
    assert state.total_time_ms == 200


def test_playback_state_seeks_by_milliseconds_and_tracks_speed():
    state = PlaybackState(timestamps=[0.0, 0.1, 0.2, 0.3])

    state.set_time_ms(210)
    state.set_speed(2.0)

    assert state.current_sample == 2
    assert state.current_time_ms == 210
    assert state.current_seconds == 0.21
    assert state.playback_speed == 2.0


def test_playback_state_keeps_unsnapped_current_time_between_samples():
    state = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    events: list[CursorEvent] = []
    state.subscribe(events.append)

    state.set_time_ms(33)

    assert state.current_time_ms == 33
    assert state.current_seconds == 0.033
    assert state.current_sample == 0
    assert events == [
        CursorEvent(kind=CursorKind.PLAYBACK, sample_index=0, seconds=0.033)
    ]


def test_playback_state_requires_sorted_timestamps():
    with pytest.raises(ValueError, match="timestamps must be sorted"):
        PlaybackState(timestamps=[0.0, 0.2, 0.1])


def test_playback_state_selects_nearest_sample_for_seconds():
    state = PlaybackState(timestamps=[0.0, 0.1, 0.3, 0.6])

    state.set_seconds(0.26)

    assert state.current_sample == 2
    assert state.current_seconds == 0.26


def test_playback_state_reports_nearest_sample_without_moving_cursor():
    state = PlaybackState(timestamps=[0.0, 0.1, 0.3, 0.6])

    assert state.sample_at_seconds(0.26) == 2
    assert state.current_sample == 0


def test_playback_state_notifies_subscribers_on_position_change():
    state = PlaybackState(timestamps=[0.0, 0.5, 1.0])
    events: list[CursorEvent] = []
    state.subscribe(events.append)

    state.set_sample(1)

    assert events == [
        CursorEvent(kind=CursorKind.PLAYBACK, sample_index=1, seconds=0.5)
    ]


def test_cursor_bus_publishes_hover_and_unsubscribes():
    bus = CursorBus()
    events: list[CursorEvent] = []
    unsubscribe = bus.subscribe(events.append)

    assert bus.subscriber_count == 1

    bus.publish_hover(sample_index=3, seconds=1.25, channel_id="RPM", value=9200.0)
    unsubscribe()
    bus.publish_hover(sample_index=4, seconds=1.5)

    assert bus.subscriber_count == 0
    assert events == [
        CursorEvent(
            kind=CursorKind.HOVER,
            sample_index=3,
            seconds=1.25,
            channel_id="RPM",
            value=9200.0,
        )
    ]


def test_playback_state_exposes_cursor_subscriber_count():
    state = PlaybackState(timestamps=[0.0, 0.1])
    unsubscribe = state.subscribe(lambda event: None)

    assert state.subscriber_count == 1

    unsubscribe()

    assert state.subscriber_count == 0


def test_playback_state_publishes_hover_with_clamped_sample_time():
    state = PlaybackState(timestamps=[0.0, 0.5, 1.0])
    events: list[CursorEvent] = []
    state.subscribe(events.append)

    state.publish_hover(sample_index=99, channel_id="TPS", value=42.0)

    assert events == [
        CursorEvent(
            kind=CursorKind.HOVER,
            sample_index=2,
            seconds=1.0,
            channel_id="TPS",
            value=42.0,
        )
    ]


def test_play_pause_and_step_helpers_emit_playback_events():
    state = PlaybackState(timestamps=[0.0, 0.2, 0.4])
    events: list[CursorEvent] = []
    state.subscribe(events.append)

    state.play()
    state.step(1)
    state.pause()

    assert state.is_playing is False
    assert state.current_sample == 1
    assert events[-1] == CursorEvent(kind=CursorKind.PLAYBACK, sample_index=1, seconds=0.2)


def test_play_and_pause_emit_observable_playback_state_changes():
    state = PlaybackState(timestamps=[0.0, 0.2, 0.4])
    events: list[CursorEvent] = []
    state.subscribe(events.append)

    state.play()
    state.pause()

    assert events == [
        CursorEvent(
            kind=CursorKind.PLAYBACK,
            sample_index=0,
            seconds=0.0,
            is_playing=True,
        ),
        CursorEvent(
            kind=CursorKind.PLAYBACK,
            sample_index=0,
            seconds=0.0,
            is_playing=False,
        ),
    ]
