# GoPro Video Sync Design

## Goal

Add a first-version GoPro driving video sync feature that lets users load a
recorded driving video, align it to the CSV playback timeline with a manual
millisecond offset, and inspect the video alongside GPS, G-G, time-series, and
current-value windows.

The app already uses `PlaybackState.current_time_ms` as the single playback
clock. The video feature must follow that clock instead of creating an
independent timeline.

## Scope

This first version implements manual offset sync only.

- Load one local video file into a new `Video Sync` analysis window.
- Use the shared CSV playback time to seek and play/pause the video.
- Let the user adjust a signed video offset in milliseconds.
- Display CSV time, video time, offset, media state, and file name.
- Persist video file path and offset in `.mflogproj`.
- Keep the current CSV session usable if the video file is missing, invalid, or
  fails to load.

## Non-Goals

- Automatic audio or visual synchronization.
- Multiple cameras.
- Frame-accurate telemetry overlay rendering into exported video.
- Video trimming, transcoding, or GoPro metadata extraction.

These are good future extensions, but v1 should make the core synchronized
analysis workflow reliable first.

## User Workflow

1. User opens a CSV and sees the normal playback dock.
2. User adds `Video Sync` from the left analysis panel.
3. In the `Video Sync` window or right properties panel, user selects a GoPro
   video file.
4. The video window seeks to:

   ```text
   video_time_ms = csv_current_time_ms + video_offset_ms
   ```

5. User changes the offset until an obvious moment in the video matches the
   telemetry, such as launch, braking, steering input, or an event marker.
6. Pressing play/pause, dragging the playback bar, clicking an event marker, or
   using keyboard seek keeps the video aligned to the shared CSV time.
7. Project save/open restores the video path and offset. If the file is missing,
   the project still opens and shows a warning inside the video window.

## UI Design

### Analysis Window

Add a `Video Sync` window to the visualization group.

The window contains:

- A `QVideoWidget` viewport.
- A compact status strip:
  - file name
  - CSV time
  - video time
  - offset
  - player state or warning
- Local controls:
  - `Load Video`
  - offset spin box in milliseconds
  - `-1000`, `-100`, `+100`, `+1000` nudge buttons
  - `Mute` toggle

The window must not duplicate the global CSV transport controls. The bottom
playback dock remains the primary play/pause/seek/speed control.

### Right Properties Panel

When `Video Sync` is the selected analysis window, show:

- video file path
- load/clear video buttons
- offset spin box
- mute toggle
- status text

These controls apply to the selected `Video Sync` window and to future video
windows through `MainWindow` state.

## Architecture

### `VideoSyncWindow`

Create a new PySide6 widget in `minimal_analysis_windows.py`:

- Constructor receives `PlaybackState`, optional video path, offset, and mute.
- Uses `QtMultimedia.QMediaPlayer` plus `QtMultimediaWidgets.QVideoWidget`.
- Subscribes to `PlaybackState` events.
- On playback cursor changes, computes target video time and seeks the media
  player.
- On app play/pause changes, starts or pauses the player.
- Exposes test helpers:
  - `video_path()`
  - `video_offset_ms()`
  - `target_video_time_ms()`
  - `status_text()`

Qt player behavior is asynchronous, so tests should cover the deterministic
sync calculation and state wiring without requiring a real codec.

### Playback Synchronization

The authoritative time remains:

```text
csv_time_ms = PlaybackState.current_time_ms
```

The derived media time is:

```text
video_time_ms = clamp(csv_time_ms + video_offset_ms, 0, media_duration_ms)
```

When the user seeks CSV:

- Update the player position if a video is loaded.
- Pause-state should remain controlled by the global CSV playback state.

When global playback is running:

- On every timer tick, `MainWindow` updates `PlaybackState`.
- The video window follows cursor events.
- If playback speed is not `1x`, v1 may either set the media playback rate when
  Qt supports it or keep video paused during non-1x speeds with a clear status.
  Preferred v1 behavior is to call `QMediaPlayer.setPlaybackRate(speed)` and
  show a warning if the backend ignores the rate.

### Persistence

Extend `ProjectState` with:

- `video_path: Path | None = None`
- `video_offset_ms: int = 0`
- `video_muted: bool = True`

Legacy `.mflogproj` files default to no video, zero offset, muted.

Restoring a project:

- Store the path and offset in `MainWindow`.
- If the video exists, new `Video Sync` windows load it.
- If it does not exist, keep the path in state and show a non-blocking warning.

### Error Handling

- Missing file: show warning, keep CSV playback enabled.
- Unsupported codec or load error: show warning from player error signal.
- Negative target video time: clamp to `0`.
- Target beyond media duration: clamp to duration when known.
- Video sync must never block CSV loading or playback.

## Tests

Focused tests should cover:

- `VideoSyncWindow` computes target video time from CSV time plus offset.
- Negative and over-duration targets are clamped.
- Offset changes update target time immediately.
- PlaybackState seek updates the window target time.
- MainWindow can add `Video Sync` from the left sidebar.
- Right properties panel for selected `Video Sync` exposes path/offset controls.
- Project state round-trips video path, offset, and muted state.
- Missing restored video path does not block project restore.

Manual acceptance should cover:

- Load a real GoPro or MP4 file.
- Seek the CSV playback bar and confirm the video follows.
- Adjust offset until a visible driving moment aligns with telemetry.
- Save/open project and confirm video path and offset restore.
- Remove/rename the video file and confirm project still opens with warning.

## Future Extensions

- Anchor-based semi-automatic sync: user marks a CSV time and matching video
  frame, then the app computes offset.
- Multi-anchor drift correction for long sessions.
- GoPro chapter-file stitching.
- Video overlay export with telemetry gauges.
- Audio/RPM correlation for automatic sync suggestions.

