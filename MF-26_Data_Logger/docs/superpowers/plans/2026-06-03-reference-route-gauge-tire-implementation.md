# Reference Route, Gauge, Tire Temperature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GPS reference route creation/save/load/overlay, playback-synced RPM/speed gauges, and future-ready tire temperature visualization windows.

**Architecture:** Keep reusable route serialization in a new analysis module, extend `GPSMapWindow` with a reference-route layer and edit mode, and wire controls through the existing selected-window properties panel. Gauge and tire temperature are new playback-subscribed widgets in `minimal_analysis_windows.py` and are exposed through the same left sidebar/add-window path as the existing analysis windows.

**Tech Stack:** Python 3, PySide6, pyqtgraph, pytest-qt, existing `PlaybackState`, existing `.mflogproj` JSON persistence.

---

## File Structure

- Create `prototype/src/mflog_proto/analysis/reference_route.py`
  - Defines `ReferenceRoutePoint`, `ReferenceRoute`, `save_reference_route`, `load_reference_route`, and validation errors.
- Modify `prototype/src/mflog_proto/persistence/project_state.py`
  - Adds optional `reference_route_path` and `reference_route_name` fields to `.mflogproj` state.
- Modify `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
  - Adds GPS reference route drawing/editing hooks.
  - Adds `GaugeIndicatorsWindow`, private `_GaugeWidget`.
  - Adds `TireTemperatureWindow`, private `_TireTemperaturePanel`.
- Modify `prototype/src/mflog_proto/ui/main_window.py`
  - Adds imports, analysis item registration, window builders, GPS route controls, save/load/clear handlers, state capture/restore wiring.
- Modify `prototype/tests/test_reference_route.py`
  - New route serialization and validation tests.
- Modify `prototype/tests/test_project_state.py`
  - Adds persistence coverage for reference route file path/name.
- Modify `prototype/tests/test_minimal_analysis_windows.py`
  - Adds GPS route overlay/edit, gauge, and tire temperature widget tests.
- Modify `prototype/tests/test_ui_shell.py`
  - Adds left sidebar, add-window, properties, and project-state integration tests.
- Modify `docs/ACCEPTANCE_TEST_KO.md`
  - Adds Korean acceptance checklist items for the new windows and route workflow.

## Task 1: Reference Route Model

**Files:**
- Create: `prototype/src/mflog_proto/analysis/reference_route.py`
- Create: `prototype/tests/test_reference_route.py`

- [ ] **Step 1: Write failing route round-trip and validation tests**

Add this file:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mflog_proto.analysis.reference_route import (
    ReferenceRoute,
    ReferenceRoutePoint,
    load_reference_route,
    save_reference_route,
)


def test_reference_route_round_trips_mflogroute_json(tmp_path: Path) -> None:
    path = tmp_path / "endurance.mflogroute"
    route = ReferenceRoute(
        name="Endurance reference",
        points=(
            ReferenceRoutePoint(latitude=35.29301, longitude=126.574061),
            ReferenceRoutePoint(latitude=35.29320, longitude=126.574300),
        ),
        created_at="2026-06-03T00:00:00+09:00",
        metadata={"source": "manual"},
    )

    save_reference_route(path, route)
    restored = load_reference_route(path)

    assert restored.name == "Endurance reference"
    assert restored.source_path == path
    assert restored.points == route.points
    assert restored.metadata == {"source": "manual"}
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_reference_route_rejects_invalid_coordinates(tmp_path: Path) -> None:
    path = tmp_path / "bad.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": [{"latitude": 91.0, "longitude": 126.0}],
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="latitude"):
        load_reference_route(path)


def test_reference_route_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "future.mflogroute"
    path.write_text(
        json.dumps({"schema_version": 99, "name": "future", "points": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema"):
        load_reference_route(path)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
pytest prototype/tests/test_reference_route.py -v
```

Expected: import failure because `mflog_proto.analysis.reference_route` does not exist.

- [ ] **Step 3: Implement the route model and JSON IO**

Create `prototype/src/mflog_proto/analysis/reference_route.py`:

```python
"""Reference GPS route serialization for GPS Map overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReferenceRoutePoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class ReferenceRoute:
    name: str
    points: tuple[ReferenceRoutePoint, ...]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        )
    )
    metadata: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "created_at": self.created_at,
            "points": [
                {"latitude": point.latitude, "longitude": point.longitude}
                for point in self.points
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        source_path: Path | None = None,
    ) -> "ReferenceRoute":
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported reference route schema: {schema_version}")
        points = tuple(_point_from_dict(item) for item in data.get("points", ()))
        name = str(data.get("name", "")).strip() or _default_route_name(source_path)
        metadata = {str(key): str(value) for key, value in dict(data.get("metadata", {})).items()}
        created_at = str(data.get("created_at", "")).strip()
        return cls(
            name=name,
            points=points,
            created_at=created_at,
            metadata=metadata,
            source_path=source_path,
        )


def save_reference_route(path: Path, route: ReferenceRoute) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(route.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_reference_route(path: Path) -> ReferenceRoute:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Reference route file must contain a JSON object")
    return ReferenceRoute.from_dict(data, source_path=path)


def _point_from_dict(data: Any) -> ReferenceRoutePoint:
    if not isinstance(data, dict):
        raise ValueError("Reference route point must be a JSON object")
    latitude = float(data["latitude"])
    longitude = float(data["longitude"])
    if latitude < -90.0 or latitude > 90.0:
        raise ValueError(f"Invalid latitude: {latitude}")
    if longitude < -180.0 or longitude > 180.0:
        raise ValueError(f"Invalid longitude: {longitude}")
    return ReferenceRoutePoint(latitude=latitude, longitude=longitude)


def _default_route_name(source_path: Path | None) -> str:
    return "Reference route" if source_path is None else source_path.stem
```

