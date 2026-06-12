# Video Sync Views Must Apply Current Playback Transport

## Problem

Playback-synchronized views can be opened after the shared CSV playback state is already playing. If a view only listens for future play/pause state changes, it may seek to the correct timestamp but never call its media backend's `play()` method.

This happened in `VideoSyncWindow`: `_last_is_playing` was initialized from `PlaybackState.is_playing`, and `set_video_path()` only set source and position. Opening the window or loading a video during active playback produced a synced position but a paused video.

## Prevention

When a view attaches to an already-active shared playback state or loads a new media source, force-apply the current transport state once after the source/position refresh.

Required checks:

- Add tests for "window opened while playback is already playing".
- Add tests for "media loaded while playback is already playing".
- Keep normal play/pause transition tests to avoid extra `pause()` or repeated `play()` calls.
- Keep missing-file paths from calling `play()`.

## Local Pattern

Use a helper equivalent to:

```python
def _apply_transport_state(self, *, force: bool = False) -> None:
    is_playing = self._playback_state.is_playing
    if is_playing == self._last_is_playing and not (force and is_playing):
        return
    self._last_is_playing = is_playing
    if is_playing and self._has_loaded_media():
        self._backend.play()
    else:
        self._backend.pause()
```

Call it with `force=True` after a valid media source is set.
