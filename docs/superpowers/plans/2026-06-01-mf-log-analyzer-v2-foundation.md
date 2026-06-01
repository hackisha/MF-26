# MF-LOG-ANALYZER v2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working v2 foundation: a Python/Qt performance prototype that loads a large CSV into a column-oriented log table, maps channels through a vehicle profile, creates derived channels, shows a PySide6 workspace shell, renders a pyqtgraph time-series window, and synchronizes playback/hover cursors.

**Architecture:** Create a new `mf-log-analyzer-v2/` Python project beside the existing v1 work. Keep data logic in `mf_log_analyzer_v2.core`, shared session/playback/cursor state in `mf_log_analyzer_v2.app`, and Qt widgets in `mf_log_analyzer_v2.ui`. The first slice validates the SRS performance direction before implementing domain-specific GPS, DBW, suspension, cooling, reports, and document-library plans.

**Tech Stack:** Python 3.12+, PySide6, pyqtgraph, polars, numpy, pydantic, pytest, pytest-qt, ruff.

---

## Scope Check

The v2 SRS covers many independent subsystems. This plan implements only the foundation and performance-validation slice. Follow-up plans shall cover GPS/LapTime, DBW/ETC, suspension visualization, cooling/electrical analysis, document library, reports, settings, project packaging, and multi-log comparison.

This plan covers these SRS foundations:

- performance validation
- candidate technology stack validation
- column-oriented data model
- CSV load progress
- standard channel/profile mapping foundation
- derived-channel foundation
- left sidebar shell behavior
- central workspace shell
- right properties panel placeholder
- playback clock
- Playback Cursor and Hover Cursor synchronization
- pyqtgraph time-series rendering foundation
- benchmark harness

## File Structure

Create this project structure:

```text
mf-log-analyzer-v2/
  pyproject.toml
  README.md
  src/mf_log_analyzer_v2/__init__.py
  src/mf_log_analyzer_v2/__main__.py
  src/mf_log_analyzer_v2/core/models.py
  src/mf_log_analyzer_v2/core/csv_loader.py
  src/mf_log_analyzer_v2/core/derived.py
  src/mf_log_analyzer_v2/core/default_profiles.py
  src/mf_log_analyzer_v2/app/session.py
  src/mf_log_analyzer_v2/app/cursor_bus.py
  src/mf_log_analyzer_v2/ui/main_window.py
  src/mf_log_analyzer_v2/ui/left_sidebar.py
  src/mf_log_analyzer_v2/ui/properties_panel.py
  src/mf_log_analyzer_v2/ui/timeline.py
  src/mf_log_analyzer_v2/ui/workspace.py
  src/mf_log_analyzer_v2/ui/time_series_window.py
  benchmarks/generate_synthetic_log.py
  benchmarks/benchmark_foundation.py
  tests/core/test_models.py
  tests/core/test_csv_loader.py
  tests/core/test_derived.py
  tests/app/test_session.py
  tests/app/test_cursor_bus.py
  tests/ui/test_left_sidebar.py
  tests/ui/test_time_series_window.py
```

Responsibilities:

- `core/models.py`: immutable-ish domain contracts for channels, profiles, log tables, cursor states, and load progress.
- `core/csv_loader.py`: CSV loading, profile mapping, calibration, progress emission, and `LogTable` creation.
- `core/derived.py`: safe derived-channel formula evaluation for the first slice.
- `core/default_profiles.py`: initial MF profile with core channels and ADXL345 correction definitions.
- `app/session.py`: current log session, playback time, playback speed, and project-wide playback cursor state.
- `app/cursor_bus.py`: visible-workspace hover cursor and project-wide playback cursor event routing.
- `ui/main_window.py`: top-level Qt shell.
- `ui/left_sidebar.py`: group list, plus-dropdowns, and add-window signal.
- `ui/properties_panel.py`: right properties panel shell.
- `ui/timeline.py`: bottom global timeline and left mini playback controls.
- `ui/workspace.py`: floating-window workspace foundation.
- `ui/time_series_window.py`: pyqtgraph time-series window with playback and hover cursor lines.
- `benchmarks/`: synthetic data generation and performance measurement.

## Task 1: Scaffold Python Project

**Files:**
- Create: `mf-log-analyzer-v2/pyproject.toml`
- Create: `mf-log-analyzer-v2/README.md`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/__init__.py`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/__main__.py`
- Test: `mf-log-analyzer-v2/tests/test_package.py`

- [ ] **Step 1: Write the package import test**

Create `tests/test_package.py`:

```python
from mf_log_analyzer_v2 import __version__


def test_package_exports_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Create `pyproject.toml`**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.24"]
build-backend = "hatchling.build"

[project]
name = "mf-log-analyzer-v2"
version = "0.1.0"
description = "High-performance desktop CSV datalog analyzer for MF race car logs"
requires-python = ">=3.12"
dependencies = [
  "numpy>=2.0",
  "polars>=1.0",
  "pydantic>=2.7",
  "PySide6>=6.7",
  "pyqtgraph>=0.13"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-qt>=4.4",
  "ruff>=0.5"
]

[project.scripts]
mf-log-analyzer-v2 = "mf_log_analyzer_v2.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
qt_api = "pyside6"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 3: Create package version and entrypoint**

Create `src/mf_log_analyzer_v2/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/mf_log_analyzer_v2/__main__.py`:

```python
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from mf_log_analyzer_v2.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create README**

Create `README.md`:

