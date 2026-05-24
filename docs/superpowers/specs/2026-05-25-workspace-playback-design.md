# Workspace Playback Design

## Goal

Keep the standalone CSV Playback tab, but make Workspace the main replay cockpit by adding shared playback controls and current-time indicators across the plotted panels.

## UX Direction

Workspace should feel like the operator screen for replaying a run. The top of the Workspace owns the shared CSV time cursor, and the panels below show where that cursor is in each analysis view. The standalone CSV Playback tab remains available for focused row/value inspection, but the default Workspace presets should prioritize analysis panels instead of embedding a full playback panel.

## Scope

- Add a reusable playback control surface used by both `PlaybackView` and `WorkspaceView`.
- Add a compact shared playback bar to Workspace.
- Remove playback panels from default Workspace presets while leaving playback available as an addable panel.
- Add current-time indicators to Time-Series and Map/Lap plots.
- Keep the existing Behavior current sample marker and 3D cue behavior.

## Out Of Scope

- Removing the CSV Playback tab.
- Drag-and-drop panel layout.
- Multi-log comparison.
- Per-panel independent time cursors.

## Acceptance Criteria

- Workspace shows shared playback controls when a CSV is loaded.
- Moving the Workspace timeline updates the global `currentTimeSec`.
- Time-Series shows a vertical current-time cursor.
- Map/Lap shows a highlighted current coordinate sample.
- Existing pop-out windows keep using the same session snapshot and shared selection sync.
