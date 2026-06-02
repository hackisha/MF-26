# MF-LOG-ANALYZER Integrated UX Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the integrated UX improvements selected in A안 while explicitly excluding CSV upload-first-screen changes and expanded data-quality diagnostics.

**Architecture:** Keep the existing PySide6 MDI shell and shared `PlaybackState`. Add focused domain modules for event reviews, segment analysis, report export, and app logging, then connect them through `MainWindow` and project persistence.

**Tech Stack:** Python, PySide6, pyqtgraph, numpy/polars-backed existing data model, pytest, pytest-qt, PyInstaller.

---

## File Structure

- Create `prototype/src/mflog_proto/analysis/segments.py`
  - Owns segment data models and segment statistic calculation.
- Create `prototype/src/mflog_proto/analysis/event_reviews.py`
  - Owns review status, note data, and conversion from playback markers.
- Create `prototype/src/mflog_proto/reporting/html_report.py`
  - Owns HTML report rendering and file writing.
- Create `prototype/src/mflog_proto/diagnostics/app_logging.py`
  - Owns app log path creation and exception logging.
- Modify `prototype/src/mflog_proto/persistence/project_state.py`
  - Upgrade project schema to version 2 with backward-compatible loading for version 1.
- Modify `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
  - Add `EventReviewWindow`, `SegmentAnalysisWindow`, and `ExportReportWindow`.
- Modify `prototype/src/mflog_proto/ui/main_window.py`
  - Wire new windows, grouped left sidebar, project persistence, report export, and log warnings.
- Modify `prototype/tests/test_ui_shell.py`
  - Add UI integration tests for grouped sidebar, event review, segment analysis, report export, and project restore.
- Create `prototype/tests/test_segments.py`
  - Add focused segment statistic tests.
- Create `prototype/tests/test_event_reviews.py`
  - Add focused event review model tests.
- Create `prototype/tests/test_html_report.py`
  - Add focused HTML report tests.
- Create `prototype/tests/test_app_logging.py`
  - Add focused logging utility tests.
- Modify `docs/ACCEPTANCE_TEST.md` and `docs/ACCEPTANCE_TEST_KO.md`
  - Document integrated UX acceptance coverage.

---

### Task 1: Event Review Model

**Files:**
- Create: `prototype/src/mflog_proto/analysis/event_reviews.py`
- Test: `prototype/tests/test_event_reviews.py`

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_event_reviews.py`:

```python
from mflog_proto.analysis.event_reviews import (
    EventReview,
    EventReviewState,
    build_event_reviews,
)


def test_build_event_reviews_defaults_to_unreviewed_without_notes():
    reviews = build_event_reviews(
        [
            {
                "name": "Battery low",
                "time_ms": 18320,
                "severity": "warning",
                "sensor": "Battery voltage",
                "value": 13.878,
                "condition": "value < 14.0",
            }
        ]
    )

    assert reviews == (
        EventReview(
            name="Battery low",
            time_ms=18320,
            severity="warning",
            sensor="Battery voltage",
            value=13.878,
            condition="value < 14.0",
            state=EventReviewState.UNREVIEWED,
            note="",
        ),
    )


def test_event_review_round_trips_project_json_shape():
    review = EventReview(
        name="G limit exceeded",
        time_ms=2500,
        severity="danger",
        sensor="ay",
        value=1.25,
        condition="abs(ay) > 1.0",
        state=EventReviewState.CONFIRMED,
        note="Corner entry spike",
    )

    restored = EventReview.from_dict(review.to_dict())

    assert restored == review
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_event_reviews.py -v
```

Expected: FAIL because `mflog_proto.analysis.event_reviews` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `prototype/src/mflog_proto/analysis/event_reviews.py`:

```python
"""Event review state for analysis playback markers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class EventReviewState(str, Enum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"


@dataclass(frozen=True)
class EventReview:
    name: str
    time_ms: int
    severity: str
    sensor: str
    value: float
    condition: str
    state: EventReviewState = EventReviewState.UNREVIEWED
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "time_ms": self.time_ms,
            "severity": self.severity,
            "sensor": self.sensor,
            "value": self.value,
            "condition": self.condition,
            "state": self.state.value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EventReview":
        state_value = str(data.get("state", EventReviewState.UNREVIEWED.value))
        try:
            state = EventReviewState(state_value)
        except ValueError:
            state = EventReviewState.UNREVIEWED
        return cls(
            name=str(data.get("name", "")),
            time_ms=int(data.get("time_ms", 0)),
            severity=str(data.get("severity", "info")),
            sensor=str(data.get("sensor", "")),
            value=float(data.get("value", 0.0)),
            condition=str(data.get("condition", "")),
            state=state,
            note=str(data.get("note", "")),
        )


def build_event_reviews(events: Iterable[Mapping[str, Any]]) -> tuple[EventReview, ...]:
    return tuple(EventReview.from_dict(event) for event in events)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_event_reviews.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\analysis\event_reviews.py prototype\tests\test_event_reviews.py
git commit -m "feat: add event review model"
```

---

### Task 2: Segment Analysis Model

**Files:**
- Create: `prototype/src/mflog_proto/analysis/segments.py`
- Test: `prototype/tests/test_segments.py`

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_segments.py`:

```python
import numpy as np

from mflog_proto.analysis.segments import AnalysisSegment, compute_segment_summary


def test_compute_segment_summary_uses_available_sensor_channels():
    timestamps = np.array([0.0, 1.0, 2.0, 3.0])
    sensors = {
        "VSS / GPS speed": np.array([10.0, 20.0, 30.0, 40.0]),
        "RPM": np.array([1000.0, 2000.0, 3000.0, 4000.0]),
        "TPS": np.array([5.0, 10.0, 20.0, 25.0]),
        "ax": np.array([0.1, -0.3, 0.5, 0.2]),
        "ay": np.array([0.2, 0.4, -0.7, 0.1]),
        "Battery voltage": np.array([13.9, 13.8, 13.7, 13.6]),
    }

    summary = compute_segment_summary(
        AnalysisSegment(name="Corner 1", start_ms=1000, end_ms=3000),
        timestamps,
        sensors,
    )

    assert summary.name == "Corner 1"
    assert summary.duration_ms == 2000
    assert summary.row_count == 3
    assert summary.average_speed == 30.0
    assert summary.max_speed == 40.0
    assert summary.min_rpm == 2000.0
    assert summary.max_rpm == 4000.0
    assert summary.average_tps == 35.0 / 3.0
    assert summary.max_abs_ax == 0.5
    assert summary.max_abs_ay == 0.7
    assert summary.min_battery_voltage == 13.6


def test_compute_segment_summary_keeps_missing_channels_empty():
    summary = compute_segment_summary(
        AnalysisSegment(name="Short", start_ms=0, end_ms=1000),
        np.array([0.0, 1.0]),
        {},
    )

    assert summary.average_speed is None
    assert summary.max_speed is None
    assert summary.row_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_segments.py -v