- [ ] **Step 4: Run the route tests**

Run:

```powershell
pytest prototype/tests/test_reference_route.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add prototype/src/mflog_proto/analysis/reference_route.py prototype/tests/test_reference_route.py
git commit -m "feat: add reference route serialization"
```

## Task 2: Project State Persistence

**Files:**
- Modify: `prototype/src/mflog_proto/persistence/project_state.py`
- Modify: `prototype/tests/test_project_state.py`

- [ ] **Step 1: Write the failing persistence test**

Add this assertion block to the existing round-trip test in `prototype/tests/test_project_state.py`:

```python
        reference_route_path=Path("routes/endurance.mflogroute"),
        reference_route_name="Endurance reference",
```

Then add these assertions after restore:

```python
    assert restored.reference_route_path == Path("routes/endurance.mflogroute")
    assert restored.reference_route_name == "Endurance reference"
```

Add this legacy-default assertion to the schema-v1/defaults test:

```python
    assert restored.reference_route_path is None
    assert restored.reference_route_name == ""
```

- [ ] **Step 2: Run the focused project state tests**

Run:

```powershell
pytest prototype/tests/test_project_state.py -v
```

Expected: failure because `ProjectState` does not accept the new fields.

- [ ] **Step 3: Add fields and JSON mapping**

Modify `ProjectState`:

```python
    reference_route_path: Path | None = None
    reference_route_name: str = ""
```

Add to `to_dict()`:

```python
            "reference_route_path": (
                None if self.reference_route_path is None else str(self.reference_route_path)
            ),
            "reference_route_name": self.reference_route_name,
```

Add in `from_dict()` before `return cls(...)`:

```python
        reference_route_path = data.get("reference_route_path")
```

Add to the `cls(...)` call:

```python
            reference_route_path=(
                None if reference_route_path in (None, "") else Path(str(reference_route_path))
            ),
            reference_route_name=str(data.get("reference_route_name", "")),
```

- [ ] **Step 4: Run the focused project state tests**

Run:

```powershell
pytest prototype/tests/test_project_state.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add prototype/src/mflog_proto/persistence/project_state.py prototype/tests/test_project_state.py
git commit -m "feat: persist reference route project state"
```

## Task 3: GPSMapWindow Reference Route Layer and Edit Mode

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/tests/test_minimal_analysis_windows.py`

- [ ] **Step 1: Write failing GPS reference route tests**

Add imports:

```python
from mflog_proto.analysis.reference_route import ReferenceRoute, ReferenceRoutePoint
```

Add tests:

```python
def test_gps_map_draws_reference_route_with_start_and_end(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)

    route = ReferenceRoute(
        name="Reference A",
        points=(
            ReferenceRoutePoint(37.0, 127.0),
            ReferenceRoutePoint(37.0001, 127.0002),
            ReferenceRoutePoint(37.0003, 127.0004),
        ),
        created_at="2026-06-03T00:00:00+09:00",
    )
    window.set_reference_route(route)

    assert window.reference_route_name == "Reference A"
    assert window.reference_route_point_count == 3
    assert window.reference_route_start == pytest.approx((37.0, 127.0))
    assert window.reference_route_end == pytest.approx((37.0003, 127.0004))
    assert window.reference_route_visible is True


def test_gps_map_edit_mode_click_adds_reference_points(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1])
    window = GPSMapWindow(playback)
    qtbot.addWidget(window)
    window.resize(640, 360)
    window.show()
    window.plot.setXRange(126.999, 127.001)
    window.plot.setYRange(36.999, 37.001)
    qtbot.waitExposed(window)

    window.set_reference_route_edit_enabled(True)
    scene_pos = window.plot.plotItem.vb.mapViewToScene(QtCore.QPointF(127.0, 37.0))
    window.add_reference_point_from_scene(scene_pos)

    assert window.reference_route_point_count == 1
    assert window.reference_route_start == pytest.approx((37.0, 127.0))
    assert window.reference_route_end == pytest.approx((37.0, 127.0))
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_gps_map_draws_reference_route_with_start_and_end prototype/tests/test_minimal_analysis_windows.py::test_gps_map_edit_mode_click_adds_reference_points -v
```

Expected: attribute errors for missing reference route methods/properties.

- [ ] **Step 3: Implement reference route layer state and items**

In `minimal_analysis_windows.py`, import:

```python
from mflog_proto.analysis.reference_route import ReferenceRoute, ReferenceRoutePoint
```

In `GPSMapWindow.__init__`, add state:

```python
        self._reference_route = ReferenceRoute(name="Reference route", points=())
        self._reference_route_positions: tuple[tuple[float, float], ...] = ()
        self._reference_hover_candidates: tuple[_GPSHoverCandidate, ...] = ()
        self._reference_route_edit_enabled = False