```markdown
# MF-LOG-ANALYZER v2

Python/Qt performance-validation implementation for the MF-LOG-ANALYZER v2 SRS.

## Development

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -e ".[dev]"
.\\.venv\\Scripts\\python -m pytest
.\\.venv\\Scripts\\python -m mf_log_analyzer_v2
```
```

- [ ] **Step 5: Run the package test**

Run:

```powershell
cd mf-log-analyzer-v2
python -m pytest tests/test_package.py
```

Expected: PASS, `1 passed`.

- [ ] **Step 6: Commit scaffold**

Run:

```powershell
git add mf-log-analyzer-v2
git commit -m "feat: scaffold MF Log Analyzer v2"
```

## Task 2: Define Core Domain Models

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/models.py`
- Test: `mf-log-analyzer-v2/tests/core/test_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/core/test_models.py`:

```python
import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.models import Calibration, ChannelDefinition, LogTable, VehicleProfile


def test_calibration_scale_offset_and_invert():
    calibration = Calibration(scale=0.125, offset=1.0, invert=True)
    values = np.array([8.0, -8.0])
    np.testing.assert_allclose(calibration.apply(values), np.array([-2.0, 0.0]))


def test_vehicle_profile_resolves_source_alias():
    profile = VehicleProfile(
        profile_id="2025",
        name="2025 Vehicle",
        channels={
            "EOT_IN": ChannelDefinition(
                channel_id="EOT_IN",
                display_name={"en": "Engine Oil Temp In", "ko": "엔진오일 온도 IN"},
                source_columns=("EOT_IN", "OilTemp_C"),
                unit="degC",
                group="CoolingOil",
            )
        },
    )

    assert profile.source_for("EOT_IN", ["Timestamp", "OilTemp_C"]) == "OilTemp_C"


def test_log_table_exposes_column_values():
    frame = pl.DataFrame({"Timestamp": [0.0, 0.1], "RPM": [1000.0, 1200.0]})
    log = LogTable(file_name="sample.csv", frame=frame, time_channel="Timestamp")

    assert log.row_count == 2
    assert log.time_range == (0.0, 0.1)
    np.testing.assert_allclose(log.values("RPM"), np.array([1000.0, 1200.0]))
```

- [ ] **Step 2: Run model tests to verify they fail**

Run:

```powershell
python -m pytest tests/core/test_models.py
```

Expected: FAIL with `ModuleNotFoundError` or missing symbols.

- [ ] **Step 3: Implement core models**

Create `src/mf_log_analyzer_v2/core/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import polars as pl

ChannelGroup = Literal[
    "Time",
    "GPS",
    "Engine",
    "CoolingOil",
    "Fuel",
    "Electrical",
    "DriverInput",
    "DBW",
    "IMU",
    "Suspension",
    "Aero",
    "Diagnostics",
    "UserDefined",
]


@dataclass(frozen=True)
class Calibration:
    scale: float = 1.0
    offset: float = 0.0
    invert: bool = False

    def apply(self, values: np.ndarray) -> np.ndarray:
        calibrated = values * self.scale + self.offset
        return -calibrated if self.invert else calibrated


@dataclass(frozen=True)
class ChannelDefinition:
    channel_id: str
    display_name: dict[str, str]
    source_columns: tuple[str, ...]
    unit: str
    group: ChannelGroup
    calibration: Calibration = field(default_factory=Calibration)
    color: str = "#4c78a8"
    required: bool = False


@dataclass(frozen=True)
class VehicleProfile:
    profile_id: str
    name: str
    channels: dict[str, ChannelDefinition]

    def source_for(self, channel_id: str, headers: list[str]) -> str | None:
        channel = self.channels[channel_id]
        header_lookup = {header.casefold(): header for header in headers}
        for source in channel.source_columns:
            if source.casefold() in header_lookup:
                return header_lookup[source.casefold()]
        return None


@dataclass(frozen=True)
class LogTable:
    file_name: str
    frame: pl.DataFrame
    time_channel: str

    @property
    def row_count(self) -> int:
        return self.frame.height

    @property
    def time_range(self) -> tuple[float, float]:
        if self.row_count == 0:
            return (0.0, 0.0)
        values = self.frame[self.time_channel]
        return (float(values[0]), float(values[-1]))

    def values(self, channel_id: str) -> np.ndarray:
        return self.frame[channel_id].to_numpy()


@dataclass(frozen=True)
class LoadProgress:
    stage: str
    processed_rows: int = 0
    total_rows: int | None = None
```

- [ ] **Step 4: Run model tests**

Run:

```powershell
python -m pytest tests/core/test_models.py
```

Expected: PASS, `3 passed`.

- [ ] **Step 5: Commit core models**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/models.py mf-log-analyzer-v2/tests/core/test_models.py
git commit -m "feat: define v2 core data models"
```

## Task 3: Add Default MF Profile

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/default_profiles.py`
- Test: `mf-log-analyzer-v2/tests/core/test_default_profiles.py`

- [ ] **Step 1: Write default profile tests**

Create `tests/core/test_default_profiles.py`:

```python
from mf_log_analyzer_v2.core.default_profiles import mf_default_profile


def test_default_profile_maps_eot_in_from_oil_temp():
    profile = mf_default_profile()
    assert profile.source_for("EOT_IN", ["Timestamp", "OilTemp_C"]) == "OilTemp_C"


def test_default_profile_defines_adxl_correction():
    profile = mf_default_profile()
    assert profile.channels["AX_CORRECTED_G"].source_columns == ("ax_g",)
    assert profile.channels["AX_CORRECTED_G"].calibration.scale == 0.125


def test_default_profile_contains_dbw_and_suspension_channels():
    profile = mf_default_profile()
    assert "DBW_TARGET_PERCENT" in profile.channels
    assert "DBW_ACTUAL_PERCENT" in profile.channels
    assert "SUSP_FL_MM" in profile.channels
    assert "SUSP_RR_MM" in profile.channels
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/core/test_default_profiles.py
```

