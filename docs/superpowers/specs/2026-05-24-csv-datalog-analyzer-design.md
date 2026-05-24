# MF Log Analyzer Design

Date: 2026-05-24
Status: Draft for user review

## Goal

Build MF Log Analyzer, a Windows desktop app for Formula Student / student race car CSV datalog analysis.

The app should let the team open a CSV log after a run, apply the correct vehicle profile, inspect the vehicle and engine state, understand driver and vehicle behavior, and generate a meeting-ready report within about 5 minutes.

Primary success criteria:

- A useful run report can be produced within 5 minutes after opening a CSV.
- Dangerous engine or vehicle states are surfaced automatically.
- Driver input and vehicle behavior can be understood without needing MATLAB.
- Team-specific sensor mapping, calibration, thresholds, and report choices are configurable instead of hardcoded.

## Product Shape

MF Log Analyzer is a vehicle-profile-based CSV datalog desktop analyzer.

Basic workflow:

1. Select a vehicle profile, such as `2025 Vehicle` or `2026 Vehicle`.
2. Open a CSV log.
3. Apply column mapping, units, calibration, and correction rules from the selected profile.
4. Run log diagnostics and event detection.
5. Inspect the result in dashboard, graph, behavior, map/lap, and report views.
6. Export an HTML/PDF report for team review.

Core app views:

- Summary
- Log Diagnostics
- Time-Series Graph
- Vehicle Behavior
- Map / Lap
- Report
- Settings

Each analysis view should be available as a normal tab and as a pop-out view. Pop-out views share the same analysis session, so selecting a time, segment, lap, or event in one view updates the others.

Shared session state:

- Open CSV
- Selected vehicle profile
- Current timestamp
- Selected segment or lap
- Selected event
- Active filters
- Active overlay preset

## Existing CSV Input

The 2025 log format includes these columns:

```text
Timestamp
Latitude
Longitude
GPS_Speed_KPH
Satellites
Altitude_m
Heading_deg
RPM
TPS_percent
IAT_C
MAP_kPa
PulseWidth_ms
AnalogIn1_V
AnalogIn2_V
AnalogIn3_V
AnalogIn4_V
VSS_kmh
Baro_kPa
OilTemp_C
OilPressure_bar
FuelPressure_bar
CLT_C
EOT_OUT
fuelPumpTemp
IgnAngle_deg
DwellTime_ms
WBO_Lambda
LambdaCorrection_percent
EGT1_C
EGT2_C
Gear
EmuTemp_C
Batt_V
CEL_Error
Flags1
Ethanol_percent
DBW_Pos_percent
DBW_Target_percent
TC_drpm_raw
TC_drpm
TC_TorqueReduction_percent
PitLimit_TorqueReduction_percent
AnalogIn5_V
AnalogIn6_V
OutFlags1
OutFlags2
OutFlags3
OutFlags4
BoostTarget_kPa
PWM1_DC_percent
DSG_Mode
LambdaTarget
PWM2_DC_percent
FuelUsed_L
ax_g
ay_g
az_g
gx_dps
gy_dps
gz_dps
ADU_ax_g
ADU_ay_g
ADU_az_g
```

The 2025 `OilTemp_C` column represents `EOT_IN`. The canonical channel should be treated as engine oil temperature in, with `OilTemp_C` and `EOT_IN` supported as aliases depending on the CSV year.

## 2026 Sensor Additions

Recommended standard columns for the 2026 profile:

```text
Susp_FL_mm
Susp_FR_mm
Susp_RL_mm
Susp_RR_mm
Pitot_dP_Pa
Pitot_AirSpeed_KPH
SteeringAngle_deg
```

Suspension convention:

- `0 mm` is the static ride-height reference.
- Positive value means bump/compression.
- Negative value means rebound/droop.
- Each corner can be inverted in settings if the physical sensor installation direction is opposite.

This matches common motorsport analysis convention where bump/compression is treated as positive and rebound/droop as negative.

Suspension values should be described as suspension stroke or wheel travel. They do not directly measure force, but they can support load-transfer trend analysis.

## Vehicle Profiles And Sensor Channels

Profiles are the main mechanism for avoiding hardcoded behavior.

