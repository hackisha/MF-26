# MF-LOG-ANALYZER v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MF-LOG-ANALYZER v2 as a high-performance Korean-first Windows desktop application for race-car CSV datalog analysis, based on the 2026-05-25 SRS.

**Architecture:** Use a column-oriented data core with stable standard channel IDs, profile-driven mapping/calibration/derived channels, background processing, shared playback/hover state, modular analysis windows, persistent project/workspace state, and benchmark-driven performance gates. UI modules consume standard channels and derived analysis results rather than raw CSV names.

**Tech Stack:** Python 3.12, PySide6/Qt, pyqtgraph, numpy, polars, YAML/JSON project/profile files, pytest, pytest-qt, ruff, mypy or pyright, pyinstaller or Nuitka packaging after validation, optional native extensions only for measured bottlenecks.

---

## Preconditions

- Finish the technology validation prototype first.
- Do not start full implementation until the prototype decision memo confirms the stack or names a targeted stack adjustment.
- Convert this roadmap into smaller execution plans when implementation starts. The SRS is broad enough that each milestone should have its own task-level plan and review cycle.
- Initialize a git repository before production implementation if this folder remains the project root.
- Treat project-root assets as first-class implementation inputs:
  - root-level CSV files are realistic fixtures for mapping, health checks, and report examples
  - `car.glb` is the default 3D vehicle-model fixture
  - `데이터분석기 콘티.pdf` is the first UI shell/workspace layout reference
  - `대회로그.zip` is a fixture candidate for import/package workflows

## Product Architecture

### Core Layers

```text
src/mflog_analyzer/
  app/
    main.py
    application.py
    actions.py
  core/
    channel_id.py
    column_store.py
    csv_loader.py
    data_session.py
    derived_engine.py
    unit_system.py
    event_model.py
    annotation_model.py
    metadata_model.py
  profiles/
    profile_model.py
    profile_repository.py
    default_profiles/
      mf_2025.yaml
      mf_2026.yaml
  mapping/
    matcher.py
    mapping_session.py
    confidence.py
  health/
    health_model.py
    checks_time.py
    checks_signal.py
    checks_gps.py
    checks_dbw.py
    checks_suspension.py
    checks_electrical.py
  processing/
    downsample.py
    filters.py
    resampling.py
    statistics.py
    step_response.py
    lap_segmentation.py
  playback/
    playback_state.py
    cursor_bus.py
  project/
    project_model.py
    project_io.py
    package_io.py
    autosave.py
  reports/
    report_model.py
    html_report.py
    pdf_report.py
    image_export.py
  ui/
    shell/
    widgets/
    dialogs/
    workspace/
    analysis_windows/
    settings/
    i18n/
    themes/
  documents/
    document_model.py
    document_store.py
    pdf_viewer.py
  benchmarks/
    metrics.py
    runner.py
    report.py
```

### Dependency Direction

- `core`, `profiles`, `mapping`, `health`, `processing`, `playback`, `project`, and `reports` shall not import UI modules.
- UI modules may import service interfaces and view models, not raw polars/numpy internals except render-ready arrays.
- Analysis windows shall refer to standard channel IDs, never hardcoded CSV column names.
- Reports shall use the same analysis-result models as UI windows.
- Native acceleration, if added, shall sit behind `processing` interfaces.

## Milestone 0: Repository And Engineering Baseline

- [ ] Initialize git and create `.gitignore`.
- [ ] Create `pyproject.toml` with app, test, lint, and packaging dependencies.
- [ ] Add `src/` package layout and smoke-test entry point.
- [ ] Add `tests/` with pytest configuration.
- [ ] Add ruff formatting/linting.
- [ ] Add type checking configuration.
- [ ] Add `docs/superpowers/plans/` and keep this plan under version control.
- [ ] Add a small CI-friendly command set:
  - `pytest`
  - `ruff check`
  - `ruff format --check`
  - type check command
- [ ] Commit the baseline.

Exit criteria:

- App opens an empty main window.
- Tests/lint/type checks run locally.
- The project can be installed in editable mode.

## Milestone 1: Data Foundation

- [ ] Implement `ColumnStore` with column-oriented access.
- [ ] Implement `CsvLoadRequest`, `CsvLoadProgress`, and cancellable background CSV load.
- [ ] Implement duplicate-column handling.
- [ ] Implement malformed row and invalid numeric value reporting.
- [ ] Implement timestamp normalization and row index fallback.
- [ ] Preserve raw source traceability for every standard channel.
- [ ] Add benchmark hooks for:
  - CSV load time
  - memory usage
  - row count
  - column count
  - conversion-error count
- [ ] Add tests with tiny fixture CSVs for malformed rows, duplicate columns, missing timestamps, duplicate timestamps, and invalid numbers.
- [ ] Add integration fixtures that load the root-level sample CSV files without moving or rewriting them.

Exit criteria:

- Real sample CSVs from this workspace load.
- Synthetic 300k x 200 CSV loads through the same path.
- Load progress can be cancelled.

## Milestone 2: Profiles, Standard Channels, Mapping

- [ ] Define profile schema and validation.
- [ ] Add default 2025 and 2026 profiles.
- [ ] Define standard channel groups from the SRS.
- [ ] Define stable channel IDs independent of UI language.
- [ ] Implement mapping matcher:
  - exact name
  - aliases
  - case-insensitive
  - whitespace-insensitive
  - underscore-insensitive
  - unit suffix tolerant
  - previous mapping history
- [ ] Implement mapping confidence scoring.
- [ ] Implement mapping review model.
- [ ] Add known mappings:
  - `OilTemp_C` as source alias for `EOT_IN`
  - `EOT_IN` as source alias for `EOT_IN`
  - raw `ax_g`, `ay_g`, `az_g`
  - 2026 suspension, pitot, airspeed, steering channels
  - DBW/ETC channel family
- [ ] Add tests for every known mapping rule.

Exit criteria:

- Loading a CSV produces mapping states: Matched, Auto-matched, Needs review, Missing, Ignored, Derived.
- The mapping review data model contains sample values, unit, calibration, status, and confidence.

## Milestone 3: Units, Calibration, Derived Channels

- [ ] Implement unit registry for SRS unit families.
- [ ] Implement scale/offset/invert calibration.
- [ ] Implement formula-based derived channels using a restricted safe expression engine.
- [ ] Implement derived formula validation:
  - unknown input channel
  - unit conflict
  - circular dependency
  - missing input behavior
- [ ] Implement required derived channels:
  - corrected ADXL345 acceleration
  - `EOT_DELTA`
  - `DBW_ERROR`
  - front/rear/left/right suspension averages
  - pitch and roll trend
  - GPS/VSS speed difference
- [ ] Add tests for formula correctness and unit validation.

Exit criteria:

- Derived channels are computed once in the data layer and reused by UI/report consumers.
- ADXL345 correction is traceable and can be surfaced in UI/report notes.

## Milestone 4: Log Health Check And Event Foundation

- [ ] Implement health result model with whole-log and per-analysis reliability statuses.
- [ ] Implement generic checks:
  - missing columns
  - empty values
  - numeric conversion failures
  - timestamp gaps
  - duplicate/backward timestamps
  - malformed rows
  - stuck sensors
  - out-of-range values
  - sudden jumps
  - excessive noise
  - long dropouts
  - suspicious units
  - calibration status
  - ADXL345 correction status
- [ ] Implement GPS checks.
- [ ] Implement DBW/ETC checks.
- [ ] Implement suspension checks.
- [ ] Implement electrical checks.
- [ ] Implement event-window model shared by analyses and reports.
- [ ] Add tests for representative pass/warn/critical cases.

Exit criteria:

- Health check runs automatically after CSV load.
- `Tools > Log Health Check` can re-run it.
- Analysis windows can display reliability badges.

## Milestone 5: Project File, Autosave, Crash Recovery