Expected: FAIL because `default_profiles.py` does not exist.

- [ ] **Step 3: Implement default profile**

Create `src/mf_log_analyzer_v2/core/default_profiles.py`:

```python
from __future__ import annotations

from mf_log_analyzer_v2.core.models import Calibration, ChannelDefinition, VehicleProfile


def channel(
    channel_id: str,
    display_en: str,
    display_ko: str,
    source_columns: tuple[str, ...],
    unit: str,
    group: str,
    color: str,
    calibration: Calibration | None = None,
    required: bool = False,
) -> ChannelDefinition:
    return ChannelDefinition(
        channel_id=channel_id,
        display_name={"en": display_en, "ko": display_ko},
        source_columns=source_columns,
        unit=unit,
        group=group,  # type: ignore[arg-type]
        color=color,
        calibration=calibration or Calibration(),
        required=required,
    )


def mf_default_profile() -> VehicleProfile:
    adxl_correction = Calibration(scale=0.125)
    channels = {
        "Timestamp": channel("Timestamp", "Timestamp", "시간", ("Timestamp",), "s", "Time", "#9ca3af", required=True),
        "RPM": channel("RPM", "RPM", "RPM", ("RPM",), "rpm", "Engine", "#d55e00"),
        "TPS_PERCENT": channel("TPS_PERCENT", "Throttle Position", "스로틀 포지션", ("TPS_percent",), "%", "DriverInput", "#e69f00"),
        "EOT_IN": channel("EOT_IN", "Engine Oil Temp In", "엔진오일 온도 IN", ("EOT_IN", "OilTemp_C"), "degC", "CoolingOil", "#f59e0b"),
        "EOT_OUT": channel("EOT_OUT", "Engine Oil Temp Out", "엔진오일 온도 OUT", ("EOT_OUT",), "degC", "CoolingOil", "#d97706"),
        "OilPressure_bar": channel("OilPressure_bar", "Oil Pressure", "오일 압력", ("OilPressure_bar",), "bar", "CoolingOil", "#009e73"),
        "Batt_V": channel("Batt_V", "Battery Voltage", "배터리 전압", ("Batt_V",), "V", "Electrical", "#56b4e9"),
        "AX_CORRECTED_G": channel("AX_CORRECTED_G", "Corrected Longitudinal G", "보정 종가속도", ("ax_g",), "g", "IMU", "#0072b2", adxl_correction),
        "AY_CORRECTED_G": channel("AY_CORRECTED_G", "Corrected Lateral G", "보정 횡가속도", ("ay_g",), "g", "IMU", "#cc79a7", adxl_correction),
        "AZ_CORRECTED_G": channel("AZ_CORRECTED_G", "Corrected Vertical G", "보정 수직가속도", ("az_g",), "g", "IMU", "#8b5cf6", adxl_correction),
        "GPS_Speed_KPH": channel("GPS_Speed_KPH", "GPS Speed", "GPS 속도", ("GPS_Speed_KPH",), "km/h", "GPS", "#22c55e"),
        "Latitude": channel("Latitude", "Latitude", "위도", ("Latitude",), "deg", "GPS", "#60a5fa"),
        "Longitude": channel("Longitude", "Longitude", "경도", ("Longitude",), "deg", "GPS", "#34d399"),
        "DBW_TARGET_PERCENT": channel("DBW_TARGET_PERCENT", "DBW Target", "DBW 목표", ("DBW_Target_percent",), "%", "DBW", "#f97316"),
        "DBW_ACTUAL_PERCENT": channel("DBW_ACTUAL_PERCENT", "DBW Actual", "DBW 실제", ("DBW_Pos_percent",), "%", "DBW", "#3b82f6"),
        "SUSP_FL_MM": channel("SUSP_FL_MM", "Suspension FL", "서스펜션 FL", ("Susp_FL_mm",), "mm", "Suspension", "#f59e0b"),
        "SUSP_FR_MM": channel("SUSP_FR_MM", "Suspension FR", "서스펜션 FR", ("Susp_FR_mm",), "mm", "Suspension", "#ef4444"),
        "SUSP_RL_MM": channel("SUSP_RL_MM", "Suspension RL", "서스펜션 RL", ("Susp_RL_mm",), "mm", "Suspension", "#10b981"),
        "SUSP_RR_MM": channel("SUSP_RR_MM", "Suspension RR", "서스펜션 RR", ("Susp_RR_mm",), "mm", "Suspension", "#6366f1"),
    }
    return VehicleProfile(profile_id="mf-default", name="MF Default Vehicle", channels=channels)
```

- [ ] **Step 4: Run default profile tests**

Run:

```powershell
python -m pytest tests/core/test_default_profiles.py
```

Expected: PASS, `3 passed`.

- [ ] **Step 5: Commit default profile**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/default_profiles.py mf-log-analyzer-v2/tests/core/test_default_profiles.py
git commit -m "feat: add MF default vehicle profile"
```

## Task 4: Implement Column-Oriented CSV Loader

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/csv_loader.py`
- Test: `mf-log-analyzer-v2/tests/core/test_csv_loader.py`

