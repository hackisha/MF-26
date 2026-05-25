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
The current expected count is `105 passed`.

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
- With no CSV session, the bottom playback dock is disabled and shows the upload
  guidance.
- `File > Open CSV` loads a root sample CSV and the dock shows filename, row
  count, total length, current time, current row, estimated sample period, and
  event count.
- Play/pause, home, previous/next event, speed selection, timeline slider,
  arrow-key seek, and Space play/pause work.
- Moving the timeline updates the time-series cursor line, GPS current point,
  G-G current point, sensor cards, and event highlight to the same playback
  time.
- Switching tabs preserves the loaded CSV session and playback position.
- Graph hover shows sensor name, time, value, and unit tooltip; graph click
  seeks to that time.
- Autosave warnings do not block the current CSV session or playback controls.
- `3D Vehicle Model` loads the root `car.glb` fixture.