```

Expected: FAIL because `mflog_proto.analysis.segments` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `prototype/src/mflog_proto/analysis/segments.py`:

```python
"""Time-range segment summaries for log analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class AnalysisSegment:
    name: str
    start_ms: int
    end_ms: int

    def normalized(self) -> "AnalysisSegment":
        start = min(self.start_ms, self.end_ms)
        end = max(self.start_ms, self.end_ms)
        return AnalysisSegment(self.name, start, end)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "start_ms": self.start_ms, "end_ms": self.end_ms}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AnalysisSegment":
        return cls(
            name=str(data.get("name", "Segment")),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 0)),
        )


@dataclass(frozen=True)
class SegmentSummary:
    name: str
    start_ms: int
    end_ms: int
    duration_ms: int
    row_count: int
    average_speed: float | None
    max_speed: float | None
    min_rpm: float | None
    max_rpm: float | None
    average_tps: float | None
    max_abs_ax: float | None
    max_abs_ay: float | None
    min_battery_voltage: float | None


def compute_segment_summary(
    segment: AnalysisSegment,
    timestamps_seconds: np.ndarray,
    sensors: Mapping[str, np.ndarray],
) -> SegmentSummary:
    normalized = segment.normalized()
    times_ms = np.asarray(timestamps_seconds, dtype=float) * 1000.0
    mask = (times_ms >= normalized.start_ms) & (times_ms <= normalized.end_ms)

    def channel_stat(name: str, reducer) -> float | None:
        values = sensors.get(name)
        if values is None:
            return None
        selected = np.asarray(values, dtype=float)[mask]
        if selected.size == 0:
            return None
        finite = selected[np.isfinite(selected)]
        if finite.size == 0:
            return None
        return float(reducer(finite))

    return SegmentSummary(
        name=normalized.name,
        start_ms=normalized.start_ms,
        end_ms=normalized.end_ms,
        duration_ms=normalized.end_ms - normalized.start_ms,
        row_count=int(np.count_nonzero(mask)),
        average_speed=channel_stat("VSS / GPS speed", np.mean),
        max_speed=channel_stat("VSS / GPS speed", np.max),
        min_rpm=channel_stat("RPM", np.min),
        max_rpm=channel_stat("RPM", np.max),
        average_tps=channel_stat("TPS", np.mean),
        max_abs_ax=channel_stat("ax", lambda values: np.max(np.abs(values))),
        max_abs_ay=channel_stat("ay", lambda values: np.max(np.abs(values))),
        min_battery_voltage=channel_stat("Battery voltage", np.min),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_segments.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\analysis\segments.py prototype\tests\test_segments.py
git commit -m "feat: add segment analysis model"
```

---

### Task 3: Project State v2 Persistence

**Files:**
- Modify: `prototype/src/mflog_proto/persistence/project_state.py`
- Test: `prototype/tests/test_project_state.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_project_state.py`:

```python
from mflog_proto.analysis.event_reviews import EventReview, EventReviewState
from mflog_proto.analysis.segments import AnalysisSegment


def test_project_state_v2_round_trips_event_reviews_and_segments(tmp_path):
    state = ProjectState(
        event_reviews=(
            EventReview(
                name="Battery low",
                time_ms=18320,
                severity="warning",
                sensor="Battery voltage",
                value=13.878,
                condition="value < 14.0",
                state=EventReviewState.CONFIRMED,
                note="Check alternator",
            ),
        ),
        analysis_segments=(AnalysisSegment("Corner 1", 1000, 3500),),
        selected_sidebar_group="분석",
        report_output_path=tmp_path / "report.html",
    )

    path = tmp_path / "session.mflogproj"
    save_project_state(path, state)
    restored = load_project_state(path)

    assert restored.schema_version == 2
    assert restored.event_reviews == state.event_reviews
    assert restored.analysis_segments == state.analysis_segments
    assert restored.selected_sidebar_group == "분석"
    assert restored.report_output_path == tmp_path / "report.html"


def test_project_state_loads_v1_files_with_empty_integrated_ux_fields(tmp_path):
    path = tmp_path / "v1.mflogproj"
    path.write_text(
        '{"schema_version": 1, "active_profile": "prototype", "open_windows": []}',
        encoding="utf-8",
    )

    restored = load_project_state(path)

    assert restored.schema_version == 2
    assert restored.event_reviews == ()
    assert restored.analysis_segments == ()
    assert restored.selected_sidebar_group == "시각화"
    assert restored.report_output_path is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_project_state.py -k "integrated_ux_fields or v1_files" -v
```

Expected: FAIL because new fields are missing or schema version 1 is the only supported version.

- [ ] **Step 3: Write minimal implementation**

Modify `prototype/src/mflog_proto/persistence/project_state.py`:

```python
from mflog_proto.analysis.event_reviews import EventReview
from mflog_proto.analysis.segments import AnalysisSegment


SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
```

Add fields to `ProjectState`:

```python
    event_reviews: tuple[EventReview, ...] = ()
    analysis_segments: tuple[AnalysisSegment, ...] = ()
    selected_sidebar_group: str = "시각화"
    report_output_path: Path | None = None
```

Add these keys to `to_dict()`:

```python
            "event_reviews": [review.to_dict() for review in self.event_reviews],
            "analysis_segments": [segment.to_dict() for segment in self.analysis_segments],
            "selected_sidebar_group": self.selected_sidebar_group,
            "report_output_path": (
                None if self.report_output_path is None else str(self.report_output_path)
            ),
```

Update `from_dict()` schema handling and return construction:

```python
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"Unsupported project schema version: {schema_version}")

        report_output_path = data.get("report_output_path")
```

Set `schema_version=SCHEMA_VERSION` in the returned state and add:

```python
            event_reviews=tuple(
                EventReview.from_dict(item) for item in data.get("event_reviews", [])
            ),
            analysis_segments=tuple(
                AnalysisSegment.from_dict(item) for item in data.get("analysis_segments", [])
            ),
            selected_sidebar_group=str(data.get("selected_sidebar_group", "시각화")),
            report_output_path=(
                None if report_output_path in (None, "") else Path(str(report_output_path))
            ),
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_project_state.py -k "integrated_ux_fields or v1_files" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\persistence\project_state.py prototype\tests\test_project_state.py
git commit -m "feat: persist integrated analysis state"
```

---

### Task 4: Grouped Sidebar

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_ui_shell.py`:

```python
def test_left_sidebar_groups_analysis_items_by_workflow(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    groups = {
        window.analysis_tree.topLevelItem(index).text(0)
        for index in range(window.analysis_tree.topLevelItemCount())
    }

    assert groups == {"시각화", "분석", "리포트", "문서"}
    assert window.sidebar_item_titles("분석") == [
        "Data Analysis",
        "Segment Analysis",
        "Event Review",
    ]
    assert window.sidebar_item_titles("리포트") == [
        "Benchmark Summary",
        "Export Report",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_left_sidebar_groups_analysis_items_by_workflow -v
```

Expected: FAIL because `analysis_tree` or `sidebar_item_titles` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `prototype/src/mflog_proto/ui/main_window.py`, replace the left list with a `QTreeWidget` named `analysis_tree`. Define:

```python
SIDEBAR_GROUPS = {
    "시각화": (
        "Time-Series Graph",
        "GPS Map",
        "G-G Diagram",
        "3D Vehicle Model",
        "Current Values Table",
    ),
    "분석": ("Data Analysis", "Segment Analysis", "Event Review"),
    "리포트": ("Benchmark Summary", "Export Report"),
    "문서": ("Documents",),
}
```

Add helper:

```python
    def sidebar_item_titles(self, group_name: str) -> list[str]:
        for index in range(self.analysis_tree.topLevelItemCount()):
            group = self.analysis_tree.topLevelItem(index)
            if group.text(0) == group_name:
                return [group.child(child).text(0) for child in range(group.childCount())]
        return []
```

Connect child item activation to `add_analysis_window(item.text(0))`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_left_sidebar_groups_analysis_items_by_workflow -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_ui_shell.py
git commit -m "feat: group analysis sidebar"
```

---

### Task 5: Event Review UI

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_ui_shell.py`:

```python
def test_event_review_window_seeks_and_edits_review_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.add_analysis_window("Event Review")
    review_window = window.workspace.subWindowList()[-1].widget()

    assert review_window.windowTitle() == "Event Review"
    assert review_window.event_table.rowCount() == 3

    review_window.event_table.selectRow(1)
    assert window.playback_state.current_time_ms == 2500

    review_window.state_combo.setCurrentText("확인")
    review_window.note_edit.setPlainText("Driver felt rear slip")
    review_window.apply_current_review()

    assert window.event_reviews[1].state.value == "confirmed"
    assert window.event_reviews[1].note == "Driver felt rear slip"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_event_review_window_seeks_and_edits_review_state -v
```

Expected: FAIL because `Event Review` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Add `EventReviewWindow` to `prototype/src/mflog_proto/ui/minimal_analysis_windows.py` with:

```python
class EventReviewWindow(QtWidgets.QWidget):
    reviewChanged = QtCore.Signal(int, object)

    def __init__(self, reviews, seek_to_time_ms, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Event Review")
        self.reviews = list(reviews)
        self.seek_to_time_ms = seek_to_time_ms
        self.event_table = QtWidgets.QTableWidget(0, 5)
        self.event_table.setHorizontalHeaderLabels(["시간", "심각도", "이름", "센서", "상태"])
        self.state_combo = QtWidgets.QComboBox()
        self.state_combo.addItems(["미검토", "확인", "무시"])
        self.note_edit = QtWidgets.QPlainTextEdit()
        self.apply_button = QtWidgets.QPushButton("적용")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.event_table)
        layout.addWidget(self.state_combo)
        layout.addWidget(self.note_edit)
        layout.addWidget(self.apply_button)

        self.event_table.itemSelectionChanged.connect(self._handle_selection_changed)
        self.apply_button.clicked.connect(self.apply_current_review)
        self.refresh_reviews(self.reviews)

    def refresh_reviews(self, reviews):
        self.reviews = list(reviews)
        self.event_table.setRowCount(len(self.reviews))
        for row, review in enumerate(self.reviews):
            values = [
                f"{review.time_ms / 1000.0:.3f} s",
                review.severity,
                review.name,
                review.sensor,
                self._label_for_state(review.state.value),
            ]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, review.time_ms)
                self.event_table.setItem(row, column, item)

    def _handle_selection_changed(self):
        row = self.event_table.currentRow()
        if row < 0 or row >= len(self.reviews):
            return
        review = self.reviews[row]
        self.seek_to_time_ms(review.time_ms)
        self.state_combo.setCurrentText(self._label_for_state(review.state.value))
        self.note_edit.setPlainText(review.note)

    def apply_current_review(self):
        row = self.event_table.currentRow()
        if row < 0 or row >= len(self.reviews):
            return
        self.reviewChanged.emit(row, {
            "state": self._state_for_label(self.state_combo.currentText()),
            "note": self.note_edit.toPlainText(),
        })

    def _label_for_state(self, state):
        return {"unreviewed": "미검토", "confirmed": "확인", "ignored": "무시"}.get(state, "미검토")

    def _state_for_label(self, label):
        return {"미검토": "unreviewed", "확인": "confirmed", "무시": "ignored"}.get(label, "unreviewed")
```

Wire `MainWindow.add_analysis_window("Event Review")` to create the window and update `self.event_reviews` on `reviewChanged`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_event_review_window_seeks_and_edits_review_state -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\ui\minimal_analysis_windows.py prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_ui_shell.py
git commit -m "feat: add event review window"
```

---

### Task 6: Segment Analysis UI

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_ui_shell.py`:

```python
def test_segment_analysis_window_creates_segment_from_playback_times(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    window.add_analysis_window("Segment Analysis")
    segment_window = window.workspace.subWindowList()[-1].widget()

    window.set_playback_seconds(1.0)
    segment_window.set_start_from_playback()
    window.set_playback_seconds(3.0)
    segment_window.set_end_from_playback()
    segment_window.name_edit.setText("Corner 1")
    segment_window.add_segment()

    assert window.analysis_segments[0].name == "Corner 1"
    assert window.analysis_segments[0].start_ms == 1000
    assert window.analysis_segments[0].end_ms == 3000
    assert segment_window.segment_table.rowCount() == 1
    assert segment_window.segment_table.item(0, 0).text() == "Corner 1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_segment_analysis_window_creates_segment_from_playback_times -v
```

Expected: FAIL because `Segment Analysis` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Add `SegmentAnalysisWindow` to `minimal_analysis_windows.py` with start/end spin boxes, name edit, add button, and summary table. It emits `segmentAdded`.

Wire `MainWindow` to:

- Hold `self.analysis_segments`.
- Build sensor arrays from `self.sensor_series`.
- Call `compute_segment_summary`.
- Refresh open segment windows when a segment is added.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_segment_analysis_window_creates_segment_from_playback_times -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\ui\minimal_analysis_windows.py prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_ui_shell.py
git commit -m "feat: add segment analysis window"
```

---

### Task 7: HTML Report Export

**Files:**
- Create: `prototype/src/mflog_proto/reporting/html_report.py`
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_html_report.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing tests**

Create `prototype/tests/test_html_report.py`:

```python
from mflog_proto.analysis.event_reviews import EventReview, EventReviewState
from mflog_proto.analysis.segments import SegmentSummary
from mflog_proto.reporting.html_report import render_html_report


def test_render_html_report_contains_session_events_and_segments():
    html = render_html_report(
        session={
            "file_name": "demo.csv",
            "row_count": 101,
            "duration_seconds": 10.0,
            "sample_ms": 100,
            "event_count": 1,
        },
        selected_channels=("RPM", "TPS"),
        event_reviews=(
            EventReview(
                "Battery low",
                18320,
                "warning",
                "Battery voltage",
                13.878,
                "value < 14.0",
                EventReviewState.CONFIRMED,
                "Check wiring",
            ),
        ),
        segment_summaries=(
            SegmentSummary(
                name="Corner 1",
                start_ms=1000,
                end_ms=3000,
                duration_ms=2000,
                row_count=20,
                average_speed=32.5,
                max_speed=44.0,
                min_rpm=2500.0,
                max_rpm=7200.0,
                average_tps=55.0,
                max_abs_ax=0.8,
                max_abs_ay=1.1,
                min_battery_voltage=13.5,
            ),
        ),
        generated_at="2026-06-02 09:00:00",
    )

    assert "demo.csv" in html
    assert "Battery low" in html
    assert "Check wiring" in html
    assert "Corner 1" in html
    assert "RPM" in html
```

Append UI test:

```python
def test_export_report_window_writes_html_report(tmp_path, qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()
    output = tmp_path / "report.html"

    window.export_report_file(output)

    html = output.read_text(encoding="utf-8")
    assert "MF-LOG-ANALYZER v2 Report" in html
    assert "prototype-demo.csv" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_html_report.py tests\test_ui_shell.py::test_export_report_window_writes_html_report -v
```

Expected: FAIL because report module and `export_report_file` do not exist.

- [ ] **Step 3: Write minimal implementation**

Create `prototype/src/mflog_proto/reporting/html_report.py` with escaped HTML rendering. Add `MainWindow.export_report_file(path)` to build session data, event reviews, segment summaries, and call report writer.

Add `ExportReportWindow` with output path edit and export button. The menu action `Export Report` calls the same method through a save dialog.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_html_report.py tests\test_ui_shell.py::test_export_report_window_writes_html_report -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\reporting\html_report.py prototype\src\mflog_proto\ui\minimal_analysis_windows.py prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_html_report.py prototype\tests\test_ui_shell.py
git commit -m "feat: export analysis reports"
```

---

### Task 8: Playback Dock Layout Hardening

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_ui_shell.py`:

```python
def test_playback_dock_uses_scrollable_sensor_cards_for_narrow_width(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    assert isinstance(window.sensor_card_scroll_area, QtWidgets.QScrollArea)
    assert window.sensor_card_scroll_area.widgetResizable()
    assert window.playback_controls_row.layout().spacing() <= 8
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_playback_dock_uses_scrollable_sensor_cards_for_narrow_width -v
```

Expected: FAIL because the scroll area or named controls row is missing.

- [ ] **Step 3: Write minimal implementation**

Wrap the sensor cards row in `QScrollArea` named `sensor_card_scroll_area`. Name the controls container `playback_controls_row`. Set compact spacing and keep the timeline expanding.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_playback_dock_uses_scrollable_sensor_cards_for_narrow_width -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_ui_shell.py
git commit -m "fix: harden playback dock layout"
```

---

### Task 9: App Logging

**Files:**
- Create: `prototype/src/mflog_proto/diagnostics/app_logging.py`
- Modify: `prototype/src/mflog_proto/app.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_app_logging.py`

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_app_logging.py`:

```python
from mflog_proto.diagnostics.app_logging import log_exception, log_root


def test_log_exception_writes_exception_details(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    try:
        raise RuntimeError("sample failure")
    except RuntimeError as exc:
        path = log_exception(exc, context="report export")

    assert path.parent == log_root()
    text = path.read_text(encoding="utf-8")
    assert "report export" in text
    assert "RuntimeError" in text
    assert "sample failure" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_app_logging.py -v
```

Expected: FAIL because diagnostics module does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `prototype/src/mflog_proto/diagnostics/app_logging.py`:

```python
"""Application diagnostic logging."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import traceback