- [ ] **Step 1: Write CSV loader tests**

Create `tests/core/test_csv_loader.py`:

```python
from pathlib import Path

import numpy as np

from mf_log_analyzer_v2.core.csv_loader import load_csv
from mf_log_analyzer_v2.core.default_profiles import mf_default_profile


def test_load_csv_maps_aliases_and_calibration(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "Timestamp,OilTemp_C,ax_g,ay_g,DBW_Target_percent,DBW_Pos_percent\\n"
        "0.0,91.5,8.0,-16.0,20.0,18.0\\n"
        "0.1,92.0,16.0,-8.0,22.0,21.0\\n",
        encoding="utf-8",
    )

    log = load_csv(csv_path, mf_default_profile())

    assert log.row_count == 2
    assert log.time_channel == "Timestamp"
    np.testing.assert_allclose(log.values("EOT_IN"), np.array([91.5, 92.0]))
    np.testing.assert_allclose(log.values("AX_CORRECTED_G"), np.array([1.0, 2.0]))
    np.testing.assert_allclose(log.values("AY_CORRECTED_G"), np.array([-2.0, -1.0]))
    np.testing.assert_allclose(log.values("DBW_TARGET_PERCENT"), np.array([20.0, 22.0]))


def test_load_csv_emits_progress(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,RPM\\n0.0,1000\\n", encoding="utf-8")
    stages: list[str] = []

    load_csv(csv_path, mf_default_profile(), on_progress=lambda progress: stages.append(progress.stage))

    assert stages == ["reading", "mapping", "calibrating", "complete"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/core/test_csv_loader.py
```

Expected: FAIL because `csv_loader.py` does not exist.

- [ ] **Step 3: Implement CSV loader**

Create `src/mf_log_analyzer_v2/core/csv_loader.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import polars as pl

from mf_log_analyzer_v2.core.models import LoadProgress, LogTable, VehicleProfile

ProgressCallback = Callable[[LoadProgress], None]


def _emit(callback: ProgressCallback | None, stage: str, processed_rows: int = 0, total_rows: int | None = None) -> None:
    if callback is not None:
        callback(LoadProgress(stage=stage, processed_rows=processed_rows, total_rows=total_rows))


def load_csv(path: Path, profile: VehicleProfile, on_progress: ProgressCallback | None = None) -> LogTable:
    _emit(on_progress, "reading")
    raw = pl.read_csv(path, infer_schema_length=10_000, ignore_errors=True)
    headers = raw.columns

    _emit(on_progress, "mapping", total_rows=raw.height)
    mapped_columns: dict[str, pl.Series] = {}

    _emit(on_progress, "calibrating", total_rows=raw.height)
    for channel_id, channel in profile.channels.items():
        source = profile.source_for(channel_id, headers)
        if source is None:
            continue
        values = raw[source].cast(pl.Float64, strict=False).to_numpy()
        mapped_columns[channel_id] = pl.Series(channel_id, channel.calibration.apply(values))

    if "Timestamp" not in mapped_columns:
        mapped_columns["Timestamp"] = pl.Series("Timestamp", list(range(raw.height)), dtype=pl.Float64)

    frame = pl.DataFrame(mapped_columns)
    _emit(on_progress, "complete", processed_rows=frame.height, total_rows=frame.height)
    return LogTable(file_name=path.name, frame=frame, time_channel="Timestamp")
```

- [ ] **Step 4: Run CSV loader tests**

Run:

```powershell
python -m pytest tests/core/test_csv_loader.py
```

Expected: PASS, `2 passed`.

- [ ] **Step 5: Commit CSV loader**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/csv_loader.py mf-log-analyzer-v2/tests/core/test_csv_loader.py
git commit -m "feat: load CSV logs into columnar tables"
```

## Task 5: Add Derived Channel Engine

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/derived.py`
- Test: `mf-log-analyzer-v2/tests/core/test_derived.py`

- [ ] **Step 1: Write derived-channel tests**

Create `tests/core/test_derived.py`:

```python
import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.derived import add_formula_channel
from mf_log_analyzer_v2.core.models import LogTable


def test_add_formula_channel_subtracts_series():
    log = LogTable(
        file_name="sample.csv",
        time_channel="Timestamp",
        frame=pl.DataFrame(
            {
                "Timestamp": [0.0, 0.1, 0.2],
                "DBW_TARGET_PERCENT": [10.0, 20.0, 30.0],
                "DBW_ACTUAL_PERCENT": [8.0, 18.0, 33.0],
            }
        ),
    )

    updated = add_formula_channel(log, "DBW_ERROR", "DBW_TARGET_PERCENT - DBW_ACTUAL_PERCENT")

    np.testing.assert_allclose(updated.values("DBW_ERROR"), np.array([2.0, 2.0, -3.0]))


def test_add_formula_channel_rejects_unknown_channel():
    log = LogTable(file_name="sample.csv", time_channel="Timestamp", frame=pl.DataFrame({"Timestamp": [0.0]}))

    try:
        add_formula_channel(log, "BAD", "MISSING + 1")
    except ValueError as error:
        assert "Unknown formula token: MISSING" in str(error)
    else:
        raise AssertionError("expected ValueError")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/core/test_derived.py
```

Expected: FAIL because `derived.py` does not exist.

- [ ] **Step 3: Implement formula engine**

Create `src/mf_log_analyzer_v2/core/derived.py`:

```python
from __future__ import annotations

import ast
import operator
from collections.abc import Callable

import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.models import LogTable

BinaryOperator = Callable[[np.ndarray | float, np.ndarray | float], np.ndarray | float]

_BINARY_OPS: dict[type[ast.operator], BinaryOperator] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def add_formula_channel(log: LogTable, channel_id: str, formula: str) -> LogTable:
    expression = ast.parse(formula, mode="eval")
    values = _eval_node(expression.body, log)
    frame = log.frame.with_columns(pl.Series(channel_id, values))
    return LogTable(file_name=log.file_name, frame=frame, time_channel=log.time_channel)


def _eval_node(node: ast.AST, log: LogTable) -> np.ndarray | float:
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported formula operator: {type(node.op).__name__}")
        return op(_eval_node(node.left, log), _eval_node(node.right, log))

    if isinstance(node, ast.Name):
        if node.id not in log.frame.columns:
            raise ValueError(f"Unknown formula token: {node.id}")
        return log.values(node.id)

    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)

    raise ValueError(f"Unsupported formula expression: {ast.dump(node)}")
```

- [ ] **Step 4: Run derived-channel tests**

Run:

```powershell
python -m pytest tests/core/test_derived.py
```

Expected: PASS, `2 passed`.

- [ ] **Step 5: Commit derived engine**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/derived.py mf-log-analyzer-v2/tests/core/test_derived.py
git commit -m "feat: add derived channel formulas"
```

## Task 6: Add Playback Session and Cursor Bus

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/app/session.py`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/app/cursor_bus.py`
- Test: `mf-log-analyzer-v2/tests/app/test_session.py`
- Test: `mf-log-analyzer-v2/tests/app/test_cursor_bus.py`

- [ ] **Step 1: Write session tests**

Create `tests/app/test_session.py`:

```python
import polars as pl

from mf_log_analyzer_v2.app.session import PlaybackSession
from mf_log_analyzer_v2.core.models import LogTable


def test_playback_session_seek_and_tick():
    log = LogTable(file_name="sample.csv", time_channel="Timestamp", frame=pl.DataFrame({"Timestamp": [0.0, 1.0, 2.0]}))
    session = PlaybackSession(log=log)

    session.seek(1.5)
    assert session.current_time_sec == 1.5

    session.playback_speed = 2.0
    session.tick(0.25)
    assert session.current_time_sec == 2.0
    assert session.is_playing is False
```

- [ ] **Step 2: Write cursor bus tests**

Create `tests/app/test_cursor_bus.py`:

```python
from mf_log_analyzer_v2.app.cursor_bus import CursorBus


def test_cursor_bus_publishes_playback_and_hover_times():
    bus = CursorBus()
    seen: list[tuple[str, float | None]] = []
    bus.subscribe(lambda event: seen.append((event.kind, event.time_sec)))

    bus.set_playback_time(12.3)
    bus.set_hover_time(13.7)
    bus.clear_hover_time()

    assert seen == [("playback", 12.3), ("hover", 13.7), ("hover", None)]
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/app/test_session.py tests/app/test_cursor_bus.py
```

Expected: FAIL because app modules do not exist.

- [ ] **Step 4: Implement playback session**

Create `src/mf_log_analyzer_v2/app/session.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from mf_log_analyzer_v2.core.models import LogTable


@dataclass
class PlaybackSession:
    log: LogTable
    current_time_sec: float = 0.0
    is_playing: bool = False
    playback_speed: float = 1.0

    def __post_init__(self) -> None:
        self.current_time_sec = self.log.time_range[0]

    def seek(self, time_sec: float) -> None:
        start, end = self.log.time_range
        self.current_time_sec = max(start, min(end, time_sec))

    def play(self) -> None:
        self.is_playing = True

    def pause(self) -> None:
        self.is_playing = False

    def tick(self, delta_sec: float) -> None:
        if not self.is_playing:
            return
        start, end = self.log.time_range
        del start
        next_time = self.current_time_sec + delta_sec * self.playback_speed
        self.current_time_sec = min(end, next_time)
        if self.current_time_sec >= end:
            self.is_playing = False
```

- [ ] **Step 5: Implement cursor bus**

Create `src/mf_log_analyzer_v2/app/cursor_bus.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CursorEvent:
    kind: Literal["playback", "hover"]
    time_sec: float | None


class CursorBus:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[CursorEvent], None]] = []
        self.playback_time_sec: float | None = None
        self.hover_time_sec: float | None = None

    def subscribe(self, callback: Callable[[CursorEvent], None]) -> None:
        self._subscribers.append(callback)

    def set_playback_time(self, time_sec: float) -> None:
        self.playback_time_sec = time_sec
        self._publish(CursorEvent(kind="playback", time_sec=time_sec))

    def set_hover_time(self, time_sec: float) -> None:
        self.hover_time_sec = time_sec
        self._publish(CursorEvent(kind="hover", time_sec=time_sec))

    def clear_hover_time(self) -> None:
        self.hover_time_sec = None
        self._publish(CursorEvent(kind="hover", time_sec=None))

    def _publish(self, event: CursorEvent) -> None:
        for subscriber in list(self._subscribers):
            subscriber(event)
```

- [ ] **Step 6: Run app tests**

Run:

```powershell
python -m pytest tests/app/test_session.py tests/app/test_cursor_bus.py
```

Expected: PASS, `2 passed`.

- [ ] **Step 7: Commit playback foundation**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/app mf-log-analyzer-v2/tests/app
git commit -m "feat: add playback and cursor state"
```

