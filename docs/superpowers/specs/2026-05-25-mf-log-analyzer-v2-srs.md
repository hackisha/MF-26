# MF-LOG-ANALYZER v2 Software Requirements Specification

Date: 2026-05-25
Status: Draft for user review
Project: MF-LOG-ANALYZER v2
Target users: Formula Student / student race-car team members, including non-developer users

## 1. Purpose

MF-LOG-ANALYZER v2 shall be a high-performance Windows desktop application for analyzing CSV datalogs from the MF race car.

The application shall help users load a run log, verify data quality, inspect vehicle behavior, compare sensor relationships, tune DBW/ETC control behavior, review cooling and electrical reliability, analyze GPS/lap/segment performance, and generate HTML/PDF reports.

The application shall be designed as a full-featured final product specification. All requirements in this document are mandatory requirements. This document shall not use priority labels such as Must, Should, Could, or nice-to-have. Implementation order shall be handled in a separate implementation plan and shall not remove or weaken any requirement in this SRS.

## 2. Product Scope

The application shall support the following major workflows:

1. Open a CSV log.
2. Select or create a vehicle profile.
3. Map CSV columns to standard channels.
4. Apply calibration, correction, unit conversion, and derived-channel formulas.
5. Run log health checks.
6. Create and arrange analysis windows in a workspace.
7. Replay the log using a shared playback timeline.
8. Synchronize playback and hover cursors across visible analysis windows.
9. Analyze time-series data, GPS/lap data, vehicle behavior, suspension movement, DBW/ETC control response, cooling efficiency, electrical voltage behavior, and general data relationships.
10. Link sensor datasheets, wiring diagrams, ECU pin maps, calibration documents, and test notes to the project.
11. Save and reload projects with workspace layouts, presets, settings, linked documents, metadata, annotations, and CSV references or embedded CSV data.
12. Export reports, processed data, tables, summaries, images, and project packages.

## 3. Performance Requirements

The application shall treat performance as a primary product requirement.

The application shall support logs up to 300,000 rows and 100-200 sensor columns as the standard target workload.

The application shall use data structures and rendering strategies that do not prevent later support for logs larger than 1,000,000 rows.

The application shall keep the UI responsive while loading, parsing, mapping, calibrating, deriving, health-checking, caching, and rendering logs.

The application shall provide benchmark tools for measuring:

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

The application shall provide a benchmark report export.

## 4. Technology Selection Requirements

The application shall use a technology stack selected through a performance prototype before full implementation.

The initial candidate stack shall include:

- Python
- PySide6 / Qt
- pyqtgraph
- numpy
- polars
- C/C++ extension modules where measured bottlenecks require native acceleration

The technology selection prototype shall verify:

- loading a 300,000-row, 100-200-channel CSV
- rendering at least 10 time-series channels
- moving a playback cursor smoothly during playback
- synchronizing playback and hover indicators across multiple analysis windows
- preserving responsive UI behavior while multiple windows are open
- saving and restoring project/workspace state

The application shall not use C/C++ merely because native code is available. Native modules shall be introduced only behind clear interfaces for measured bottlenecks such as parsing, downsampling, filtering, interpolation, step-response calculation, or large-array processing.

## 5. Data Model Requirements

The application shall separate raw CSV columns from standard analysis channels.

The application shall store and process data using a column-oriented internal representation.

The application shall preserve raw CSV values or enough raw-source information to trace each standard channel back to its source column.

The application shall support:

- raw channels
- calibrated channels
- unit-converted channels
- derived channels
- analysis-result channels
- event windows
- lap windows
- segment windows
- annotations
- metadata

The application shall ensure that analysis windows refer to standard channel IDs rather than hardcoded CSV column names.

## 6. CSV Load Requirements

The application shall load CSV files through the File menu and project restore flows.

The application shall show progress while loading a CSV.

The load progress UI shall show:

- current stage
- progress bar
- processed row count
- total row count when available
- elapsed time
- estimated remaining time when available
- cancel control

The load stages shall include:

1. file selection
2. file reading
3. CSV structure detection
4. column mapping
5. calibration
6. derived-channel calculation
7. log health check
8. event detection
9. graph-cache/downsample preparation
10. workspace display

The application shall handle:

- blank rows
- malformed rows
- inconsistent field counts
- invalid numeric values
- duplicate column names
- missing required columns
- timestamp gaps
- duplicate timestamps
- backward timestamps
- encoding problems

The application shall report the failed stage and a useful recovery message when CSV load fails.

## 7. Vehicle Profile Requirements

The application shall use vehicle profiles to avoid hardcoded sensor behavior.

Each vehicle profile shall contain:

- profile ID
- display name
- revision or last-modified timestamp
- standard channel definitions
- CSV column aliases
- calibration rules
- unit conversion rules
- valid ranges
- warning thresholds
- critical thresholds
- derived-channel definitions
- event rules
- graph presets
- workspace presets
- report configuration
- document links

The application shall provide default profiles for known 2025 and 2026 vehicle data.

The application shall allow users to create, duplicate, rename, import, export, edit, and restore vehicle profiles.

The application shall record the active profile name and revision in exported reports.

## 8. Standard Channel Requirements

The application shall define standard channel groups:

- Time / Index
- GPS
- Engine
- Cooling / Oil
- Fuel
- Electrical
- Driver Input
- DBW / ETC
- IMU / Vehicle Dynamics
- Suspension
- Aero / Pitot
- Diagnostics / Flags
- User Defined

Each channel shall contain:

- channel ID
- localized display name
- source column list
- raw unit
- canonical unit
- display unit
- group
- scale
- offset
- invert flag
- calibration expression
- valid physical range
- warning threshold
- critical threshold
- default color
- default visibility
- description
- linked documents

The application shall support user-defined channels.

The application shall support multilingual display names while preserving stable channel IDs.

## 9. Known Channel Mapping Requirements

The application shall treat 2025 `OilTemp_C` as `EOT_IN`.

The application shall support both `OilTemp_C` and `EOT_IN` as possible source aliases for the `EOT_IN` standard channel.

The application shall preserve raw `ax_g`, `ay_g`, and `az_g` values.

The application shall provide corrected ADXL345 acceleration channels:

```text
AX_CORRECTED_G = ax_g / 8
AY_CORRECTED_G = ay_g / 8
AZ_CORRECTED_G = az_g / 8
```

The application shall clearly state in analysis views and reports when corrected ADXL345 channels are used.

The application shall support 2026 sensor additions:

- `Susp_FL_mm`
- `Susp_FR_mm`
- `Susp_RL_mm`
- `Susp_RR_mm`
- `Pitot_dP_Pa`
- `Pitot_AirSpeed_KPH`
- `SteeringAngle_deg`

The application shall support DBW/ETC channels including:

- accelerator pedal position 1/2
- throttle position sensor 1/2
- DBW target position
- DBW actual position
- DBW tracking error
- PID P term
- PID I term
- PID D term
- actuator control output
- motor PWM duty
- motor current
- DBW mode
- DBW fault flags
- rate limit active flag
- limp mode flag
- control loop timestamp or sample time

The application shall support Pingel or electronic solenoid shifter event channels when present.

## 10. Column Mapping Requirements

The application shall automatically map CSV columns to standard channels.

The automatic mapping shall consider:

- exact name match
- profile aliases
- case differences
- whitespace differences
- underscore differences
- unit suffix differences
- similar names
- previous mappings from project/profile history

The application shall provide a column mapping review screen.

The column mapping review screen shall show:

- standard channel
- matched CSV column
- mapping confidence
- unit
- calibration
- sample values
- channel status
- required-channel status
- group filter
- search
- manual dropdown selection

Each channel mapping shall show one of these states:

- Matched
- Auto-matched
- Needs review
- Missing
- Ignored
- Derived

The application shall allow users to:

- choose a source CSV column manually
- add an alias
- remove a mapping
- ignore a channel
- create a user-defined channel
- edit calibration
- edit unit conversion
- preview before/after sample values
- save changes to the profile
- apply changes only to the current CSV session

The application shall warn when required channels are missing, units are suspicious, value ranges are abnormal, or mapping confidence is low.

## 11. Unit System Requirements

The application shall distinguish raw units, canonical units, and display units.

The application shall support unit conversion for:

- speed: km/h, m/s, mph
- temperature: degC, degF, K
- pressure: bar, kPa, Pa, psi
- length: mm, m, inch
- acceleration: g, m/s^2
- angle: deg, rad
- angular rate: deg/s, rad/s
- time: s, ms
- voltage/current: V, A, mA

The application shall allow users to set display units per channel, per profile, per graph axis, and per report.

The application shall warn when a derived-channel formula combines incompatible units.

The application shall preserve raw CSV units and display selected output units in reports.

## 12. Derived Channel Requirements

The application shall support derived channels.

The application shall support:

- scale/offset/invert calibration
- unit conversion
- formula-based channels
- advanced analysis function results

Formula-based derived channels shall allow expressions such as:

```text
EOT_DELTA = EOT_OUT - EOT_IN
DBW_ERROR = DBW_TARGET_PERCENT - DBW_ACTUAL_PERCENT
FRONT_SUSP_AVG = (SUSP_FL_MM + SUSP_FR_MM) / 2
REAR_SUSP_AVG = (SUSP_RL_MM + SUSP_RR_MM) / 2
GPS_VSS_DIFF = GPS_SPEED_KPH - VSS_KMH
```

Each derived channel shall define:

- channel ID
- display name
- formula
- input channels
- unit
- group
- color
- valid range
- failure behavior
- report inclusion flag

The application shall provide advanced analysis functions including:

- step response
- rise time
- settling time
- overshoot
- steady-state error
- oscillation detection
- signal smoothing
- moving average
- low-pass filter
- derivative
- resampling
- lap segmentation
- event-window extraction

The application shall compute shared derived results in the data layer and reuse them across analysis windows and reports.

## 13. Log Health Check Requirements

The application shall run Log Health Check automatically after CSV load.

The application shall provide whole-log and per-analysis reliability status.

The per-analysis reliability statuses shall include:

- Time-Series reliability
- GPS / LapTime reliability
- G-G Diagram reliability
- Vehicle Behavior reliability
- Suspension reliability
- DBW / ETC reliability
- Cooling Efficiency reliability
- Electrical / Voltage reliability
- Report reliability

The Log Health Check shall inspect:

- missing columns
- empty values
- numeric conversion failures
- timestamp missing values
- timestamp backward movement
- timestamp duplicates
- irregular sample interval
- malformed CSV rows
- stuck sensors
- out-of-range values
- physically implausible values
- sudden jumps
- excessive noise
- long dropouts
- suspicious units
- calibration application status
- ADXL345 correction status

The GPS health check shall inspect:

- missing coordinates
- GPS jumps
- low satellite count
- GPS speed vs VSS mismatch
- heading discontinuity
- stationary coordinates
- low lap-segmentation reliability