def log_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = base / "MF-LOG-ANALYZER-v2" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_exception(exc: BaseException, *, context: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = log_root() / f"error-{timestamp}.log"
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    path.write_text(f"Context: {context}\n\n{details}", encoding="utf-8")
    return path
```

Use `log_exception` in report/project save/open failure handlers and top-level app exception hook.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_app_logging.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\diagnostics\app_logging.py prototype\src\mflog_proto\app.py prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_app_logging.py
git commit -m "feat: add app diagnostic logging"
```

---

### Task 10: Integrated Project Restore

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Test: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write the failing test**

Append to `prototype/tests/test_ui_shell.py`:

```python
def test_main_window_restores_event_reviews_segments_and_report_path(qtbot, tmp_path):
    source = MainWindow()
    qtbot.addWidget(source)
    source.load_demo_session()
    source.add_analysis_window("Event Review")
    source.add_analysis_window("Segment Analysis")
    source.event_reviews = source.event_reviews[:1]
    source.analysis_segments = (AnalysisSegment("Corner 1", 1000, 3000),)
    source.report_output_path = tmp_path / "report.html"

    state = source.collect_project_state()

    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.load_demo_session()
    restored.restore_project_state(state)

    assert restored.event_reviews == source.event_reviews
    assert restored.analysis_segments == source.analysis_segments
    assert restored.report_output_path == source.report_output_path
    assert "Event Review" in [sub.windowTitle() for sub in restored.workspace.subWindowList()]
    assert "Segment Analysis" in [sub.windowTitle() for sub in restored.workspace.subWindowList()]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_main_window_restores_event_reviews_segments_and_report_path -v
```

Expected: FAIL because new state is not collected/restored.

- [ ] **Step 3: Write minimal implementation**

Update `collect_project_state()` and `restore_project_state()` to include event reviews, segments, selected sidebar group, and report output path. Ensure `add_analysis_window()` supports `Event Review`, `Segment Analysis`, and `Export Report`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_ui_shell.py::test_main_window_restores_event_reviews_segments_and_report_path -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add prototype\src\mflog_proto\ui\main_window.py prototype\tests\test_ui_shell.py
git commit -m "feat: restore integrated analysis workspace"
```

---

### Task 11: Acceptance Docs and Full Verification

**Files:**
- Modify: `docs/ACCEPTANCE_TEST.md`
- Modify: `docs/ACCEPTANCE_TEST_KO.md`

- [ ] **Step 1: Update acceptance documents**

Add integrated UX coverage:

```markdown
- The left analysis panel groups windows into Visualization, Analysis, Reports, and Documents.
- Event Review supports seek, status, notes, and project restore.
- Segment Analysis creates time ranges and displays available sensor statistics.
- Export Report writes an HTML report with session, event review, and segment summaries.
- Playback dock sensor cards remain scrollable on narrow widths.
- Application save/export exceptions are logged under the local app data log directory.
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest tests\test_event_reviews.py tests\test_segments.py tests\test_html_report.py tests\test_app_logging.py tests\test_project_state.py tests\test_ui_shell.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full tests**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m pytest
```

Expected: all tests pass.

- [ ] **Step 4: Run formatting check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 5: Build EXE**

Run:

```powershell
cd prototype
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

Expected: build completes and `prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe` exists.

- [ ] **Step 6: Rebuild portable zip**

Run:

```powershell
cd prototype
Compress-Archive -Path .\dist\MF-LOG-ANALYZER-v2 -DestinationPath .\dist\MF-LOG-ANALYZER-v2.zip -Force
```

Expected: `prototype\dist\MF-LOG-ANALYZER-v2.zip` exists.

- [ ] **Step 7: Commit**

```powershell
git add docs\ACCEPTANCE_TEST.md docs\ACCEPTANCE_TEST_KO.md
git commit -m "docs: update integrated ux acceptance coverage"
```

---

## Self-Review

- Spec coverage: The plan covers grouped sidebar, selected-window properties continuity, event review, segment analysis, HTML report export, playback dock hardening, logging, and project restore.
- Explicit exclusions: CSV upload-first-screen changes and expanded data-quality diagnostics are excluded from every task.
- Empty-expression scan: The plan contains concrete paths, test commands, expected failures, and implementation targets.
- Type consistency: `EventReview`, `EventReviewState`, `AnalysisSegment`, and `SegmentSummary` are introduced before persistence, UI, and report tasks use them.