## Task 7: Build Qt Shell and Left Sidebar

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/main_window.py`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/left_sidebar.py`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/properties_panel.py`
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/workspace.py`
- Test: `mf-log-analyzer-v2/tests/ui/test_left_sidebar.py`

- [ ] **Step 1: Write sidebar tests**

Create `tests/ui/test_left_sidebar.py`:

```python
from PySide6.QtCore import Qt

from mf_log_analyzer_v2.ui.left_sidebar import LeftSidebar


def test_left_sidebar_plus_menu_emits_add_window(qtbot):
    sidebar = LeftSidebar()
    qtbot.addWidget(sidebar)
    emitted: list[str] = []
    sidebar.add_window_requested.connect(emitted.append)

    button = sidebar.plus_button_for("DBW / ETC")
    qtbot.mouseClick(button, Qt.LeftButton)

    action = sidebar.current_menu.actions()[0]
    assert action.text() == "Target vs Actual"
    action.trigger()

    assert emitted == ["dbw.target_vs_actual"]


def test_left_sidebar_search_filters_groups(qtbot):
    sidebar = LeftSidebar()
    qtbot.addWidget(sidebar)

    sidebar.search.setText("dbw")

    assert sidebar.group_widget("DBW / ETC").isVisible()
    assert not sidebar.group_widget("Cooling Efficiency").isVisible()
```

- [ ] **Step 2: Run sidebar tests to verify failure**

Run:

```powershell
python -m pytest tests/ui/test_left_sidebar.py
```

Expected: FAIL because UI modules do not exist.

- [ ] **Step 3: Implement left sidebar**

Create `src/mf_log_analyzer_v2/ui/left_sidebar.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMenu, QPushButton, QVBoxLayout, QWidget


@dataclass(frozen=True)
class SidebarGroup:
    label: str
    entries: dict[str, str]


GROUPS = [
    SidebarGroup("Vehicle Behavior", {"G-G Diagram": "behavior.gg", "3D Vehicle Attitude": "behavior.3d"}),
    SidebarGroup("GPS / LapTime", {"GPS Map": "gps.map", "Lap Time Table": "gps.lap_table"}),
    SidebarGroup("Cooling Efficiency", {"EOT IN / OUT Overlay": "cooling.eot_overlay"}),
    SidebarGroup("Engine Safety", {"RPM / Oil Pressure": "engine.rpm_oil_pressure"}),
    SidebarGroup("DBW / ETC", {"Target vs Actual": "dbw.target_vs_actual", "PID Term Viewer": "dbw.pid_terms"}),
    SidebarGroup("Electrical / Voltage", {"Battery Voltage": "electrical.battery_voltage"}),
    SidebarGroup("Suspension", {"4-Corner Stroke Graph": "suspension.stroke"}),
    SidebarGroup("Data Analysis", {"XY Scatter Plot": "data.xy_scatter", "3D Surface / Map Viewer": "data.surface_map"}),
    SidebarGroup("Documents", {"Add PDF Viewer": "documents.pdf_viewer"}),
    SidebarGroup("User Presets", {"Saved Workspace Preset": "presets.workspace"}),
]


class LeftSidebar(QWidget):
    add_window_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tools, channels, documents...")
        self.current_menu: QMenu | None = None
        self._group_widgets: dict[str, QWidget] = {}
        self._plus_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)

        for group in GROUPS:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            label = QPushButton(group.label)
            label.setFlat(True)
            plus = QPushButton("+")
            plus.clicked.connect(lambda _checked=False, current=group, button=plus: self._open_menu(current, button))
            row_layout.addWidget(label, 1)
            row_layout.addWidget(plus)
            layout.addWidget(row)
            self._group_widgets[group.label] = row
            self._plus_buttons[group.label] = plus

        layout.addStretch(1)
        self.search.textChanged.connect(self._filter)

    def plus_button_for(self, label: str) -> QPushButton:
        return self._plus_buttons[label]

    def group_widget(self, label: str) -> QWidget:
        return self._group_widgets[label]

    def _open_menu(self, group: SidebarGroup, button: QPushButton) -> None:
        menu = QMenu(self)
        self.current_menu = menu
        for text, key in group.entries.items():
            action = menu.addAction(text)
            action.triggered.connect(lambda _checked=False, entry_key=key: self.add_window_requested.emit(entry_key))
        menu.popup(button.mapToGlobal(button.rect().bottomLeft()))

    def _filter(self, text: str) -> None:
        needle = text.casefold().strip()
        for group in GROUPS:
            visible = not needle or needle in group.label.casefold() or any(needle in entry.casefold() for entry in group.entries)
            self._group_widgets[group.label].setVisible(visible)
```

- [ ] **Step 4: Implement workspace, properties, and main window shell**

Create `src/mf_log_analyzer_v2/ui/workspace.py`:

```python
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMdiArea, QMdiSubWindow


class Workspace(QMdiArea):
    def add_placeholder_window(self, window_key: str) -> None:
        label = QLabel(window_key)
        subwindow = QMdiSubWindow()
        subwindow.setWidget(label)
        subwindow.setWindowTitle(window_key)
        self.addSubWindow(subwindow)
        subwindow.show()
```

Create `src/mf_log_analyzer_v2/ui/properties_panel.py`:

```python
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PropertiesPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Properties"))
        layout.addStretch(1)
```

Create `src/mf_log_analyzer_v2/ui/main_window.py`:

```python
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow

from mf_log_analyzer_v2.ui.left_sidebar import LeftSidebar
from mf_log_analyzer_v2.ui.properties_panel import PropertiesPanel
from mf_log_analyzer_v2.ui.workspace import Workspace


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MF-LOG-ANALYZER v2")
        self.resize(1440, 920)

        self.workspace = Workspace()
        self.setCentralWidget(self.workspace)

        self.left_sidebar = LeftSidebar()
        left_dock = QDockWidget("Tools", self)
        left_dock.setWidget(self.left_sidebar)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)

        self.properties_panel = PropertiesPanel()
        right_dock = QDockWidget("Properties", self)
        right_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)

        self.left_sidebar.add_window_requested.connect(self.workspace.add_placeholder_window)
```

- [ ] **Step 5: Run UI shell tests**

Run:

```powershell
python -m pytest tests/ui/test_left_sidebar.py
```

Expected: PASS, `2 passed`.

- [ ] **Step 6: Commit Qt shell**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui mf-log-analyzer-v2/tests/ui/test_left_sidebar.py
git commit -m "feat: add Qt workspace shell"
```

## Task 8: Add pyqtgraph Time-Series Window

**Files:**
- Create: `mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/time_series_window.py`
- Test: `mf-log-analyzer-v2/tests/ui/test_time_series_window.py`

- [ ] **Step 1: Write time-series window tests**

Create `tests/ui/test_time_series_window.py`:

```python
import polars as pl

from mf_log_analyzer_v2.app.cursor_bus import CursorBus
from mf_log_analyzer_v2.core.models import LogTable
from mf_log_analyzer_v2.ui.time_series_window import TimeSeriesWindow


def test_time_series_window_adds_playback_and_hover_lines(qtbot):
    log = LogTable(
        file_name="sample.csv",
        time_channel="Timestamp",
        frame=pl.DataFrame({"Timestamp": [0.0, 0.1, 0.2], "RPM": [1000.0, 1200.0, 1300.0]}),
    )
    bus = CursorBus()
    window = TimeSeriesWindow(log=log, channels=["RPM"], cursor_bus=bus)
    qtbot.addWidget(window)

    bus.set_playback_time(0.1)
    bus.set_hover_time(0.2)

    assert window.playback_line.value() == 0.1
    assert window.hover_line.value() == 0.2
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/ui/test_time_series_window.py
```

Expected: FAIL because `time_series_window.py` does not exist.

- [ ] **Step 3: Implement time-series window**

Create `src/mf_log_analyzer_v2/ui/time_series_window.py`:

```python
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget
import pyqtgraph as pg

from mf_log_analyzer_v2.app.cursor_bus import CursorBus, CursorEvent
from mf_log_analyzer_v2.core.models import LogTable


class TimeSeriesWindow(QWidget):
    def __init__(self, log: LogTable, channels: list[str], cursor_bus: CursorBus) -> None:
        super().__init__()
        self.log = log
        self.channels = channels
        self.cursor_bus = cursor_bus
        self.plot = pg.PlotWidget()
        self.playback_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#d97706", width=2))
        self.hover_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#2563eb", width=1, style=pg.QtCore.Qt.DashLine))

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot)
        self._draw_channels()
        self.plot.addItem(self.playback_line)
        self.plot.addItem(self.hover_line)
        self.cursor_bus.subscribe(self._handle_cursor_event)

    def _draw_channels(self) -> None:
        x = self.log.values(self.log.time_channel)
        for channel in self.channels:
            self.plot.plot(x, self.log.values(channel), name=channel)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind == "playback" and event.time_sec is not None:
            self.playback_line.setValue(event.time_sec)
        if event.kind == "hover" and event.time_sec is not None:
            self.hover_line.setValue(event.time_sec)
```

- [ ] **Step 4: Run time-series window test**

Run:

```powershell
python -m pytest tests/ui/test_time_series_window.py
```

Expected: PASS, `1 passed`.

- [ ] **Step 5: Commit time-series window**

Run:

```powershell
git add mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/time_series_window.py mf-log-analyzer-v2/tests/ui/test_time_series_window.py
git commit -m "feat: add pyqtgraph time series window"
```

## Task 9: Add Synthetic Performance Benchmark

**Files:**
- Create: `mf-log-analyzer-v2/benchmarks/generate_synthetic_log.py`
- Create: `mf-log-analyzer-v2/benchmarks/benchmark_foundation.py`
- Test: `mf-log-analyzer-v2/tests/test_benchmark_scripts.py`

- [ ] **Step 1: Write benchmark script smoke test**

Create `tests/test_benchmark_scripts.py`:

```python
from pathlib import Path

from benchmarks.generate_synthetic_log import generate_synthetic_log


def test_generate_synthetic_log_writes_expected_shape(tmp_path: Path):
    output = tmp_path / "synthetic.csv"
    generate_synthetic_log(output, rows=5, extra_channels=3)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert lines[0].startswith("Timestamp,RPM,TPS_percent,OilTemp_C")
```

- [ ] **Step 2: Run benchmark smoke test to verify failure**

Run:

```powershell
python -m pytest tests/test_benchmark_scripts.py
```

Expected: FAIL because benchmark scripts do not exist.

- [ ] **Step 3: Implement synthetic log generator**

Create `benchmarks/generate_synthetic_log.py`:

```python
from __future__ import annotations

import csv
import math
from pathlib import Path