The DBW/ETC health check shall inspect:

- missing target/actual channels
- excessive tracking error
- sensor 1/2 mismatch
- saturated control output
- fault flags
- voltage dip correlated with response degradation

The suspension health check shall inspect:

- missing four-corner stroke channels
- stuck corner sensors
- suspected inversion
- left/right imbalance
- front/rear imbalance
- sensor dropout

The electrical health check shall inspect:

- low battery voltage
- sudden voltage dip
- voltage dip correlated with shift/fan/pump/DBW output
- slow voltage recovery

The application shall expose Log Health Check through `Tools > Log Health Check`.

The application shall show relevant reliability badges in analysis windows.

The application shall include major health warnings in reports.

## 14. Project File Requirements

The application shall support project files with an application-specific extension such as `.mflogproj`.

The project shall store:

- project name
- linked or embedded CSV source
- selected vehicle profile
- sensor mapping
- calibration settings
- unit settings
- derived-channel definitions
- event rules
- workspace presets
- active preset tab
- window layouts
- window settings
- graph settings
- color settings
- current playback time
- manual segments/laps
- annotations
- metadata
- linked or embedded documents
- report settings
- online map setting

The application shall support two CSV storage modes:

- path reference
- embedded CSV or compressed CSV package

The default project save mode shall use path reference.

The application shall allow users to include CSV data when saving or packaging a project.

When a project references a CSV path that no longer exists, the application shall ask the user to locate the CSV file.

The application shall restore the project by loading the profile, mapping, CSV, derived channels, health checks, event detection, workspace layout, preset tab order, playback time, annotations, and report settings.

## 15. Document Library Requirements

The application shall provide a `Documents` group in the left sidebar.

The application shall allow projects to link or embed:

- sensor datasheet PDFs
- wiring diagram PDFs
- schematic PDFs
- ECU pin maps
- system diagrams
- calibration records
- vehicle setup documents
- test notes
- images
- general document files

The application shall support two document storage modes:

- path reference
- embedded project package content

The default document storage mode shall use path reference.

The application shall allow document inclusion when packaging or saving a project.

Documents shall be linkable to:

- sensor channels
- vehicle profiles
- analysis presets
- projects
- event rules
- wiring/pin entries

The application shall open documents in workspace document viewer windows.

The PDF viewer shall support:

- page navigation
- zoom in/out
- fit page
- text search
- bookmarks
- recent page restore
- multiple open document windows
- project/preset layout persistence

## 16. Application Shell Requirements

The application shall provide a Windows desktop interface.

The application shall include:

- top menu bar
- preset tab bar
- left sidebar
- central workspace
- right properties panel
- left mini playback controls
- bottom global timeline/status bar

The application shall support Korean and English UI languages.

The default UI language shall be Korean.

The application shall allow users to change language in Settings.

The application shall preserve standard channel IDs, CSV source column names, and formula identifiers independent of UI language.

## 17. Top Menu Requirements

### 17.1 File Menu

The File menu shall contain:

- Open CSV
- Open Recent CSV
- Open Project
- Open Recent Project
- Save Project
- Save Project As
- Package Project
- Project Info
- Import Profile
- Export Profile
- Export Report
- Export Processed CSV
- Capture Workspace Snapshot
- Exit

The application shall warn before closing, loading another file, or exiting when unsaved changes exist.

The application shall support auto-save, crash recovery, and last-session restore.

### 17.2 Edit Menu

The Edit menu shall be context-sensitive.

The Edit menu shall provide common commands:

- Undo
- Redo
- Copy
- Delete
- Rename
- Duplicate
- Select All
- Clear Selection

When a workspace window is selected, the Edit menu shall support:

- rename window
- duplicate window
- close window
- reset window layout
- bring to front
- send to back
- lock window position

When a graph is selected, the Edit menu shall support:

- copy graph image
- copy current values
- copy selected range
- clear zoom
- reset axis
- add selected range as segment
- toggle selected channel
- edit graph settings

When a segment/lap is selected, the Edit menu shall support:

- rename segment
- delete segment
- duplicate segment
- export segment data
- include/exclude from report
- change segment color

When a preset tab is selected, the Edit menu shall support:

- rename preset
- duplicate preset
- delete preset
- reset preset
- save current workspace to preset
- move preset left/right

When a channel is selected, the Edit menu shall support:

- rename display name
- change color
- hide channel
- edit calibration
- edit threshold
- add to current graph

### 17.3 Tools Menu

The Tools menu shall contain current-log analysis and processing tools:

- Log Health Check
- Column Mapping
- Sensor Calibration
- Derived Channel Editor
- Event Rule Editor
- Lap / Segment Tool
- DBW / ETC Response Analysis
- Suspension Analysis
- Cooling Efficiency Analysis
- Electrical Event Analysis
- Filtering / Resampling
- Export Processed CSV
- Capture Workspace Snapshot

Tools that require long processing shall show progress and cancellation controls.

Tools shall not modify the original CSV by default.

### 17.4 Settings Menu

The Settings menu shall open settings sections for:

- General
- Vehicle Profiles
- Channel Mapping
- Calibration
- Derived Channels
- Event Rules
- Workspace Presets
- Display
- Report
- Language
- Units
- Keyboard Shortcuts
- Performance Options
- Online Map
- Advanced JSON/YAML editor

### 17.5 Help Menu

The Help menu shall contain:

- User Guide
- Sensor Naming Guide
- Calibration Guide
- About
- Check for Updates

