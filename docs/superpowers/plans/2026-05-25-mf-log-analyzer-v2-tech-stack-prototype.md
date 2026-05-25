# MF-LOG-ANALYZER v2 Technology Validation Prototype Plan

> **For agentic workers:** Use this document before starting full product implementation. This prototype is a measured technology-selection gate, not the first slice of the production app.

**Goal:** Prove that Python + PySide6/Qt + pyqtgraph + numpy + polars can smoothly handle 300,000-row, 100-200-sensor CSV logs on Windows.

**Architecture:** Build a disposable but production-shaped prototype with clear seams between CSV loading, column mapping, derived data, graph-cache generation, Qt UI, playback synchronization, workspace persistence, and benchmark export. Keep every measured bottleneck behind an interface so a future native module can replace only that part.

**Tech Stack:** Python 3.12, PySide6/Qt, pyqtgraph, numpy, polars, psutil, pytest, pytest-qt, pyinstrument or cProfile, optional pyinstaller smoke check.

---

## Context From Current Workspace

- The workspace currently contains MATLAB-era analysis files, sample CSV logs, and `car.glb`.
- It is not currently a git repository.
- Installed Python detected locally: Python 3.12.6.
- Available sample CSV logs are much smaller than the target workload, roughly 8,977 to 27,247 data lines and 2.94 MB to 9.05 MB.
- Root-level project assets are part of the prototype input set:
  - `car.glb` for 3D vehicle model loading smoke tests
  - `데이터분석기 콘티.pdf` for shell/workspace layout reference
  - root-level CSV files for realistic channel names and data-quality cases
  - `대회로그.zip` for later package/import workflow checks
- Prototype must therefore use both:
  - existing real logs for channel realism and data-quality cases
  - generated synthetic logs for target-scale performance validation

## External Stack Notes Verified On 2026-05-25

- Qt for Python provides official Python bindings for Qt through PySide6.
- pyqtgraph is a scientific/engineering graphics library built around Qt and numpy; current installation docs list Qt bindings and numpy as core dependencies.
- Polars supports Python installation through `pip install polars` and documents streaming/out-of-core style processing concepts and optional extras.

References:
- https://doc.qt.io/qtforpython-6/index.html
- https://pyqtgraph.readthedocs.io/en/latest/getting_started/installation.html
- https://docs.pola.rs/user-guide/installation/

## Prototype Scope

The prototype shall validate only the technology risks that could invalidate the SRS stack:

1. Load 300,000-row CSV files with 100, 150, and 200 channels.
2. Keep the Qt UI responsive while loading, mapping, deriving, health-checking, caching, and rendering.
3. Render at least 10 time-series channels.
4. Move a playback cursor smoothly during playback.
5. Synchronize playback and hover cursors across multiple windows.
6. Keep multiple analysis windows open without visible stutter.
7. Save and restore project/workspace state.
8. Export benchmark reports.
9. Identify measured bottlenecks and decide whether native acceleration is needed.

The prototype shall not implement every final analysis tool, report format, settings screen, or complete visual design.

## Proposed Pass Gates

These are initial engineering gates for the prototype. They can be tightened after the first benchmark pass.

| Area | Pass Gate |
| --- | --- |
| CSV target size | 300,000 rows x 200 channels |
| CSV load to typed column store | <= 15 s |
| mapping + calibration + basic derived channels | <= 5 s after load |
| health-check subset | <= 5 s for target log |
| graph-cache/downsample prep | <= 5 s for 20 channels |
| first visible time-series plot | <= 1.5 s after data/cache available |
| playback cursor | stable 30 Hz target, no obvious UI hitch |
| hover latency | p95 <= 80 ms |
| UI responsiveness during background work | no main-thread stall over 150 ms |
| memory for 300k x 200 numeric log | <= 2.5 GB resident set |
| workspace restore | <= 2 s after data already loaded |
| multiple windows | 8 time-series windows + 1 G-G window + 1 table window usable |

If a gate fails by less than about 2x, optimize Python/data/rendering first. If it fails by more than about 2x after profiling, evaluate native acceleration or a targeted library replacement for the failing component only.

## Prototype File Structure

Create the prototype separately from production code so it can be deleted or mined later.

```text
prototype/
  pyproject.toml
  README.md
  src/mflog_proto/
    __init__.py
    app.py
    benchmark/
      __init__.py
      metrics.py
      runner.py
      report.py
    data/
      __init__.py
      csv_loader.py
      synthetic_log.py
      column_store.py
      channel_mapping.py
      derived.py
      health.py
      downsample.py
    profiles/
      mf_2025.yaml
      mf_2026.yaml
    ui/
      __init__.py
      main_window.py
      load_progress.py
      playback.py
      workspace.py
      time_series_window.py
      gg_window.py
      table_window.py
    persistence/
      __init__.py
      project_state.py
  tests/
    test_synthetic_log.py
    test_csv_loader.py
    test_channel_mapping.py
    test_derived.py
    test_downsample.py
    test_project_state.py
```