```

Add plot items after `ideal_path_item`:

```python
        self.reference_route_item = pg.PlotDataItem(
            pen=pg.mkPen(QtGui.QColor(72, 201, 176, 220), width=2.5)
        )
        self.reference_start_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#2ecc71"),
            size=12,
        )
        self.reference_end_item = pg.ScatterPlotItem(
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#e74c3c"),
            size=12,
        )
```

Set z-values and add items:

```python
        self.reference_route_item.setZValue(7)
        self.reference_start_item.setZValue(13)
        self.reference_end_item.setZValue(13)
        self.plot.addItem(self.reference_route_item)
        self.plot.addItem(self.reference_start_item)
        self.plot.addItem(self.reference_end_item)
```

Connect click handling:

```python
        self.plot.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
```

- [ ] **Step 4: Add reference route public API**

Add methods/properties inside `GPSMapWindow`:

```python
    @property
    def reference_route_name(self) -> str:
        return self._reference_route.name

    @property
    def reference_route_point_count(self) -> int:
        return len(self._reference_route.points)

    @property
    def reference_route_visible(self) -> bool:
        return self.reference_route_item.isVisible() and self.reference_route_point_count > 0

    @property
    def reference_route_start(self) -> tuple[float, float] | None:
        return self._reference_route_positions[0] if self._reference_route_positions else None

    @property
    def reference_route_end(self) -> tuple[float, float] | None:
        return self._reference_route_positions[-1] if self._reference_route_positions else None

    @property
    def reference_route(self) -> ReferenceRoute:
        return self._reference_route

    @property
    def reference_route_edit_enabled(self) -> bool:
        return self._reference_route_edit_enabled

    def set_reference_route(self, route: ReferenceRoute) -> None:
        self._reference_route = route
        self._refresh_reference_route_items()

    def clear_reference_route(self) -> None:
        self.set_reference_route(ReferenceRoute(name=self._reference_route.name, points=()))

    def set_reference_route_edit_enabled(self, enabled: bool) -> None:
        self._reference_route_edit_enabled = bool(enabled)

    def rename_reference_route(self, name: str) -> None:
        cleaned = name.strip() or "Reference route"
        self.set_reference_route(
            ReferenceRoute(
                name=cleaned,
                points=self._reference_route.points,
                created_at=self._reference_route.created_at,
                metadata=dict(self._reference_route.metadata),
                source_path=self._reference_route.source_path,
            )
        )
```

- [ ] **Step 5: Add point insertion and hover/map sync**

Add:

```python
    def add_reference_point_from_scene(self, scene_pos: QtCore.QPointF) -> None:
        view_point = self.plot.plotItem.vb.mapSceneToView(scene_pos)
        point = ReferenceRoutePoint(latitude=float(view_point.y()), longitude=float(view_point.x()))
        self.set_reference_route(
            ReferenceRoute(
                name=self._reference_route.name,
                points=(*self._reference_route.points, point),
                created_at=self._reference_route.created_at,
                metadata=dict(self._reference_route.metadata),
                source_path=self._reference_route.source_path,
            )
        )

    def _handle_mouse_clicked(self, mouse_event: object) -> None:
        if not self._reference_route_edit_enabled:
            return
        if not hasattr(mouse_event, "scenePos"):
            return
        self.add_reference_point_from_scene(mouse_event.scenePos())
        if hasattr(mouse_event, "accept"):
            mouse_event.accept()

    def _refresh_reference_route_items(self) -> None:
        positions = tuple((point.latitude, point.longitude) for point in self._reference_route.points)
        self._reference_route_positions = positions
        longitudes = tuple(position[1] for position in positions)
        latitudes = tuple(position[0] for position in positions)
        self.reference_route_item.setData(longitudes, latitudes)
        self.reference_route_item.setVisible(bool(positions))
        if positions:
            self.reference_start_item.setData([{"pos": (positions[0][1], positions[0][0])}])
            self.reference_end_item.setData([{"pos": (positions[-1][1], positions[-1][0])}])
        else:
            self.reference_start_item.setData([])
            self.reference_end_item.setData([])
        self._reference_hover_candidates = tuple(
            _GPSHoverCandidate(
                route_name=f"Reference: {self._reference_route.name}",
                sample_index=index,
                latitude=position[0],
                longitude=position[1],
            )
            for index, position in enumerate(positions)
        )
        self._sync_hover_and_map_positions()
        self._refresh_map_background()
```

Modify `_sync_hover_and_map_positions()`:

```python
        self._hover_candidates = (
            self._route_hover_candidates
            + self._ideal_hover_candidates
            + self._reference_hover_candidates
        )
        self._all_positions = (
            self._route_positions
            + self._ideal_valid_positions
            + self._reference_route_positions
        )
```

- [ ] **Step 6: Run the focused GPS tests**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_gps_map_draws_reference_route_with_start_and_end prototype/tests/test_minimal_analysis_windows.py::test_gps_map_edit_mode_click_adds_reference_points -v
```