- [ ] Define `.mflogproj` JSON schema.
- [ ] Support CSV path-reference mode.
- [ ] Support embedded/compressed CSV package mode.
- [ ] Store profile, mapping, calibration, units, derived channels, event rules, workspace presets, active tab, layouts, playback time, annotations, metadata, documents, and report settings.
- [ ] Implement missing referenced CSV recovery flow.
- [ ] Implement save, save as, open project, package project.
- [ ] Implement autosave and crash recovery.
- [ ] Add schema migration versioning from the first release.
- [ ] Add project round-trip tests.

Exit criteria:

- A loaded CSV with mappings and workspace layout can be saved, closed, reopened, and restored.

## Milestone 6: Application Shell And Workspace

- [ ] Build Windows desktop shell:
  - top menu bar
  - preset tab bar
  - left sidebar
  - central workspace
  - right properties panel
  - left mini playback controls
  - bottom timeline/status bar
- [ ] Translate the root-level `데이터분석기 콘티.pdf` into the first concrete shell layout:
  - `File / EDIT / Tools / Settings / help` menu region
  - preset tabs for vehicle behavior, GPS/LapTime, cooling efficiency, voltage monitoring, and user presets
  - left search/sidebar area
  - central floating analysis windows
  - right graph-settings/properties area
  - bottom time/sample status area
- [ ] Implement default preset tabs from the SRS.
- [ ] Implement floating/docking/snapping workspace windows.
- [ ] Implement left-sidebar search and group add palette.
- [ ] Implement double-click and drag-and-drop window creation.
- [ ] Implement context-sensitive Edit menu action routing.
- [ ] Implement unsaved-change warnings.
- [ ] Add UI tests for action wiring and workspace state model.

Exit criteria:

- Users can create, arrange, duplicate, rename, close, and restore analysis windows.
- Preset tab order and workspace layout persist in project files.

## Milestone 7: Playback, Timeline, Cursor Synchronization

- [ ] Implement project-wide playback state.
- [ ] Implement global timeline.
- [ ] Implement play/pause, speed, sample stepping, home/end.
- [ ] Implement playback cursor bus.
- [ ] Implement hover cursor bus scoped to visible workspace.
- [ ] Implement current-value lookup by time/sample.
- [ ] Implement synchronized tooltips with sensor names, values, units, sample index, and time.
- [ ] Add latency instrumentation.
- [ ] Add tests for cursor state and subscriber updates.

Exit criteria:

- Every visible analysis window receives synchronized playback and hover updates.
- Cursor update metrics are reported by benchmark tools.

## Milestone 8: Time-Series Graphs And Data Analysis Tools

- [ ] Implement time-series overlay mode.
- [ ] Implement track/split mode.
- [ ] Implement axis, zoom, pan, selected range, reset, copy image/current values/range.
- [ ] Implement graph settings and per-axis display units.
- [ ] Implement render cache/downsampling.
- [ ] Implement statistics table.
- [ ] Implement histogram.
- [ ] Implement XY scatter.
- [ ] Implement correlation matrix.
- [ ] Implement lag/delay analysis.
- [ ] Implement segment compare.
- [ ] Implement outlier finder.
- [ ] Implement signal processing:
  - smoothing
  - moving average
  - low-pass filter
  - derivative
  - resampling
- [ ] Implement 3D surface/map viewer after 2D graph performance is stable.

Exit criteria:

- Acceptance criteria 8-11 are satisfied for loaded logs.

## Milestone 9: GPS, Lap, Segment Analysis

- [ ] Implement GPS map with online-map toggle and offline fallback.
- [ ] Implement current vehicle marker and hover marker.
- [ ] Implement speed/channel-based path coloring.
- [ ] Implement heading from `Heading_deg` or inferred GPS direction.
- [ ] Implement manual segment/lap creation.
- [ ] Implement start/finish and sector line model.
- [ ] Implement automatic lap split by GPS line crossing.
- [ ] Implement braking/acceleration/high-lateral-G zone extraction.
- [ ] Implement lap/segment statistics from the SRS.
- [ ] Implement lap-vs-lap and segment-vs-segment comparison.