Analysis views shall also include short in-place guidance where misinterpretation is likely.

## 18. Preset Tab Requirements

The application shall provide default workspace preset tabs:

- Vehicle Behavior
- GPS / LapTime
- Cooling Efficiency
- Engine Safety
- DBW / ETC
- Electrical / Voltage
- Suspension
- Data Analysis
- Documents
- User Presets

The application shall allow users to:

- add preset tabs
- rename preset tabs
- delete preset tabs
- duplicate preset tabs
- reset default preset tabs
- drag preset tabs to reorder them
- save current workspace state into a preset tab

Each preset tab shall store:

- open window list
- window type
- window position
- window size
- z-order
- minimized/maximized state
- window title
- selected sensors
- graph colors
- axis ranges
- filters
- display mode
- online map state
- active segment/lap
- window-specific options

Playback time shall be project-wide rather than preset-specific.

Preset tab order shall be saved in the project.

## 19. Left Sidebar Requirements

The left sidebar shall act as an analysis add palette and project reference library.

The left sidebar shall include a search input at the top.

The search input shall filter visible sidebar groups and registered entries.

The search shall match:

- group names
- registered analysis entries
- graph presets
- sensor channels
- document names
- user presets

The search shall be case-insensitive and shall support Korean and English display names.

The search shall expand matching groups and hide non-matching groups or entries.

The search shall show a no-match state when nothing matches.

The left sidebar shall contain these groups:

- Vehicle Behavior
- GPS / LapTime
- Cooling Efficiency
- Engine Safety
- DBW / ETC
- Electrical / Voltage
- Suspension
- Data Analysis
- Documents
- User Presets

Each group shall have a plus button.

Clicking a group plus button shall open an add-dropdown for that group.

The user shall create a workspace window by double-clicking or dragging an item from the add-dropdown into the central workspace.

The user shall not need to double-click a main sidebar group to create a window.

The add-dropdown shall support:

- single-click selection or preview
- double-click window creation at a default position
- drag-and-drop window creation at a chosen workspace position
- explicit configure control
- context menu

Configuration shall be opened through a gear button, `Configure`, or context menu rather than hidden double-click behavior.

Dragging a channel into an existing graph window shall add that channel to the graph when compatible.

Dragging a document entry into the workspace shall open a document viewer window.

## 20. Left Sidebar Group Contents

The Vehicle Behavior add-dropdown shall provide:

- G-G Diagram
- 3D Vehicle Attitude
- Suspension Load Transfer View
- Steering vs Lateral G
- Roll / Pitch Trend

The GPS / LapTime add-dropdown shall provide:

- GPS Map
- Lap Time Table
- Segment Analysis
- Speed Trace
- Start / Finish Line Tool

The Cooling Efficiency add-dropdown shall provide:

- EOT IN / OUT Overlay
- Cooling Delta Graph
- Temperature Rise / Fall View
- Cooling Condition Compare

The Engine Safety add-dropdown shall provide:

- RPM / Oil Pressure
- Fuel Pressure
- Lambda / EGT
- MAP / TPS
- Critical Event View

The DBW / ETC add-dropdown shall provide:

- Target vs Actual
- Tracking Error
- Step Response Analysis
- PID Term Viewer
- Condition Response Compare

The Electrical / Voltage add-dropdown shall provide:

- Battery Voltage
- Voltage Drop Events
- Pingel Shift Voltage Dip
- Output Flags
- Device Activity Compare

The Suspension add-dropdown shall provide:

- 4-Corner Stroke Graph
- Suspension Load Transfer View
- Roll / Pitch Trend
- Bump / Rebound Balance

The Data Analysis add-dropdown shall provide:

- Channel Statistics
- Histogram / Distribution
- XY Scatter Plot
- 3D Surface / Map Viewer
- Correlation Matrix
- Lag / Delay Analysis
- Segment Compare
- Outlier Finder
- Signal Processing

The Documents add-dropdown shall provide:

- Add PDF Viewer
- Add Datasheet
- Add Wiring Diagram
- Add ECU Pin Map
- Add Folder
- Link External File

The User Presets add-dropdown shall provide:

- Saved Workspace Preset
- Saved Graph Preset
- Saved Report Preset
- Create Workspace Preset
- Duplicate Current Preset
- Save Current Layout as Preset

## 21. Central Workspace Requirements

The central workspace shall support floating analysis windows by default.

The central workspace shall support docking and snapping.

Workspace windows shall support:

- move
- resize
- minimize
- maximize
- close
- duplicate
- rename
- always-on-top flag
- bring to front
- send to back
- lock position
- snap to edge
- snap beside another window
- dock when requested
- group with other windows
- save/restore layout

The workspace shall allow overlapping windows.

The workspace shall preserve window layout in project files and preset tabs.

## 22. Right Properties Panel Requirements

The application shall provide a right properties panel.

The right properties panel shall show settings for the selected workspace window, graph trace, sensor channel, segment/lap, document, or project.

The properties panel shall support:

- collapse/expand
- width resize
- search
- basic settings section
- advanced settings section
- immediate preview where safe
- undo/redo integration

For analysis windows, the properties panel shall support:

- window title
- window type
- displayed sensors
- graph mode
- axis range
- colors
- line widths
- track configuration
- event visibility
- playback cursor visibility
- hover cursor visibility
- report inclusion
- preset save state

For traces/channels, the properties panel shall support:

- display name
- color
- line style
- line width
- unit
- axis selection
- visibility
- valid range
- warning/critical threshold
- calibration summary