## Work Plan

### Phase P0: Environment Baseline

- Create `prototype/pyproject.toml` with pinned direct dependencies.
- Add `README.md` with setup and benchmark commands.
- Verify the local Python 3.12.6 environment can import PySide6, pyqtgraph, numpy, polars, and psutil.
- Record CPU model, RAM, OS, Python version, package versions, screen refresh rate, and GPU/OpenGL renderer if available.
- Add a `mflog-proto-bench` command that prints environment metadata before any benchmark.

### Phase P1: Synthetic Log Generator

- Generate deterministic CSVs for:
  - 300,000 x 100
  - 300,000 x 150
  - 300,000 x 200
  - optional stress: 1,000,000 x 200
- Include realistic known channels:
  - `Timestamp`
  - `Latitude`
  - `Longitude`
  - `GPS_Speed_KPH`
  - `RPM`
  - `TPS_percent`
  - `MAP_kPa`
  - `OilTemp_C`
  - `EOT_OUT`
  - `CLT_C`
  - `Batt_V`
  - `DBW_Pos_percent`
  - `DBW_Target_percent`
  - `ax_g`
  - `ay_g`
  - `az_g`
  - `Susp_FL_mm`
  - `Susp_FR_mm`
  - `Susp_RL_mm`
  - `Susp_RR_mm`
  - `Pitot_dP_Pa`
  - `Pitot_AirSpeed_KPH`
  - `SteeringAngle_deg`
- Add controlled data-quality defects:
  - blank rows
  - invalid numeric values
  - duplicate timestamps
  - backward timestamps
  - out-of-range values
  - stuck sensor sections
  - noisy sections
  - dropout sections

### Phase P2: CSV Loader And Column Store

- Implement a loader experiment matrix:
  - `polars.read_csv`
  - `polars.scan_csv(...).collect()`
  - selected-column read
  - type inference versus explicit schema
  - float64 versus float32 numeric storage for rendering cache
- Convert loaded data into a column-oriented store abstraction:
  - raw source column names
  - canonical channel IDs
  - numeric arrays for render-critical channels
  - timestamp/index access
  - traceability from standard channel to CSV source
- Measure:
  - load time
  - memory before/after
  - column count
  - row count
  - parse/conversion errors
  - main-thread blocked time

### Phase P3: Mapping, Calibration, Derived Channels

- Implement a small profile format for the prototype using YAML.
- Include at least the 2025 and 2026 known-channel mapping rules from the SRS.
- Prove these mappings:
  - `OilTemp_C` maps to `EOT_IN`
  - `EOT_IN` maps to `EOT_IN`
  - `ax_g`, `ay_g`, `az_g` raw values are preserved
  - `AX_CORRECTED_G = ax_g / 8`
  - `AY_CORRECTED_G = ay_g / 8`
  - `AZ_CORRECTED_G = az_g / 8`
  - `EOT_DELTA = EOT_OUT - EOT_IN`
  - `DBW_ERROR = DBW_TARGET_PERCENT - DBW_ACTUAL_PERCENT`
- Measure mapping, calibration, and derived-channel timing separately.

### Phase P4: Health-Check Subset

- Implement enough health checks to test pipeline shape and performance:
  - missing required columns
  - invalid numeric values
  - timestamp duplicate/backward/gap detection
  - stuck sensor detection
  - out-of-range values
  - suspicious units
  - ADXL345 correction applied/not applied status
  - DBW target/actual missing or excessive error
  - low battery voltage and voltage dips
- Return whole-log and per-analysis reliability badges in a structured result object.
- Measure total health-check time and per-check time.

### Phase P5: Downsampling And Graph Cache

- Implement at least two downsampling strategies:
  - fixed stride
  - min/max bucket downsampling for visual extrema preservation
- Keep the interface open for future LTTB or native acceleration without changing UI callers.
- Cache per-channel render arrays by:
  - channel ID
  - visible range
  - target pixel width
  - display unit
  - filter/downsample strategy
- Measure cache generation time and memory.

### Phase P6: PySide6 UI Shell

- Build a prototype `QMainWindow` with:
  - menu bar
  - preset tab strip
  - left sidebar
  - central MDI/dock workspace
  - right properties panel placeholder
  - bottom global timeline/status bar
  - load progress dialog