Each profile contains:

- Profile name
- CSV column mappings and aliases
- Sensor channel definitions
- Unit definitions
- Calibration and correction rules
- Direction inversion rules
- Warning and critical thresholds
- Composite event rules
- Overlay graph presets
- Report template choices

Each sensor channel contains:

- Display name
- Source CSV column
- Unit
- Sensor group
- Calibration expression, such as `value / 8` or `value * scale + offset`
- Optional direction inversion
- Missing-value behavior
- Valid physical range
- Display color
- Default visibility
- Warning/critical thresholds

Sensor groups:

- Engine
- Cooling / Oil
- Fuel
- GPS
- IMU
- Suspension
- Aero
- Driver Input
- Electrical
- Diagnostics

The 2025 profile should ship with mappings for the current CSV columns. The 2026 profile should inherit useful 2025 defaults and add suspension, pitot, and steering channels.

## ADXL345 Correction

The current `ax_g`, `ay_g`, and `az_g` values are believed to have been converted using `0.0312 g/LSB`, which corresponds to ADXL345 +/-16 g fixed 10-bit scaling.

If the sensor was actually configured in full-resolution mode, the correct scale is about `0.0039 g/LSB`, so the logged values are likely about 8x too large.

The app must preserve raw logged channels and create corrected analysis channels:

```text
ax_corrected_g = ax_g / 8
ay_corrected_g = ay_g / 8
az_corrected_g = az_g / 8
```

Default analysis should use corrected values. Reports should clearly state that the ADXL345 correction was applied.

## Log Diagnostics

Log diagnostics answer: "Can we trust this data enough to analyze it?"

Diagnostics should check:

- Missing required columns
- Missing values
- Duplicate or backward timestamps
- Irregular sample intervals
- GPS dropouts
- Low satellite count
- Sudden GPS position jumps
- Large mismatch between `GPS_Speed_KPH` and `VSS_kmh`
- Sensor channels stuck at a constant value
- Physically implausible sensor values
- Battery voltage low enough to reduce sensor confidence
- Uncorrected or suspicious accelerometer values

Diagnostics output should classify the log as usable, usable with warnings, or unreliable for specific analyses. For example, GPS analysis can be marked unreliable while engine analysis remains usable.

## Time-Series Graph And Overlays

The time-series graph is the main detailed analysis view.

Required features:

- Select any sensor channels to display.
- Overlay multiple channels on the same time axis.
- Use shared Y-axis when units match.
- Use separate Y-axes when units differ.
- Provide normalized mode to compare trend shapes across different units.
- Zoom, pan, and select time ranges.
- Display detected events as markers.
- Let users save overlay presets in the profile.

Example overlay presets:

- Cooling: `EOT_IN`, `EOT_OUT`, `CLT_C`
- Engine load and heat: `RPM`, `TPS_percent`, `MAP_kPa`, `EGT1_C`, `EGT2_C`
- Oil stability: `RPM`, `OilPressure_bar`, `EOT_IN`
- Driver input vs response: `SteeringAngle_deg`, `TPS_percent`, braking estimate, `ay_corrected_g`
- Suspension balance: `Susp_FL_mm`, `Susp_FR_mm`, `Susp_RL_mm`, `Susp_RR_mm`

Overlay presets are configurable in Settings and can be included in reports.

## Event Detection

The app should support simple threshold rules and composite rules.

Rule fields:

- Name
- Severity: info, warning, critical
- Condition channel
- Comparison operator
- Threshold
- Minimum duration
- Optional AND/OR composite conditions
- Views where the event appears
- User-facing explanation

Example critical event:

```text
High RPM Oil Pressure Drop
RPM > 6000
OilPressure_bar < 2.5
Duration >= 0.5 s
Severity: critical
```

Initial event categories:

- Oil temperature high
- Oil pressure low
- Fuel pressure low
- Coolant temperature high
- EGT high
- Lambda lean/rich
- Battery voltage low
- RPM over limit
- High RPM plus low oil pressure
- High TPS plus lean lambda
- High EGT plus lambda anomaly
- GPS quality poor
- Strong braking
- Full-throttle acceleration
- High lateral-g cornering
- Sudden speed drop