For segment/lap selections, the properties panel shall support:

- name
- start time
- end time
- color
- report inclusion
- notes

## 23. Playback and Timeline Requirements

The application shall provide left mini playback controls and a bottom global timeline.

The left mini playback controls shall provide:

- play/pause
- stop
- previous sample
- next sample
- current time
- current sample index
- playback speed

The bottom global timeline shall provide:

- full log time range
- playback cursor
- event markers
- lap markers
- segment markers
- selection range
- zoomable timeline
- drag-to-seek
- start/end time labels
- current lap/segment label
- hover time indicator

The playback state shall be project-wide.

All analysis windows shall follow the same playback time.

The playback cursor shall move during playback.

Changing time from the mini controls, global timeline, or any seek operation shall update all relevant windows.

Hovering a graph shall not change playback time.

## 24. Cursor Synchronization Requirements

The application shall provide two synchronized cursor concepts:

- Playback Cursor
- Hover Cursor

The Playback Cursor shall be shared across the whole project.

The Playback Cursor shall be stored in the project.

The Playback Cursor shall appear as:

- vertical solid line in time-series graphs
- current point marker in G-G diagrams
- vehicle/arrow marker in GPS maps
- current attitude state in 3D vehicle model
- highlighted row/value in tables
- highlighted target/actual/error values in DBW analysis

The Hover Cursor shall be shared across the currently visible workspace only.

The Hover Cursor shall not be stored in the project.

The Hover Cursor shall disappear when the pointer leaves the relevant analysis area or when the active preset tab changes.

The Hover Cursor shall appear as:

- vertical dashed line in time-series graphs
- hover point marker in G-G diagrams
- hover marker in GPS maps
- temporary row/value highlight in tables

The Playback Cursor and Hover Cursor shall use distinct colors, line styles, marker styles, and labels.

The default Playback Cursor style shall use a readable amber/orange solid style.

The default Hover Cursor style shall use a readable blue dashed style.

## 25. Tooltip Requirements

The application shall show readable hover tooltips on graphs and map views.

Tooltips shall include:

- time
- sample index
- sensor name
- sensor value
- unit
- standard channel ID
- source column when useful
- values for all visible traces at the hovered time when a graph overlays multiple channels

Tooltips shall not be clipped by graph boundaries.

Tooltips shall have readable font size.

Tooltips shall wrap long sensor names.

Tooltips shall align values and units in a readable layout.

Tooltips shall reposition automatically when near window edges.

Tooltips shall work in dark and light themes.

Tooltips shall not obscure the cursor point unnecessarily.

## 26. Time-Series Graph Requirements

The application shall support time-series graph windows.

Time-series graph windows shall support:

- overlay mode
- track mode
- normalized mode
- sensor on/off selection
- channel search
- group filter
- color editing
- line width editing
- axis range editing
- automatic axis range
- manual axis range
- shared axis for matching units
- separate axes for different units
- zoom
- pan
- selected range
- save selected range as segment
- Playback Cursor
- Hover Cursor
- hover tooltip
- event markers
- lap/segment background highlighting
- graph preset saving

Track mode shall support:

- add track
- remove track
- rename track
- resize track height
- drag sensors between tracks
- reorder tracks
- per-track Y-axis settings
- per-track event visibility

Overlay mode shall support:

- multiple sensors in one plot area
- automatic grouping by unit
- multi-axis display
- normalized comparison
- readable legend
- non-clipped labels

## 27. Data Analysis Tool Requirements

The application shall provide a `Data Analysis` group in the left sidebar.

The Channel Statistics tool shall show min, max, mean, median, standard deviation, missing rate, valid range violations, and sample count per channel.

The Histogram / Distribution tool shall show value distributions for selected channels.

The XY Scatter Plot tool shall plot one sensor against another and support color by a third channel.

The Correlation Matrix tool shall show sensor-to-sensor correlation heatmaps.

The Lag / Delay Analysis tool shall estimate delay between two signals, including DBW target-to-actual, shift output-to-voltage dip, TPS-to-MAP, and other user-selected pairs.

The Segment Compare tool shall compare selected laps or segments by statistics and plots.

The Outlier Finder shall detect spikes, dropouts, abnormal values, and unusual event windows.

The Signal Processing tool shall provide smoothing, moving average, low-pass filtering, derivative calculation, and resampling.

## 28. 3D Surface / Map Viewer Requirements

The application shall provide a 3D Surface / Map Viewer in the Data Analysis group.

The 3D Surface / Map Viewer shall support log data and lookup table data.

For log data, the viewer shall support:

- X channel selection
- Y channel selection
- Z channel selection
- selectable color channel
- 3D scatter view
- binned surface view
- 2D heatmap projection

For lookup tables, the viewer shall support:

- 2D table import
- X breakpoints
- Y breakpoints
- Z value table
- 3D surface display
- 2D heatmap display
- table-cell value inspection

For log-vs-table comparison, the viewer shall support:

- display of log samples over table regions
- map coverage analysis
- frequently used map area highlighting
- measured-vs-target difference display
- error surface generation

The viewer shall support rotation, zoom, pan, readable hover tooltips, automatic downsampling, binning, and report snapshots.

## 29. GPS / LapTime Requirements

The application shall provide GPS and LapTime analysis.

The GPS map shall show:

- GPS path
- Playback Cursor vehicle marker
- Hover Cursor marker
- speed-based path coloring
- selected-channel path coloring
- event markers
- current lap/segment label
- current speed
- direction arrow