- Use `데이터분석기 콘티.pdf` as the first shell-layout reference. The extracted UI concepts to preserve are:
  - top `File / EDIT / Tools / Settings / help` menu region
  - preset tabs for vehicle behavior, GPS/LapTime, cooling efficiency, voltage monitoring, and user presets
  - left search/sidebar area
  - central floating analysis windows
  - right graph-settings area
  - bottom time/sample status area
  - GPS map, G-G, time-series graph, and 3D vehicle-model regions
- Run CSV load and preprocessing in background worker threads.
- Show progress stages matching the SRS:
  - file reading
  - structure detection
  - column mapping
  - calibration
  - derived-channel calculation
  - health check
  - graph cache preparation
  - workspace display
- Prove cancellation during load.

### Phase P7: Time-Series, Playback, Hover Sync

- Render at least 10 channels using pyqtgraph.
- Support 8 visible time-series windows in the workspace.
- Implement a shared playback state object:
  - current time/sample
  - playing/paused state
  - playback speed
  - time range
  - subscribers
- Synchronize:
  - playback cursor across every visible graph
  - hover cursor across every visible graph
  - current values in the status bar/table window
- Measure:
  - cursor update rate
  - hover p95 latency
  - dropped timer ticks
  - event-loop stall duration

### Phase P8: Minimal Analysis Windows

- Add just enough non-time-series windows to validate architecture:
  - G-G diagram using corrected `AX_CORRECTED_G` and `AY_CORRECTED_G`
  - current-values table
  - benchmark summary window
- Add a 3D model loading smoke test using root-level `car.glb`.
- The smoke test only verifies loading, visibility, camera framing, and hidden-window render throttling. It shall not attempt validated vehicle attitude simulation.
- Use reliability badges from the health-check subset.

### Phase P9: Workspace Save/Restore

- Save prototype project state to JSON:
  - CSV path
  - active profile
  - channel mappings
  - derived-channel settings
  - open windows
  - window positions/sizes
  - selected channels
  - playback time
  - preset tab order
- Restore the workspace after data load.
- Measure restore time.

### Phase P10: Benchmark Report Export

- Export benchmark results as:
  - JSON for machine comparison
  - HTML for human review
- Include:
  - environment metadata
  - input file summary
  - all SRS-required timing categories that the prototype covers
  - memory usage
  - open-window impact
  - pass/fail against gates
  - profiling hotspots
  - decision recommendation

## Experiment Matrix

Run these combinations at minimum:

| Experiment | Variables |
| --- | --- |
| CSV loading | eager vs lazy, inferred schema vs explicit schema, all columns vs selected columns |
| numeric storage | float64 column store vs float32 render cache |
| graph rendering | full arrays vs fixed stride vs min/max bucket |
| worker model | QThread worker vs process worker for load/preprocess |
| window count | 1, 4, 8, 12 graph windows |
| cursor rate | 15 Hz, 30 Hz, 60 Hz timer target |
| data scale | real CSV, 300k x 100, 300k x 150, 300k x 200, optional 1M x 200 |

## Decision Rules

Keep the SRS candidate stack when:

- target-scale CSV load and preprocessing pass the proposed gates
- 10-channel rendering and 8-window playback feel smooth at 30 Hz
- UI remains responsive through load and preprocessing
- memory stays under the prototype gate
- project-state restore works without architectural hacks

Introduce native acceleration only when:

- profiling identifies one isolated hotspot
- Python/numpy/polars/pyqtgraph tuning cannot meet the gate
- the native boundary can be kept behind one existing interface

Native candidates, only if measured:

- downsampling
- interpolation/resampling
- digital filtering
- step-response metrics
- large-array event detection
- parser fallback for malformed CSV cases

Reject or revisit the stack when:

- pyqtgraph cannot keep cursor/hover interactions responsive even with downsampling
- Qt worker architecture still blocks the UI under normal workload
- memory usage is consistently above the gate for 300k x 200
- packaging PySide6 + pyqtgraph + 3D/PDF dependencies becomes operationally fragile

## Prototype Deliverables

- Runnable prototype app.
- Synthetic data generator.
- Benchmark CLI.
- Benchmark HTML/JSON reports.
- Profile YAML examples for 2025 and 2026.
- Short stack-decision memo:
  - selected stack
  - measured results
  - failed gates, if any
  - required optimizations
  - native-extension decision
  - production implementation adjustments

## Completion Criteria

The prototype is complete when one of these is true:

1. The candidate stack passes the 300k x 200 gates and the implementation plan can proceed with this architecture.
2. The candidate stack fails with clear measured evidence and the implementation plan is updated to include a targeted stack change.
3. A single bottleneck requires native acceleration and the production plan names the interface and measurement threshold for introducing it.