Expected: both tests pass.

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add prototype/src/mflog_proto/ui/minimal_analysis_windows.py prototype/tests/test_minimal_analysis_windows.py
git commit -m "feat: add gps reference route overlay"
```

## Task 4: MainWindow Reference Route Controls

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Modify: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write failing UI integration tests**

Add imports:

```python
from mflog_proto.analysis.reference_route import ReferenceRoute, ReferenceRoutePoint
```

Add tests:

```python
def test_gps_properties_control_reference_route_for_open_and_new_windows(qtbot, tmp_path):
    route_path = tmp_path / "reference.mflogroute"
    window = MainWindow()
    qtbot.addWidget(window)
    gps_window = window.add_analysis_window("GPS Map").widget()

    assert window.reference_route_edit_checkbox.objectName() == "referenceRouteEditCheckbox"
    assert window.reference_route_points_label.text() == "0 points"

    window.reference_route_name_edit.setText("Reference A")
    window.reference_route_edit_checkbox.setChecked(True)
    window.set_reference_route(
        ReferenceRoute(
            name="Reference A",
            points=(ReferenceRoutePoint(35.0, 126.0), ReferenceRoutePoint(35.1, 126.1)),
            created_at="2026-06-03T00:00:00+09:00",
        )
    )

    assert gps_window.reference_route_name == "Reference A"
    assert gps_window.reference_route_point_count == 2
    assert window.reference_route_points_label.text() == "2 points"

    assert window.save_reference_route_path(route_path) is True
    window.clear_reference_route()
    assert gps_window.reference_route_point_count == 0

    assert window.load_reference_route_path(route_path) is True
    new_gps_window = window.add_analysis_window("GPS Map").widget()
    assert new_gps_window.reference_route_name == "Reference A"
    assert new_gps_window.reference_route_point_count == 2
```

- [ ] **Step 2: Run the focused UI test to verify it fails**

Run:

```powershell
pytest prototype/tests/test_ui_shell.py::test_gps_properties_control_reference_route_for_open_and_new_windows -v
```

Expected: missing `reference_route_edit_checkbox`.

- [ ] **Step 3: Add MainWindow state, imports, and capture/restore**

Add imports:

```python
from mflog_proto.analysis.reference_route import (
    ReferenceRoute,
    load_reference_route,
    save_reference_route,
)
```

In `MainWindow.__init__`:

```python
        self.reference_route = ReferenceRoute(name="Reference route", points=())
        self.reference_route_path: Path | None = None
```

In `capture_project_state(...)`:

```python
            reference_route_path=self.reference_route_path,
            reference_route_name=self.reference_route.name,
```

In `restore_project_state(...)`, after vehicle model restore:

```python
        self.reference_route_path = state.reference_route_path
        if state.reference_route_name:
            self.reference_route = ReferenceRoute(
                name=state.reference_route_name,
                points=self.reference_route.points,
                created_at=self.reference_route.created_at,
                metadata=dict(self.reference_route.metadata),
                source_path=self.reference_route_path,
            )
        if self.reference_route_path is not None and self.reference_route_path.exists():
            self.load_reference_route_path(self.reference_route_path)
```

- [ ] **Step 4: Add GPS controls to the properties panel**

In `_build_right_properties_panel`, create controls:

```python
        self.reference_route_edit_checkbox = QtWidgets.QCheckBox("Edit route")
        self.reference_route_edit_checkbox.setObjectName("referenceRouteEditCheckbox")
        self.reference_route_edit_checkbox.toggled.connect(
            self._update_reference_route_controls
        )
        self.reference_route_name_edit = QtWidgets.QLineEdit(self.reference_route.name)
        self.reference_route_name_edit.setObjectName("referenceRouteNameEdit")
        self.reference_route_name_edit.editingFinished.connect(
            self._rename_reference_route_from_controls
        )
        self.reference_route_load_button = QtWidgets.QPushButton("Load route...")
        self.reference_route_load_button.setObjectName("referenceRouteLoadButton")
        self.reference_route_load_button.clicked.connect(self._open_reference_route_load_dialog)
        self.reference_route_save_button = QtWidgets.QPushButton("Save route...")
        self.reference_route_save_button.setObjectName("referenceRouteSaveButton")
        self.reference_route_save_button.clicked.connect(self._open_reference_route_save_dialog)
        self.reference_route_clear_button = QtWidgets.QPushButton("Clear")
        self.reference_route_clear_button.setObjectName("referenceRouteClearButton")
        self.reference_route_clear_button.clicked.connect(self.clear_reference_route)
        self.reference_route_points_label = QtWidgets.QLabel("0 points")
        self.reference_route_points_label.setObjectName("referenceRoutePointsLabel")
```

Append rows to `gps_properties_page`:

```python
                ("Ref edit", self.reference_route_edit_checkbox),
                ("Ref name", self.reference_route_name_edit),
                ("Ref load", self.reference_route_load_button),
                ("Ref save", self.reference_route_save_button),
                ("Ref clear", self.reference_route_clear_button),
                ("Ref points", self.reference_route_points_label),