The direction arrow shall use `Heading_deg` when available.

When `Heading_deg` is unavailable, the application shall infer direction from neighboring GPS coordinates.

The application shall support online map tiles and offline coordinate fallback.

The application shall allow users to turn online maps on/off.

The application shall support:

- manual segment creation
- manual lap creation
- start/finish line definition
- automatic lap split by GPS line crossing
- sector lines
- braking-zone extraction
- acceleration-zone extraction
- high-lateral-G zone extraction
- event-based segment generation
- segment/lap rename
- segment/lap delete
- segment/lap color selection

For each lap/segment, the application shall calculate:

- duration
- max speed
- average speed
- min speed
- max RPM
- max corrected lateral G
- max corrected longitudinal G
- max EOT_IN
- max EOT_OUT
- max CLT
- min oil pressure
- min fuel pressure
- max EGT
- average throttle
- full-throttle time
- braking-estimate time
- event count
- DBW tracking-error summary
- GPS confidence score

The application shall support lap-vs-lap and segment-vs-segment comparison.

The application shall include GPS/lap summaries in reports.

## 30. Vehicle Behavior Requirements

The application shall provide vehicle behavior analysis.

The application shall provide a G-G diagram using corrected longitudinal and lateral acceleration channels.

The G-G diagram shall show:

- all relevant samples as a background point cloud
- Playback Cursor point
- Hover Cursor point
- reference limit circle
- event coloring for braking, acceleration, and cornering when configured

The application shall provide a 3D vehicle behavior visualization.

The 3D visualization shall show qualitative roll, pitch, and yaw tendency.

The 3D visualization shall not present IMU-only integration as precise attitude estimation.

The application shall show an in-place warning that the visualization is qualitative unless a validated attitude estimator is added.

## 31. Suspension Requirements

The application shall provide suspension stroke and load-transfer tendency analysis.

The application shall treat four-corner linear sensor values as suspension stroke, not direct tire force.

The application shall show the following channel convention:

- 0 mm is static ride-height reference
- positive value means bump/compression
- negative value means rebound/droop

The application shall allow each suspension channel to be inverted in settings.

The Suspension Load Transfer View shall show 2D top-view and 3D model simultaneously.

The 2D top-view shall show:

- FL/FR/RL/RR bar indicators
- current stroke values
- compression/rebound direction
- max/min reference
- warning thresholds
- Playback Cursor value
- Hover Cursor value

The 3D model shall show:

- roll trend
- pitch trend
- braking dive tendency
- acceleration squat tendency
- left/right load-transfer tendency
- front/rear load-transfer tendency

The application shall calculate:

```text
front_avg = (FL + FR) / 2
rear_avg = (RL + RR) / 2
left_avg = (FL + RL) / 2
right_avg = (FR + RR) / 2
pitch_trend = front_avg - rear_avg
roll_trend = right_avg - left_avg
```

The suspension view shall connect with G-G, steering angle, GPS/lap/segment, throttle, RPM, and brake-pressure channels when available.

The suspension report shall include maximum compression/rebound, maximum roll trend, maximum pitch trend, braking dive, acceleration squat, and cornering load-transfer tendency windows.

## 32. 3D Vehicle Model Requirements

The application shall use a user-provided `car.glb` as the default vehicle model when available.

The application shall provide a fallback simple model when no model file is available.

The application shall allow users to import GLB or OBJ models.

The application shall allow users to adjust:

- model scale
- rotation-axis correction
- reference position
- vehicle forward direction
- brightness/color
- visibility
- 2D-only view
- 3D-only view
- combined 2D/3D view

The application shall warn when a model file is too large, polygon count is too high, or textures are too large.

The application shall pause or reduce 3D rendering when the 3D window is not visible.

The 3D vehicle model shall be described as qualitative behavior visualization rather than validated physical simulation.

## 33. Cooling Efficiency Requirements

The application shall provide Cooling Efficiency analysis.

The cooling analysis shall use:

- EOT_IN
- EOT_OUT
- EOT_DELTA
- CLT_C
- RPM
- VSS_kmh
- GPS_Speed_KPH
- TPS_percent
- MAP_kPa
- fan state when available
- fan duty when available
- pump state/duty when available

The application shall calculate:

- EOT_DELTA
- EOT rise rate
- EOT fall rate
- CLT rise rate
- CLT fall rate
- high-speed cooling recovery rate
- low-speed temperature rise rate
- high-load temperature rise rate
- fan/pump activation response
- cooling recovery time

The application shall compare cooling performance by:

- speed band
- RPM band
- TPS band
- MAP band
- lap/segment
- fan on/off state
- pit/low-speed condition
- high-load continuous window

The application shall automatically identify:

- EOT_IN over-temperature windows
- EOT_OUT over-temperature windows
- CLT over-temperature windows
- high-speed windows where temperature does not decrease
- low-speed rapid temperature rise
- slow recovery after high-load windows
- fan/pump active without expected cooling response
- abnormal EOT_IN/EOT_OUT delta
- stuck or implausible temperature sensors

Cooling reports shall include max temperatures, max/average EOT_DELTA, worst temperature-rise window, slowest cooling-recovery window, lap/segment summaries, overheating events, and fan/pump behavior summaries.

## 34. DBW / ETC Requirements

The application shall provide DBW/ETC control development analysis.

The application shall compare:

- DBW target
- DBW actual
- TPS
- tracking error
- actuator output
- PWM duty
- motor current
- PID P term
- PID I term
- PID D term
- RPM
- MAP
- lambda
- gear
- battery voltage