def generate_synthetic_log(output: Path, rows: int = 300_000, extra_channels: int = 120) -> None:
    headers = [
        "Timestamp",
        "RPM",
        "TPS_percent",
        "OilTemp_C",
        "EOT_OUT",
        "Batt_V",
        "ax_g",
        "ay_g",
        "DBW_Target_percent",
        "DBW_Pos_percent",
    ]
    headers.extend(f"Extra_{index:03d}" for index in range(extra_channels))

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for index in range(rows):
            t = index * 0.02
            rpm = 5000 + 1500 * math.sin(t * 0.7)
            tps = 50 + 30 * math.sin(t * 0.31)
            target = 40 + 20 * math.sin(t * 0.5)
            actual = target - 2.0 * math.sin(t * 1.7)
            row = [
                f"{t:.3f}",
                f"{rpm:.1f}",
                f"{tps:.2f}",
                f"{90 + 5 * math.sin(t * 0.08):.2f}",
                f"{84 + 4 * math.sin(t * 0.08):.2f}",
                f"{13.2 - 0.2 * math.sin(t * 1.2):.2f}",
                f"{8 * math.sin(t * 0.4):.3f}",
                f"{8 * math.cos(t * 0.37):.3f}",
                f"{target:.2f}",
                f"{actual:.2f}",
            ]
            row.extend(f"{math.sin(t + channel):.4f}" for channel in range(extra_channels))
            writer.writerow(row)


if __name__ == "__main__":
    generate_synthetic_log(Path("synthetic_300k.csv"))
```

- [ ] **Step 4: Implement benchmark runner**

Create `benchmarks/benchmark_foundation.py`:

```python
from __future__ import annotations

import time
from pathlib import Path

from benchmarks.generate_synthetic_log import generate_synthetic_log
from mf_log_analyzer_v2.core.csv_loader import load_csv
from mf_log_analyzer_v2.core.default_profiles import mf_default_profile


def main() -> int:
    output = Path("synthetic_300k.csv")
    if not output.exists():
        generate_synthetic_log(output)

    start = time.perf_counter()
    log = load_csv(output, mf_default_profile())
    elapsed = time.perf_counter() - start

    print(f"rows={log.row_count}")
    print(f"columns={len(log.frame.columns)}")
    print(f"load_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run benchmark smoke test**

Run:

```powershell
python -m pytest tests/test_benchmark_scripts.py
```

Expected: PASS, `1 passed`.

- [ ] **Step 6: Run foundation benchmark**

Run:

```powershell
python benchmarks/benchmark_foundation.py
```

Expected output includes:

```text
rows=300000
load_seconds=
```

Record the observed load time in the PR/commit notes.

- [ ] **Step 7: Commit benchmark harness**

Run:

```powershell
git add mf-log-analyzer-v2/benchmarks mf-log-analyzer-v2/tests/test_benchmark_scripts.py
git commit -m "test: add v2 foundation benchmark"
```

## Task 10: Final Verification

**Files:**
- Modify: `mf-log-analyzer-v2/README.md`

- [ ] **Step 1: Run all tests**

Run:

```powershell
cd mf-log-analyzer-v2
python -m pytest
```

Expected: all tests PASS.

- [ ] **Step 2: Run ruff**

Run:

```powershell
python -m ruff check .
```

Expected: PASS with no lint errors.

- [ ] **Step 3: Launch the app shell**

Run:

```powershell
python -m mf_log_analyzer_v2
```

Expected:

- A window titled `MF-LOG-ANALYZER v2` opens.
- The left sidebar is visible.
- The central workspace is visible.
- The right properties panel is visible.
- Clicking `+` on `DBW / ETC` opens a dropdown.
- Triggering `Target vs Actual` creates a workspace placeholder window.

- [ ] **Step 4: Update README with benchmark result**

Append this section to `README.md`, replacing the sample `12.345` value with the observed local benchmark:

````markdown
## Foundation Benchmark

Local benchmark target:

- 300,000 rows
- MF default profile channel mapping
- column-oriented Polars load

Latest local result:

```text
rows=300000
load_seconds=12.345
```
````

- [ ] **Step 5: Commit verification notes**

Run:

```powershell
git add mf-log-analyzer-v2/README.md
git commit -m "docs: record v2 foundation benchmark"
```

## Self-Review

Spec coverage in this foundation plan:

- SRS Section 3: performance target and benchmark foundation
- SRS Section 4: technology-stack validation foundation
- SRS Section 5: column-oriented data model foundation
- SRS Section 6: CSV load and progress foundation
- SRS Section 7-10: vehicle profile, channels, ADXL correction, column mapping foundation
- SRS Section 12: formula-derived channel foundation
- SRS Section 16: application shell foundation
- SRS Section 19-21: left sidebar plus-dropdown and workspace foundation
- SRS Section 23-26: playback, cursor sync, tooltip/time-series rendering foundations

Required follow-up plans:

- Project save/load and package format
- Full settings UI and profile editor
- Document library and PDF viewer
- GPS/LapTime
- Cooling Efficiency
- DBW/ETC response analysis
- Electrical/Pingel voltage analysis
- Suspension 2D/3D visualization
- Data Analysis tools and 3D Surface / Map Viewer
- Reports and exports
- Multi-log comparison
- Annotation and metadata
- Theme/language/unit polish

Placeholder scan:

- This plan contains no TODO/TBD placeholders.
- Every implementation task includes tests, expected command output, implementation snippets, and commit steps.

Type consistency:

- `ChannelDefinition`, `VehicleProfile`, `LogTable`, `LoadProgress`, `PlaybackSession`, `CursorBus`, and `TimeSeriesWindow` are introduced before use by later tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-mf-log-analyzer-v2-foundation.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