Exit criteria:

- GPS/lap summaries are available for reports.
- GPS reliability warnings appear when data quality is poor.

## Milestone 10: Vehicle Behavior And 3D Model

- [ ] Implement G-G diagram using corrected acceleration.
- [ ] Implement background point cloud, playback point, hover point, limit circle, and event coloring.
- [ ] Implement qualitative 3D behavior visualization.
- [ ] Load root-level `car.glb` as the default development fixture and user-provided `car.glb` when available in a project.
- [ ] Provide fallback simple vehicle model.
- [ ] Implement model import for GLB/OBJ.
- [ ] Implement scale, rotation correction, reference position, forward direction, brightness/color, visibility, 2D-only, 3D-only, and combined modes.
- [ ] Add warnings for qualitative visualization and oversized models.
- [ ] Reduce/pause 3D rendering when hidden.

Exit criteria:

- Vehicle behavior views do not present qualitative estimates as validated physical measurements.

## Milestone 11: Domain Analysis Modules

- [ ] Implement Suspension analysis:
  - four-corner stroke convention
  - inversion settings
  - 2D top-view bars
  - 3D trend view
  - roll/pitch trend calculations
  - report summaries
- [ ] Implement Cooling Efficiency analysis:
  - EOT/CLT rates
  - speed/RPM/TPS/MAP/lap/segment comparisons
  - fan/pump response when available
  - overheating and slow-recovery windows
- [ ] Implement DBW/ETC analysis:
  - target/actual/error overlays
  - step response
  - rise time, settling time, overshoot, steady-state error
  - oscillation/hunting score
  - voltage correlation
  - tuning-insight warning
- [ ] Implement Electrical/Voltage analysis:
  - low voltage
  - dips/recovery
  - shift/Pingel correlation
  - device activity windows
- [ ] Implement Engine Safety analysis.
- [ ] Implement Aero/Pitot analysis.

Exit criteria:

- Acceptance criteria 13-17 are satisfied.

## Milestone 12: Documents, Annotations, Metadata

- [ ] Implement document library model.
- [ ] Support path-reference and embedded project package document modes.
- [ ] Link documents to channels, profiles, presets, projects, event rules, and wiring/pin entries.
- [ ] Implement PDF viewer:
  - page navigation
  - zoom
  - fit page
  - text search
  - bookmarks
  - recent page restore
  - multiple document windows
- [ ] Implement annotations attached to time, sample, range, segment, lap, event, GPS location, and graph window.
- [ ] Implement annotation search and report-inclusion flag.
- [ ] Implement session metadata editor.

Exit criteria:

- Documents, annotations, and metadata are persisted in projects and available to reports.

## Milestone 13: Settings, Language, Theme, Shortcuts

- [ ] Implement Korean and English i18n infrastructure.
- [ ] Set Korean as default UI language.
- [ ] Keep channel IDs, CSV names, formula IDs, and project IDs language-independent.
- [ ] Implement dark/light themes.
- [ ] Implement non-fluorescent default palettes and color-blind-friendly palette option.
- [ ] Implement settings sections from the SRS.
- [ ] Implement advanced JSON/YAML editor behind Advanced section.
- [ ] Validate settings edits:
  - syntax
  - required fields
  - duplicate channel IDs
  - unknown formula channels
  - unit conflicts
  - invalid calibration values
  - invalid thresholds
- [ ] Implement editable keyboard shortcuts and conflict warnings.

Exit criteria:

- UI/report language can be selected independently.
- Settings are safe for non-developer users by default.

## Milestone 14: Export And Reports

- [ ] Export processed CSV.
- [ ] Export lap table CSV.
- [ ] Export segment table CSV.
- [ ] Export event list CSV.
- [ ] Export DBW summary CSV.
- [ ] Export cooling summary CSV.
- [ ] Export suspension summary CSV.
- [ ] Export voltage event summary CSV.
- [ ] Export graph images and workspace snapshots.
- [ ] Implement HTML report.
- [ ] Implement PDF report.
- [ ] Implement report configuration sections.
- [ ] Include profile revision, unit settings, ADXL345 correction note, health warnings, selected graphs, tables, key events, and analysis summaries.