The application shall detect and analyze step responses.

The application shall calculate:

- rise time
- settling time
- overshoot
- steady-state error
- oscillation/hunting score
- tracking error statistics
- response delay
- output saturation windows

The application shall compare DBW response by:

- battery voltage band
- RPM band
- MAP band
- gear
- target step size
- throttle opening range

The application shall detect:

- sustained target/actual error
- excessive overshoot
- throttle oscillation
- target changed but actual did not follow
- output saturated but position remained insufficient
- sensor 1/2 mismatch
- voltage dip correlated with poor response
- fault flag windows
- limp mode windows
- rate-limit active windows

The application shall provide DBW/ETC response summaries in reports.

The application shall not write or apply control parameters to the ECU.

The application shall show an in-place warning that DBW/ETC analysis provides tuning insight only and does not apply control parameters.

## 35. Electrical / Voltage Requirements

The application shall provide Electrical / Voltage monitoring.

The application shall support:

- Batt_V
- ECU voltage when available
- sensor supply voltage when available
- output flags
- PWM outputs
- fuel pump state
- cooling fan state
- DBW activity
- Pingel/shift solenoid output
- shift up/down commands
- gear
- RPM

The application shall detect:

- low voltage
- sudden voltage dip
- slow voltage recovery
- voltage dip during shift
- low voltage while DBW active
- low voltage while fuel pump active
- low voltage while cooling fan active
- output active without expected response
- shift command without gear change

The Pingel shift voltage analysis shall show:

- shift command time
- solenoid active time
- gear change time
- Batt_V before shift
- minimum Batt_V
- voltage dip magnitude
- dip duration
- recovery time
- RPM before/after shift
- gear before/after shift
- suspected failed or delayed shift
- repeated-shift voltage accumulation behavior

Electrical reports shall include voltage event summaries and correlated device-activity windows.

## 36. Engine Safety Requirements

The application shall provide Engine Safety analysis.

The Engine Safety group shall include:

- RPM / Oil Pressure
- Fuel Pressure
- Lambda / EGT
- MAP / TPS
- Critical Event View

The application shall detect critical and warning events including:

- high RPM with low oil pressure
- low fuel pressure
- high coolant temperature
- high EOT_IN
- high EOT_OUT
- high EGT
- lean/rich lambda
- low battery voltage
- RPM over limit
- high TPS with lambda anomaly
- high EGT with lambda anomaly
- sudden speed drop

The application shall allow users to edit thresholds, durations, and composite event rules in Settings.

## 37. Aero / Pitot Requirements

The application shall support pitot and airspeed analysis.

The application shall compare:

- pitot differential pressure
- pitot airspeed
- GPS speed
- VSS speed
- heading
- selected lap/segment

The application shall detect speed sensor inconsistencies and possible wind-related differences when data allows.

The application shall include pitot/airspeed channels in graph presets and reports when available.

## 38. Annotation / Memo Requirements

The application shall allow users to create annotations.

Annotations shall be attachable to:

- time
- sample
- selected range
- segment
- lap
- event
- GPS location
- graph window

Annotations shall support:

- title
- text
- author
- timestamp
- color/tag
- report inclusion flag
- edit
- delete
- search

Annotations shall appear as markers in graphs and GPS views.

Annotations shall be saved in the project.

## 39. Multi-Log Comparison Requirements

The application shall support comparing multiple logs.

The application shall allow users to load more than one CSV into a project.

The application shall allow users to select a reference log and comparison logs.

The application shall support:

- same-channel overlay across logs
- lap/segment alignment
- time alignment
- distance alignment when distance calculation is available
- delta graph
- lap time comparison
- cooling comparison
- DBW response comparison
- suspension trend comparison
- voltage event comparison
- comparison report generation

## 40. Session Metadata Requirements

The application shall store run and project metadata.

Metadata shall include:

- date
- vehicle
- driver
- location
- course
- weather
- track/surface condition
- tire
- gear ratio
- vehicle setup
- ECU/firmware version
- test purpose
- author
- notes
- related documents

Metadata shall be saved in the project and included in reports.

## 41. Data Export Requirements

The application shall export:

- processed CSV
- lap table CSV
- segment table CSV
- event list CSV
- DBW response summary CSV
- cooling summary CSV
- suspension summary CSV
- voltage event summary CSV
- graph images
- workspace snapshots
- HTML report
- PDF report
- project package

Exports shall preserve units, profile revision, and generation timestamp.

## 42. Report Requirements

The application shall export HTML and PDF reports.

HTML reports shall support detailed analysis review with graph images and interactive content.

PDF reports shall support team meetings and archival records.

Reports shall include configurable sections:

- Summary
- Log Health Check
- Time-Series Presets
- GPS / LapTime
- Cooling Efficiency
- DBW / ETC
- Suspension
- Vehicle Behavior
- Electrical / Voltage
- Engine Safety
- Data Analysis
- Events
- Annotations
- Sensor Configuration
- Documents
- Appendix

Reports shall include:

- project metadata
- source CSV information
- active profile name and revision
- unit settings
- ADXL345 correction note when applied
- health warnings
- selected graphs
- lap/segment tables
- key events
- analysis summaries

Reports shall be creatable for:

- whole run
- current preset
- selected lap
- selected segment
- detected issue windows

The user shall choose report language independently of application language.

## 43. Settings Requirements

The application shall provide settings for non-developer users first and advanced users second.