```

- [ ] **Step 5: Add MainWindow reference route methods**

Add:

```python
    def set_reference_route(self, route: ReferenceRoute) -> None:
        self.reference_route = route
        self.reference_route_path = route.source_path
        if hasattr(self, "reference_route_name_edit"):
            self.reference_route_name_edit.setText(route.name)
        self._apply_reference_route_to_open_windows()
        self._refresh_reference_route_status()

    def clear_reference_route(self) -> None:
        self.set_reference_route(ReferenceRoute(name=self.reference_route.name, points=()))

    def load_reference_route_path(self, path: Path) -> bool:
        try:
            route = load_reference_route(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.statusBar().showMessage(f"Reference route load failed: {exc}", 5000)
            return False
        self.set_reference_route(route)
        self.statusBar().showMessage(f"Loaded reference route: {path.name}", 5000)
        return True

    def save_reference_route_path(self, path: Path) -> bool:
        route = ReferenceRoute(
            name=self.reference_route.name,
            points=self.reference_route.points,
            created_at=self.reference_route.created_at,
            metadata=dict(self.reference_route.metadata),
            source_path=path,
        )
        try:
            save_reference_route(path, route)
        except OSError as exc:
            self.statusBar().showMessage(f"Reference route save failed: {exc}", 5000)
            return False
        self.reference_route = route
        self.reference_route_path = path
        self.statusBar().showMessage(f"Saved reference route: {path.name}", 5000)
        return True
```

Add imports for `json` if needed by exception handling.

- [ ] **Step 6: Add dialog and window sync helpers**

Add:

```python
    def _open_reference_route_load_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load reference route",
            str(Path.cwd()),
            "MF route (*.mflogroute);;JSON (*.json);;All files (*.*)",
        )
        if path:
            self.load_reference_route_path(Path(path))

    def _open_reference_route_save_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save reference route",
            str(self.reference_route_path or Path.cwd() / "reference.mflogroute"),
            "MF route (*.mflogroute);;JSON (*.json);;All files (*.*)",
        )
        if path:
            self.save_reference_route_path(Path(path))

    def _rename_reference_route_from_controls(self) -> None:
        name = self.reference_route_name_edit.text().strip() or "Reference route"
        self.set_reference_route(
            ReferenceRoute(
                name=name,
                points=self.reference_route.points,
                created_at=self.reference_route.created_at,
                metadata=dict(self.reference_route.metadata),
                source_path=self.reference_route_path,
            )
        )

    def _update_reference_route_controls(self, *_args: object) -> None:
        self._apply_reference_route_to_open_windows()

    def _apply_reference_route_to_open_windows(self) -> None:
        edit_enabled = (
            hasattr(self, "reference_route_edit_checkbox")
            and self.reference_route_edit_checkbox.isChecked()
        )
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, GPSMapWindow):
                widget.set_reference_route(self.reference_route)
                widget.set_reference_route_edit_enabled(edit_enabled)

    def _refresh_reference_route_status(self) -> None:
        if hasattr(self, "reference_route_points_label"):
            self.reference_route_points_label.setText(
                f"{len(self.reference_route.points)} points"
            )
```

In `_build_gps_map_window`, after ideal path:

```python
        widget.set_reference_route(self.reference_route)
        if hasattr(self, "reference_route_edit_checkbox"):
            widget.set_reference_route_edit_enabled(self.reference_route_edit_checkbox.isChecked())