Default thresholds should be conservative starting points and editable in Settings.

## Vehicle Behavior Analysis

This view focuses on how the car behaves, not only whether sensor values are safe.

Required features:

- G-G diagram using corrected longitudinal/lateral acceleration.
- Time playback marker on the G-G diagram.
- Event coloring for braking, acceleration, and cornering.
- Simple race-car model visualization for roll, pitch, and yaw tendency.
- Clear confidence labels when behavior is inferred from IMU only.

Important accuracy rule:

- IMU angular rates can show roll/pitch/yaw tendency, but pure integration will drift.
- The first version should present this as behavior visualization or trend analysis, not precision attitude estimation.
- When 4-corner suspension stroke is available, roll and pitch trend confidence improves.

2026 suspension-derived behavior analysis:

- Left/right compression difference
- Front/rear compression difference
- Roll tendency
- Pitch tendency
- Braking nose-dive tendency
- Acceleration squat tendency
- Outside-corner compression increase

Pitot and steering analysis:

- Airspeed vs GPS/VSS speed difference
- Possible wind or speed-sensor inconsistency indicators
- Steering angle vs lateral-g response
- Large steering input with weak lateral response
- Abrupt steering changes

## Map / Lap Analysis

Core analysis and report generation must work offline. Map tiles may require internet.

Required behavior:

- If internet is available, show GPS path on map tiles.
- If internet is unavailable, show the GPS path on a plain coordinate plot.
- Color GPS path by speed, event type, or selected channel.
- Show event markers on the path.
- Allow manual segment selection.
- Allow GPS start/finish line definition.
- Split laps or segments from the GPS line when possible.
- Extract event-based segments such as braking zones, full-throttle acceleration, and high lateral-g corners.

For each segment or lap, summarize:

- Duration
- Maximum speed
- Average speed
- Maximum corrected G
- Maximum RPM
- Maximum temperatures
- Minimum pressures
- Event count

## Report

Reports should be designed for team meetings and run logs.

Report output:

- HTML export required
- PDF export desired

Report content:

- Run summary
- Log diagnostic status
- Key maxima/minima
- Critical and warning events
- Selected overlay graphs
- G-G diagram
- Vehicle behavior summary
- Map/lap or coordinate-path summary
- Segment/lap table
- ADXL345 correction note when applied
- Profile name and settings revision

Report content should be configurable per profile.

## Settings

Settings are a first-class part of the product, not an afterthought.

Settings must support:

- Creating and editing vehicle profiles
- Mapping CSV columns to sensor channels
- Defining aliases such as `OilTemp_C` -> `EOT_IN`
- Setting units
- Setting calibration expressions
- Setting scale and offset
- Inverting sensor direction
- Defining physical valid ranges
- Setting warning and critical thresholds
- Creating composite event rules
- Creating overlay presets
- Selecting report sections
- Importing/exporting profile configuration files

The app should make profile edits traceable by recording a profile revision or last-modified timestamp in exported reports.

## Non-Goals For The First Version

- Real-time telemetry streaming
- Cloud sync
- Team account management
- Precise force estimation from suspension stroke alone
- Precision attitude estimation without drift correction
- Full MATLAB-style custom scripting
- Online-only map dependency

## Key Risks And Mitigations

Risk: The app becomes too complex because every sensor is configurable.

Mitigation: Ship useful default profiles and keep advanced settings collapsible.

Risk: Users misinterpret inferred roll/pitch/yaw as precise attitude.

Mitigation: Label IMU-only outputs as tendency/visualization and raise confidence when suspension channels are available.

Risk: Default warning thresholds are wrong for the team's engine setup.

Mitigation: Treat defaults as conservative starting points, make them editable, and include the active profile in reports.

Risk: GPS quality can make map/lap analysis misleading.

Mitigation: Run diagnostics first and show GPS confidence in the map/lap view and report.

Risk: Sensor column names change between years.

Mitigation: Use profile-based column mapping and aliases.

## Approval Checkpoint

This document captures the agreed product scope for planning. After review and edits, the next step is to create an implementation plan that selects the desktop technology stack, data model, UI architecture, and build order.
