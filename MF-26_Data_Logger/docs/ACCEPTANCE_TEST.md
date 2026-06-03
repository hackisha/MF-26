# MF-LOG-ANALYZER v2 Prototype Acceptance Test

Use these commands from the project root:

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
```

`QT_QPA_PLATFORM=minimal` is intentional on Windows. Do not use `offscreen` for
the normal pytest suite; it can trigger native PySide6/pyqtgraph teardown
crashes.

## 1. Automated Test Suite

```powershell
.\prototype\.venv\Scripts\python -m pytest .\prototype\tests
```

Expected result: all tests pass without a `python.exe` native error dialog.
The current expected count is `178 passed`.

## 2. Generate Target CSV

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.data.synthetic_log --rows 300000 --channels 200 --output .\prototype\.generated\synthetic_300k_200.csv
```

Generated input:

```text
prototype\.generated\synthetic_300k_200.csv
```

## 3. Readiness Report

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.benchmark.runner --json-output .\prototype\.generated\acceptance\benchmark_readiness.json --html-output .\prototype\.generated\acceptance\benchmark_readiness.html
```

This report verifies dependency readiness and marks target-scale categories as
`PENDING` until the measured benchmark below runs.

## 4. Target 300k x 200 Benchmark

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.benchmark.runner --target-benchmark --rows 300000 --channels 200 --input .\prototype\.generated\synthetic_300k_200.csv --json-output .\prototype\.generated\acceptance\target_300k_200.json --html-output .\prototype\.generated\acceptance\target_300k_200.html --playback-updates 900 --hover-queries 1000 --graph-channel-count 20 --graph-pixel-width 1200
```

Primary acceptance outputs:

```text
prototype\.generated\acceptance\benchmark_readiness.json
prototype\.generated\acceptance\benchmark_readiness.html
prototype\.generated\acceptance\target_300k_200.json
prototype\.generated\acceptance\target_300k_200.html
```

Latest local target run on 2026-05-25 passed all prototype gates:

| Gate | Result |
| --- | ---: |
| CSV loading | 0.603 s |
| Mapping | 0.0002 s |
| Derived channels | 0.042 s |
| Health checks | 0.157 s |
| Graph cache | 0.793 s |
| Playback cursor | 227,710 Hz measured update loop |
| Hover latency p95 | 0.0027 ms |
| First plot | 0.292 s |
| Workspace restore | 0.403 s |
| Open-window impact | 0.480 s |
| Memory RSS | 0.694 GB |

## 5. Manual UI Smoke

```powershell
.\prototype\.venv\Scripts\python -m mflog_proto.app
```

Check that:

- The prototype opens.
- The left analysis list can add windows.
- The right properties panel follows the selected analysis window and shows only
  that window's relevant settings. With no analysis-specific settings selected,
  the workspace page can tune the left analysis panel: show/hide search,
  show/hide the add button, switch default/A-Z ordering, choose compact or
  comfortable density, and adjust the panel width. Property pages use visible
  grouped rows, high-contrast labels, and readable checkboxes/inputs in both
  enabled and disabled states.
- With no CSV session, the bottom playback dock is disabled and shows the upload
  guidance.
- `File > Open CSV` loads a root sample CSV and the dock shows filename, row
  count, total length, current time, current row, estimated sample period, and
  event count.
- CSV malformed-row diagnostics appear as warnings without blocking playback.
- `File > Save Project` and `File > Open Project` round-trip the CSV path,
  playback time, tab order, and open analysis windows through `.mflogproj`.
- The left analysis panel groups windows into Visualization, Analysis, Reports,
  and Documents while preserving search, add, sort, density, and width controls.
- The central workspace command bar is reduced to window-management tools such
  as `Tile`; analysis presets are not duplicated as layout buttons.
- Clicking a top preset tab opens a suitable default analysis window set for
  that domain, such as GPS / LapTime opening GPS Map, Time-Series Graph, and
  Segment Analysis, without duplicating already-open windows. The same analysis
  mode also applies domain-default time-series channels and focuses the matching
  right properties page.
- `Event Review` opens from the Analysis group, seeks playback to the selected
  event, supports unreviewed/confirmed/ignored states, stores notes, and
  restores review data from `.mflogproj`.
- `Vehicle Dynamics` opens from the Analysis group and summarizes peak lateral
  G, peak longitudinal G, peak combined G, G-limit utilization/exceedance, max
  yaw rate, and steering-aware yaw response/handling tendency when steering
  data is available.
- `Segment Analysis` can create named time ranges from the current playback
  time and displays available sensor statistics without failing on missing
  channels.
- `Export Report` writes an HTML report with session summary, selected
  channels, event review notes, and segment summaries.
- The playback dock keeps sensor cards in a horizontal scroll area so narrow
  windows do not overlap controls.
- Save/open/export failures are logged under the local app-data log directory
  and shown as warnings without blocking the active session.
- Play/pause, home, end, previous/next event, speed selection, timeline slider,
  arrow-key seek, and Space play/pause work.
- Moving the timeline updates the time-series cursor line, GPS current point,
  G-G current point, sensor cards, and event highlight to the same playback
  time.
- Maximized analysis windows keep local minimize/restore/close controls visible
  inside the central workspace.
- `Settings` / right properties controls can toggle the GPS real-map background
  layer. When network/cache access is available, a high-resolution
  OpenStreetMap tile mosaic is drawn behind the full route with GPS points
  aligned to latitude/longitude; if tiles are unavailable, playback, route, and
  current point remain usable. The same panel can choose visible time-series
  channels, adjust time-series line color and thickness, plus the G-G
  limit-circle radius, for existing and newly opened windows.
- GPS map draws all loaded CSV route plots faintly in the background, highlights
  the currently playing CSV route, and shows a hover marker/label for the nearest
  route point under the mouse.
- GPS routes ignore invalid `(0, 0)` and out-of-range coordinate samples instead
  of drawing a line from the null island origin to the real track.
- G-G keeps the 1 G limit circle visible after CSV upload and uses corrected
  ADXL345 acceleration for `ax_g` / `ay_g`.
- Switching tabs preserves the loaded CSV session and playback position.
- Time-series, GPS, and G-G plots show hover labels/tooltips with the nearest
  sample's time and plot-specific values; time-series graph click seeks to that
  time. Time-series axes, legend, and playback cursor use high-contrast dark UI
  chrome. Analysis-window status labels remain readable against the dark window
  background.
- Autosave warnings do not block the current CSV session or playback controls.
- `3D Vehicle Model` loads the root `car.glb` fixture, parses the renderable
  mesh vertices/triangles, shows the actual GLB mesh in the viewport, and labels
  the view as qualitative visualization. During playback, the model tilts from
  the current corrected `ax`/`ay` acceleration, integrates yaw from `yaw rate`,
  shows the roll/pitch/yaw attitude text, and draws XYZ axes plus
  Roll/Pitch/Yaw arrows in the viewport. The right properties panel can load a
  different GLB model and applies it to open and newly created 3D vehicle
  windows. The selected GLB path is preserved in `.mflogproj` save/open flows.

## 6. Windows EXE Build Smoke

```powershell
cd .\prototype
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

Expected output:

```text
prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe
```

Optional handoff archive:

```powershell
Compress-Archive -Path .\dist\MF-LOG-ANALYZER-v2 -DestinationPath .\dist\MF-LOG-ANALYZER-v2.zip -Force
```

Launch the exe and check that the main window opens with a white-background,
blue MuHanZilJu logo as the program icon, `3D Vehicle Model` can load the
bundled `car.glb`, and `Documents` lists the bundled storyboard PDF.