```

- [ ] **Step 7: Run the focused UI test**

Run:

```powershell
pytest prototype/tests/test_ui_shell.py::test_gps_properties_control_reference_route_for_open_and_new_windows -v
```

Expected: pass.

- [ ] **Step 8: Commit Task 4**

Run:

```powershell
git add prototype/src/mflog_proto/ui/main_window.py prototype/tests/test_ui_shell.py
git commit -m "feat: wire reference route controls"
```

## Task 5: Gauge Indicators Window

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Modify: `prototype/tests/test_minimal_analysis_windows.py`
- Modify: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write failing gauge tests**

Add to `test_minimal_analysis_windows.py`:

```python
def test_gauge_indicators_update_rpm_and_speed_from_playback(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = GaugeIndicatorsWindow(
        playback,
        {
            "RPM": [1000.0, 4500.0, 8000.0],
            "GPS speed": [10.0, 55.5, 100.0],
        },
    )
    qtbot.addWidget(window)

    playback.set_sample(1)

    assert window.gauge_value("RPM") == pytest.approx(4500.0)
    assert window.gauge_text("RPM") == "4500 rpm"
    assert window.gauge_value("Speed") == pytest.approx(55.5)
    assert window.gauge_text("Speed") == "55.5 km/h"
```

Add to `test_ui_shell.py`:

```python
def test_left_sidebar_adds_gauge_indicators_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_demo_session()

    gauge_window = window.add_analysis_window("Gauge Indicators").widget()
    window.set_playback_position(10)

    assert "Gauge Indicators" in window.sidebar_item_titles("시각화")
    assert gauge_window.gauge_value("RPM") == pytest.approx(window.sensor_series["RPM"][10])
```

- [ ] **Step 2: Run the focused gauge tests**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_gauge_indicators_update_rpm_and_speed_from_playback prototype/tests/test_ui_shell.py::test_left_sidebar_adds_gauge_indicators_window -v
```

Expected: missing `GaugeIndicatorsWindow`.

- [ ] **Step 3: Implement `_GaugeWidget` and `GaugeIndicatorsWindow`**

Add to `minimal_analysis_windows.py` after `CurrentValuesWindow`:

```python
class _GaugeWidget(QtWidgets.QWidget):
    def __init__(self, title: str, unit: str, maximum: float, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.maximum = float(maximum)
        self.value: float | None = None
        self.setMinimumSize(170, 140)

    def set_value(self, value: float | None) -> None:
        self.value = None if value is None else float(value)
        self.update()

    def value_text(self) -> str:
        if self.value is None:
            return "-"
        if self.unit == "rpm":
            return f"{self.value:.0f} rpm"
        return f"{self.value:.1f} {self.unit}"

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)
        center = QtCore.QPointF(rect.center().x(), rect.bottom() - 18)
        radius = min(rect.width() / 2.0, rect.height() - 38)
        arc_rect = QtCore.QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.setPen(QtGui.QPen(QtGui.QColor("#41505a"), 8))
        painter.drawArc(arc_rect, 30 * 16, 120 * 16)
        ratio = 0.0 if self.value is None else min(max(self.value / self.maximum, 0.0), 1.0)
        painter.setPen(QtGui.QPen(QtGui.QColor("#f4c95d"), 8))
        painter.drawArc(arc_rect, 150 * 16, int(-120 * ratio * 16))
        angle = math.radians(150 - 120 * ratio)
        needle_end = QtCore.QPointF(
            center.x() + math.cos(angle) * radius * 0.78,
            center.y() - math.sin(angle) * radius * 0.78,
        )
        painter.setPen(QtGui.QPen(QtGui.QColor("#e8f1f5"), 3))
        painter.drawLine(center, needle_end)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter, self.title)
        painter.setPen(QtGui.QColor("#f4c95d"))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignHCenter, self.value_text())


class GaugeIndicatorsWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        series: dict[str, Sequence[float | None]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gaugeIndicatorsWindow")
        self._playback_state = playback_state
        self._series = series
        self._speed_channel = _first_existing_channel(series, ("GPS speed", "VSS / GPS speed", "GPS_SPEED_KPH", "GPS_Speed_KPH", "VSS_kmh"))
        self._gauges = {
            "RPM": _GaugeWidget("RPM", "rpm", 9000.0),
            "Speed": _GaugeWidget("Speed", "km/h", 180.0),
        }
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        for gauge in self._gauges.values():
            layout.addWidget(gauge, 1)
        self._update_values(self._playback_state.current_sample)

    def gauge_value(self, name: str) -> float | None:
        return self._gauges[name].value

    def gauge_text(self, name: str) -> str:
        return self._gauges[name].value_text()

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_values(event.sample_index)

    def _update_values(self, sample_index: int) -> None:
        self._gauges["RPM"].set_value(_sample_value(self._series.get("RPM"), sample_index))
        self._gauges["Speed"].set_value(_sample_value(self._series.get(self._speed_channel, ()), sample_index))
```

Add helpers near existing formatting helpers:

```python
def _first_existing_channel(series: Mapping[str, Sequence[float | None]], names: Sequence[str]) -> str:
    for name in names:
        if name in series:
            return name
    return ""


def _sample_value(values: Sequence[float | None] | None, sample_index: int) -> float | None:
    if not values:
        return None
    clamped = min(max(sample_index, 0), len(values) - 1)
    value = values[clamped]
    return None if value is None else float(value)
```

- [ ] **Step 4: Wire MainWindow**

Add `GaugeIndicatorsWindow` to the import list from `minimal_analysis_windows`.

Add `"Gauge Indicators"` to `DEFAULT_ANALYSIS_ITEMS` and the `시각화` tuple in `SIDEBAR_GROUPS`.

Add in `add_analysis_window`:

```python
        elif title == "Gauge Indicators":
            widget = self._build_gauge_indicators_window()
```

Add builder:

```python
    def _build_gauge_indicators_window(self) -> GaugeIndicatorsWindow:
        return GaugeIndicatorsWindow(self.playback_state, self.sensor_series)
```

Update `_default_analysis_window_size`:

```python
        if title == "Gauge Indicators":
            return QtCore.QSize(440, 230)
```

- [ ] **Step 5: Run gauge tests**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_gauge_indicators_update_rpm_and_speed_from_playback prototype/tests/test_ui_shell.py::test_left_sidebar_adds_gauge_indicators_window -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit Task 5**

Run:

```powershell
git add prototype/src/mflog_proto/ui/minimal_analysis_windows.py prototype/src/mflog_proto/ui/main_window.py prototype/tests/test_minimal_analysis_windows.py prototype/tests/test_ui_shell.py
git commit -m "feat: add playback gauge indicators"
```

## Task 6: Tire Temperature Window

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Modify: `prototype/tests/test_minimal_analysis_windows.py`
- Modify: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write failing tire temperature tests**

Add to `test_minimal_analysis_windows.py`:

```python
def test_tire_temperature_window_maps_channels_and_empty_states(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1])
    window = TireTemperatureWindow(
        playback,
        {
            "Tire_FL_C": [45.0, 55.0],
            "FR_TireTemp_C": [46.0, 56.0],
        },
    )
    qtbot.addWidget(window)

    playback.set_sample(1)

    assert window.temperature_text("FL") == "55.0 C"
    assert window.temperature_text("FR") == "56.0 C"
    assert window.temperature_text("RL") == "-"
    assert window.temperature_text("RR") == "-"
```

Add to `test_ui_shell.py`:

```python
def test_left_sidebar_adds_tire_temperature_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    tire_window = window.add_analysis_window("Tire Temperature").widget()

    assert "Tire Temperature" in window.sidebar_item_titles("시각화")
    assert tire_window.temperature_text("FL") == "-"
```

- [ ] **Step 2: Run the focused tire tests**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_tire_temperature_window_maps_channels_and_empty_states prototype/tests/test_ui_shell.py::test_left_sidebar_adds_tire_temperature_window -v
```

Expected: missing `TireTemperatureWindow`.

- [ ] **Step 3: Implement tire temperature panel/window**

Add to `minimal_analysis_windows.py` after `GaugeIndicatorsWindow`:

```python
_TIRE_CHANNEL_ALIASES: dict[str, tuple[str, ...]] = {
    "FL": ("Tire_FL_C", "FL_TireTemp_C", "TireTemp_FL", "FL_temp"),
    "FR": ("Tire_FR_C", "FR_TireTemp_C", "TireTemp_FR", "FR_temp"),
    "RL": ("Tire_RL_C", "RL_TireTemp_C", "TireTemp_RL", "RL_temp"),
    "RR": ("Tire_RR_C", "RR_TireTemp_C", "TireTemp_RR", "RR_temp"),
}


class _TireTemperaturePanel(QtWidgets.QWidget):
    def __init__(self, corner: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.corner = corner
        self.temperature: float | None = None
        self.setMinimumSize(150, 190)

    def set_temperature(self, value: float | None) -> None:
        self.temperature = value
        self.update()

    def temperature_text(self) -> str:
        return "-" if self.temperature is None else f"{self.temperature:.1f} C"

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.setPen(QtGui.QColor("#f4c95d"))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft, self.corner)
        tire_rect = QtCore.QRectF(rect.center().x() - 32, rect.center().y() - 48, 64, 96)
        painter.setPen(QtGui.QPen(QtGui.QColor("#95a5a6"), 3))
        painter.setBrush(QtGui.QColor("#151b1f"))
        painter.drawRoundedRect(tire_rect, 24, 24)
        bar_rect = QtCore.QRectF(rect.right() - 24, rect.top() + 28, 16, rect.height() - 66)
        gradient = QtGui.QLinearGradient(bar_rect.bottomLeft(), bar_rect.topLeft())
        gradient.setColorAt(0.0, QtGui.QColor("#3498db"))
        gradient.setColorAt(1.0, QtGui.QColor("#e74c3c"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#62727c"), 1))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(bar_rect)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignHCenter, self.temperature_text())


class TireTemperatureWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        series: dict[str, Sequence[float | None]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tireTemperatureWindow")
        self._playback_state = playback_state
        self._series = series
        self._corner_channels = {
            corner: _first_existing_channel(series, aliases)
            for corner, aliases in _TIRE_CHANNEL_ALIASES.items()
        }
        self._panels = {corner: _TireTemperaturePanel(corner) for corner in ("FL", "FR", "RL", "RR")}
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._panels["FL"], 0, 0)
        layout.addWidget(self._panels["FR"], 0, 1)
        layout.addWidget(self._panels["RL"], 1, 0)
        layout.addWidget(self._panels["RR"], 1, 1)
        self._update_values(self._playback_state.current_sample)

    def temperature_text(self, corner: str) -> str:
        return self._panels[corner].temperature_text()

    def dispose(self) -> None:
        self._unsubscribe()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is CursorKind.PLAYBACK:
            self._update_values(event.sample_index)

    def _update_values(self, sample_index: int) -> None:
        for corner, panel in self._panels.items():
            channel_id = self._corner_channels[corner]
            panel.set_temperature(_sample_value(self._series.get(channel_id, ()), sample_index))
```

- [ ] **Step 4: Wire MainWindow**

Add `TireTemperatureWindow` to the import list.

Add `"Tire Temperature"` to `DEFAULT_ANALYSIS_ITEMS` and the `시각화` tuple.

Add in `add_analysis_window`:

```python
        elif title == "Tire Temperature":
            widget = self._build_tire_temperature_window()
```

Add builder:

```python
    def _build_tire_temperature_window(self) -> TireTemperatureWindow:
        return TireTemperatureWindow(self.playback_state, self.sensor_series)
```

Update `_default_analysis_window_size`:

```python
        if title == "Tire Temperature":
            return QtCore.QSize(430, 380)
```

- [ ] **Step 5: Run tire tests**

Run:

```powershell
pytest prototype/tests/test_minimal_analysis_windows.py::test_tire_temperature_window_maps_channels_and_empty_states prototype/tests/test_ui_shell.py::test_left_sidebar_adds_tire_temperature_window -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit Task 6**

Run:

```powershell
git add prototype/src/mflog_proto/ui/minimal_analysis_windows.py prototype/src/mflog_proto/ui/main_window.py prototype/tests/test_minimal_analysis_windows.py prototype/tests/test_ui_shell.py
git commit -m "feat: add tire temperature visualization"
```

## Task 7: Final Integration, Docs, Verification, GitHub Upload

**Files:**
- Modify: `docs/ACCEPTANCE_TEST_KO.md`
- Modify test expectations if counts are documented in `docs/ACCEPTANCE_TEST.md`.

- [ ] **Step 1: Update Korean acceptance checklist**

Add this section to `docs/ACCEPTANCE_TEST_KO.md`:

```markdown
## Reference Route / Gauge / Tire Temperature

- GPS Map 선택 후 우측 속성에서 Reference Route 편집을 켠다.
- 지도 위를 클릭해 기준 경로 점을 추가하고 START/END 마커를 확인한다.
- 기준 경로를 `.mflogroute`로 저장한 뒤 Clear 후 다시 Load해서 동일한 경로가 복원되는지 확인한다.
- 실제 CSV GPS 경로와 기준 경로가 GPS Map 위에 동시에 보이는지 확인한다.
- 좌측 패널에서 Gauge Indicators를 추가하고 RPM/Speed가 재생 위치에 맞춰 변하는지 확인한다.
- 좌측 패널에서 Tire Temperature를 추가하고 센서가 없을 때 FL/FR/RL/RR 빈 상태 표시가 깨지지 않는지 확인한다.
```

- [ ] **Step 2: Run focused suites**

Run:

```powershell
$env:QT_QPA_PLATFORM='minimal'; $env:QT_QPA_FONTDIR='C:\Windows\Fonts'; pytest prototype/tests/test_reference_route.py prototype/tests/test_project_state.py prototype/tests/test_minimal_analysis_windows.py prototype/tests/test_ui_shell.py -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
$env:QT_QPA_PLATFORM='minimal'; $env:QT_QPA_FONTDIR='C:\Windows\Fonts'; pytest
```

Expected: all tests pass.

- [ ] **Step 4: Build EXE**

Run the existing project build command used by this repo. If the last successful flow used PyInstaller from the prototype package, run the same command from repository root:

```powershell
$env:QT_QPA_PLATFORM='minimal'; $env:QT_QPA_FONTDIR='C:\Windows\Fonts'; pyinstaller prototype\MF-LOG-ANALYZER-v2.spec --noconfirm
```

Expected: `dist` contains the MF-LOG-ANALYZER executable/app bundle without build errors.

- [ ] **Step 5: Smoke run EXE**

Run with escalation because GUI app launch is outside the normal sandbox:

```powershell
Start-Process -FilePath .\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe -WindowStyle Hidden
```

Expected: process starts and remains alive long enough to verify startup, then terminate it cleanly.

- [ ] **Step 6: Final commit**

Run:

```powershell
git add docs/ACCEPTANCE_TEST_KO.md
git commit -m "docs: add reference route acceptance checks"
```

If implementation tasks have uncommitted fixes from verification, include them in this commit with the same message only if they are directly related to making the feature pass verification.

- [ ] **Step 7: Upload to GitHub subfolder branch**

Push the local `master` branch:

```powershell
git push origin master
```

Create or refresh the upload worktree on `codex/mf-26-data-logger-import`:

```powershell
git worktree add .github-mf26-upload codex/mf-26-data-logger-import
```

If the worktree already exists, skip the add command and continue. Export the committed tree into `MF-26_Data_Logger`:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$root = (Resolve-Path '.').Path; $worktree = (Resolve-Path '.\.github-mf26-upload').Path; $target = Join-Path $worktree 'MF-26_Data_Logger'; $archive = Join-Path $env:TEMP 'mflog_data_logger_export.zip'; if (-not $worktree.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) { throw \"Unexpected worktree path: $worktree\" }; if (-not $target.StartsWith($worktree, [System.StringComparison]::OrdinalIgnoreCase)) { throw \"Unexpected target path: $target\" }; if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }; New-Item -ItemType Directory -Path $target | Out-Null; if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }; git archive --format=zip -o $archive HEAD; Expand-Archive -LiteralPath $archive -DestinationPath $target -Force; Remove-Item -LiteralPath $archive -Force; Write-Output \"exported=$target\""
```

Commit and push the upload branch:

```powershell
git -C .github-mf26-upload add MF-26_Data_Logger
git -C .github-mf26-upload commit -m "Update MF-26 data logger analyzer"
git -C .github-mf26-upload push origin codex/mf-26-data-logger-import
```

Expected: local branch contains implementation commits, upload branch contains updated `MF-26_Data_Logger`, and both pushes succeed.

## Self-Review

- Spec coverage: Task 1 covers `.mflogroute`; Tasks 3-4 cover GPS Map overlay, edit, start/end, save/load, and properties; Task 5 covers gauge indicators; Task 6 covers tire temperature; Task 7 covers docs, full tests, EXE, and GitHub upload.
- Placeholder scan: this plan avoids unspecified task labels and includes concrete tests, code snippets, commands, and expected outcomes.
- Type consistency: `ReferenceRoute`, `ReferenceRoutePoint`, `GPSMapWindow.set_reference_route`, `GaugeIndicatorsWindow`, and `TireTemperatureWindow` names are consistent across tasks.