Exit criteria:

- Reports can be generated for whole run, current preset, selected lap, selected segment, and detected issue windows.

## Milestone 15: Multi-Log Comparison

- [ ] Extend project model for multiple logs.
- [ ] Implement reference/comparison log selection.
- [ ] Implement same-channel overlay across logs.
- [ ] Implement time alignment.
- [ ] Implement lap/segment alignment.
- [ ] Implement distance alignment when distance calculation is available.
- [ ] Implement delta graph.
- [ ] Implement comparison outputs for lap time, cooling, DBW, suspension, and voltage events.
- [ ] Implement comparison report generation.

Exit criteria:

- Multiple logs can be loaded, aligned, compared, saved, restored, and reported.

## Milestone 16: Benchmarking, Hardening, Packaging

- [ ] Keep benchmark tools available from the app and CLI.
- [ ] Measure every SRS performance category:
  - CSV load time
  - column mapping time
  - calibration time
  - derived-channel calculation time
  - health-check time
  - event detection time
  - graph cache generation time
  - chart render time
  - playback cursor update rate
  - hover cursor latency
  - memory usage
  - open analysis-window count impact
- [ ] Export benchmark reports.
- [ ] Run 300k x 200 acceptance benchmark.
- [ ] Run optional 1M-row stress benchmark.
- [ ] Profile bottlenecks and optimize.
- [ ] Introduce native modules only when measurement requires it.
- [ ] Package Windows build.
- [ ] Test first-run, update-check placeholder, crash recovery, autosave, and uninstall-safe file locations.

Exit criteria:

- The app satisfies all SRS acceptance criteria at the 300k x 100-200-channel target workload.

## Test Strategy

- Unit tests:
  - mapping
  - units
  - calibration
  - derived formulas
  - health checks
  - event detection
  - project IO
  - report models
- Integration tests:
  - CSV load pipeline
  - profile + mapping + derived + health
  - project save/open
  - report generation
  - multi-log comparison
- UI tests:
  - menu/action wiring
  - mapping review workflows
  - workspace creation/restore
  - playback and cursor sync
  - settings validation
- Performance tests:
  - synthetic 300k x 100/150/200
  - real sample CSVs
  - window-count impact
  - cursor/hover latency
  - memory ceiling
- Manual validation:
  - Korean-first workflow
  - non-developer usability
  - safety/accuracy warnings
  - report readability

## Build Order Rationale

Build data correctness and performance before rich UI. The app is only valuable if channel mapping, derived data, health warnings, playback synchronization, and persistence are reliable. Domain-specific analysis windows should arrive after the shared data/playback/report foundations are solid, so every new module reuses the same tested contracts.

## Risk Register

| Risk | Mitigation |
| --- | --- |
| pyqtgraph stutters with many windows | downsample/cache first, profile, then isolate renderer/native options |
| CSV parsing edge cases multiply | keep raw-source error model and fixture tests from the start |
| SRS scope is too large for one execution pass | split each milestone into separate task-level plans |
| project file migration pain | version schema from first save format |
| unit/formula mistakes create unsafe conclusions | validate units, preserve traceability, display reliability warnings |
| DBW analysis misread as ECU tuning writer | include explicit warning and never implement ECU write path |
| qualitative 3D views look too authoritative | label them as qualitative in UI and reports |
| packaging bloats or breaks | packaging smoke tests start before feature-complete stage |

## First Execution Recommendation

After prototype completion, implement Milestones 0-4 first as the first production slice:

1. repository baseline
2. data foundation
3. profiles and mapping
4. units/calibration/derived channels
5. health-check/event foundation

This creates a testable data engine before investing heavily in UI. The first UI slice should then be Milestones 5-8: project persistence, shell/workspace, playback/cursor sync, and time-series/data-analysis windows.