Settings shall use UI controls such as dropdowns, checkboxes, numeric inputs, color pickers, searchable lists, and previews.

Advanced JSON/YAML editing shall exist but shall be hidden behind an Advanced section.

Settings shall provide:

- General
- Vehicle Profiles
- Channel Mapping
- Calibration
- Derived Channels
- Event Rules
- Workspace Presets
- Display
- Report
- Language
- Units
- Keyboard Shortcuts
- Performance Options
- Online Map
- Advanced

Settings shall validate:

- JSON/YAML syntax
- required fields
- duplicate channel IDs
- unknown formula channels
- unit conflicts
- invalid calibration values
- invalid thresholds

Settings shall provide:

- default restore
- change preview
- before/after sample value preview
- automatic backup
- import/export
- search
- explanatory tooltips
- warnings before risky changes

## 44. Theme and Color Requirements

The application shall support dark and light themes.

The default theme shall be dark.

The dark theme shall use readable charcoal/dark-gray backgrounds rather than pure black.

The light theme shall be readable for reports, screenshots, and document review.

The application shall avoid highly fluorescent colors.

The application shall use color plus line style, marker shape, or labels for meaning.

The application shall provide color-blind-friendly palette options.

The display settings shall allow users to configure:

- graph background
- grid visibility
- sensor colors
- cursor colors
- font size
- tooltip size
- event colors
- warning/critical colors

## 45. Keyboard Shortcut Requirements

The application shall provide default keyboard shortcuts and allow users to edit them.

Default shortcuts shall include:

- Ctrl+O: Open CSV
- Ctrl+Shift+O: Open Project
- Ctrl+S: Save Project
- Ctrl+Shift+S: Save Project As
- Space: Play/Pause
- Left/Right: previous/next sample or small time step
- Shift+Left/Right: larger time step
- Home: log start
- End: log end
- Ctrl+F: search
- Ctrl+R: reset zoom
- Ctrl+C: copy current values
- Delete: delete selected window/segment where safe
- F11: maximize selected window
- Ctrl+Tab: next preset tab
- Ctrl+Shift+Tab: previous preset tab

The application shall warn about shortcut conflicts.

The application shall support shortcut search and default restore.

## 46. Language Requirements

The application shall support Korean and English.

The default language shall be Korean.

Language selection shall affect:

- menus
- buttons
- tabs
- settings
- guidance text
- error messages
- report section titles
- Help content
- tooltips
- Log Health Check messages

Language selection shall not change:

- standard channel IDs
- CSV source column names
- formula internal identifiers
- project internal identifiers

Reports shall support Korean or English generation.

## 47. Help Requirements

The Help menu shall provide:

- User Guide
- Sensor Naming Guide
- Calibration Guide
- About
- Check for Updates

The User Guide shall explain:

- opening CSVs
- saving/loading projects
- using preset tabs
- adding analysis windows
- graph interaction
- Playback Cursor
- Hover Cursor
- report generation

The Sensor Naming Guide shall explain:

- standard channel names
- CSV columns vs standard channels
- EOT_IN / EOT_OUT
- GPS speed vs VSS
- DBW target vs actual
- Suspension FL/FR/RL/RR
- ADXL345 corrected acceleration

The Calibration Guide shall explain:

- scale
- offset
- invert
- unit conversion
- ADXL345 /8 correction

## 48. Safety and Accuracy Requirements

The application shall not represent qualitative estimates as validated physical measurements.

The application shall label suspension stroke analysis as load-transfer tendency rather than direct tire force.

The application shall label IMU/3D behavior visualization as qualitative unless a validated estimator is added.

The application shall label DBW/ETC analysis as tuning insight and shall not write parameters to the ECU.

The application shall include health-check and reliability warnings in relevant views and reports.

The application shall preserve raw data traceability.

## 49. Acceptance Criteria

The SRS shall be considered satisfied when the final application can:

1. Load a 300,000-row, 100-200-channel CSV with progress feedback.
2. Map CSV columns to standard channels with review and correction.
3. Apply calibration, units, ADXL345 correction, and derived-channel formulas.
4. Run Log Health Check with per-analysis reliability.
5. Open workspace windows from left-sidebar group plus-dropdowns by double-click or drag-and-drop.
6. Arrange floating windows and use docking/snapping where needed.
7. Save and restore project files with workspace, presets, settings, metadata, annotations, documents, and CSV reference or embedded CSV.
8. Provide project-wide Playback Cursor and visible-workspace Hover Cursor synchronization.
9. Show readable hover tooltips with sensor names, values, units, sample index, and time.
10. Support time-series overlay and track modes.
11. Support Data Analysis tools including statistics, histograms, XY scatter, 3D surface/map viewer, correlation, lag analysis, segment comparison, outlier detection, and signal processing.
12. Support GPS/lap/segment analysis with clear current vehicle marker.
13. Support cooling efficiency analysis and reports.
14. Support suspension 2D/3D stroke/load-transfer tendency analysis.
15. Support DBW/ETC control development analysis and reports.
16. Support electrical/Pingel voltage-dip analysis.
17. Support document library and PDF viewer.
18. Support annotations, metadata, multi-log comparison, exports, HTML reports, and PDF reports.
19. Support Korean/English UI and report language.
20. Support dark/light themes and readable, non-fluorescent color palettes.

## 50. Implementation Planning Note

This SRS defines the required final behavior. A separate implementation plan shall define build order, milestones, test strategy, and technology-stack validation. The implementation plan shall not remove requirements from this SRS.
