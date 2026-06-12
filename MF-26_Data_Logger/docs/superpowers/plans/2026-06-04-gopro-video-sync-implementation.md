# GoPro Video Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Video Sync` analysis window that loads one GoPro/MP4 video and keeps it synchronized with CSV playback through a manual millisecond offset.

**Architecture:** Keep `PlaybackState.current_time_ms` as the single clock. Add a testable video backend boundary so unit tests can verify sync math without relying on OS codecs, while production uses `QMediaPlayer` and `QVideoWidget`. Persist video path, offset, and mute state in `.mflogproj`, and expose controls in the selected-window right properties panel.

**Tech Stack:** Python 3.12, PySide6 `QtMultimedia` / `QtMultimediaWidgets`, existing `PlaybackState`, existing PySide6 MDI shell, pytest, pytest-qt.

---

## File Structure

- Modify `prototype/src/mflog_proto/persistence/project_state.py`
  - Add `video_path`, `video_offset_ms`, and `video_muted` fields to `ProjectState`.
- Modify `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
  - Add `_VideoBackend`, `_QtMediaVideoBackend`, `_FakeVideoBackend`-compatible behavior, and `VideoSyncWindow`.
- Modify `prototype/src/mflog_proto/ui/main_window.py`
  - Register `Video Sync`, build the window, add right properties controls, propagate path/offset/mute to open windows, and persist/restore state.
- Modify `prototype/tests/test_project_state.py`
  - Cover video project state round-trip and legacy defaults.
- Modify `prototype/tests/test_minimal_analysis_windows.py`
  - Cover deterministic video sync math, offset changes, playback follow, play/pause, and missing-file warning.
- Modify `prototype/tests/test_ui_shell.py`
  - Cover sidebar creation, properties controls, project capture/restore, and missing video restore.
- Modify `docs/ACCEPTANCE_TEST_KO.md`
  - Add manual GoPro/MP4 video sync acceptance checks.

## Task 1: Project State Persistence

**Files:**
- Modify: `prototype/src/mflog_proto/persistence/project_state.py`
- Modify: `prototype/tests/test_project_state.py`

- [ ] **Step 1: Write failing persistence tests**

Add video fields to the existing round-trip `ProjectState(...)` construction in `prototype/tests/test_project_state.py`:

```python
        video_path=Path("videos/endurance_gopro.mp4"),
        video_offset_ms=-1250,
        video_muted=False,
```

Add assertions after restore:

```python
    assert restored.video_path == Path("videos/endurance_gopro.mp4")
    assert restored.video_offset_ms == -1250
    assert restored.video_muted is False
```

Add assertions to the legacy/defaults test:

```python
    assert restored.video_path is None
    assert restored.video_offset_ms == 0
    assert restored.video_muted is True
```

- [ ] **Step 2: Run the focused project state tests and verify failure**

Run:

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer\prototype
.\.venv\Scripts\python.exe -m pytest tests\test_project_state.py -v
```

Expected: failure because `ProjectState` does not accept `video_path`, `video_offset_ms`, or `video_muted`.

- [ ] **Step 3: Add video fields to `ProjectState`**

In `prototype/src/mflog_proto/persistence/project_state.py`, add fields after `reference_route_name`:

```python
    video_path: Path | None = None
    video_offset_ms: int = 0
    video_muted: bool = True
```

Add these keys to `to_dict()` after `reference_route_name`:

```python
            "video_path": None if self.video_path is None else str(self.video_path),
            "video_offset_ms": self.video_offset_ms,
            "video_muted": self.video_muted,
```

Add `video_path = data.get("video_path")` next to the other path reads in `from_dict()`, then add these constructor arguments:

```python
            video_path=None if video_path in (None, "") else Path(str(video_path)),
            video_offset_ms=int(data.get("video_offset_ms", 0)),
            video_muted=bool(data.get("video_muted", True)),
```

- [ ] **Step 4: Run project state tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_project_state.py -v
```

Expected: all project state tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add prototype/src/mflog_proto/persistence/project_state.py prototype/tests/test_project_state.py
git commit -m "feat: persist video sync state"
```

## Task 2: Testable Video Sync Window

**Files:**
- Modify: `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`
- Modify: `prototype/tests/test_minimal_analysis_windows.py`

- [ ] **Step 1: Write failing deterministic sync tests**

Add imports in `prototype/tests/test_minimal_analysis_windows.py`:

```python
from pathlib import Path
from mflog_proto.ui.minimal_analysis_windows import VideoSyncWindow
```

If `Path` is already imported, only add `VideoSyncWindow`.

Add this fake backend class near the existing fake test helpers:

```python
class FakeVideoBackend:
    def __init__(self, *, duration_ms=10_000):
        self.duration_ms = duration_ms
        self.position_ms = 0
        self.playback_rate = 1.0
        self.muted = True
        self.play_called = 0
        self.pause_called = 0
        self.source_path = None
        self.error_text = ""

    def set_video_output(self, _video_widget):
        self.video_output_set = True

    def set_source(self, path):
        self.source_path = path

    def clear_source(self):
        self.source_path = None

    def set_position(self, position_ms):
        self.position_ms = int(position_ms)

    def play(self):
        self.play_called += 1

    def pause(self):
        self.pause_called += 1

    def set_muted(self, muted):
        self.muted = bool(muted)

    def set_playback_rate(self, rate):
        self.playback_rate = float(rate)
```

Add tests:

```python
def test_video_sync_window_seeks_backend_from_playback_time_and_offset(qtbot):
    playback = PlaybackState(timestamps=[0.0, 1.0, 2.0, 3.0])
    backend = FakeVideoBackend(duration_ms=5_000)
    window = VideoSyncWindow(
        playback,
        video_path=Path("drive.mp4"),
        video_offset_ms=250,
        backend=backend,
    )
    qtbot.addWidget(window)

    playback.set_time_ms(2_000)

    assert window.video_path() == Path("drive.mp4")
    assert window.video_offset_ms() == 250
    assert window.target_video_time_ms() == 2250
    assert backend.position_ms == 2250
    assert window.status_text() == "Video: drive.mp4 | CSV 2.000 s | Video 2.250 s | Offset +250 ms"
```

```python
def test_video_sync_window_clamps_target_time_and_updates_offset(qtbot):
    playback = PlaybackState(timestamps=[0.0, 1.0, 2.0])
    backend = FakeVideoBackend(duration_ms=1_500)
    window = VideoSyncWindow(
        playback,
        video_path=Path("drive.mp4"),
        video_offset_ms=-500,
        backend=backend,
    )
    qtbot.addWidget(window)

    playback.set_time_ms(0)
    assert window.target_video_time_ms() == 0
    assert backend.position_ms == 0

    window.set_video_offset_ms(1_000)
    playback.set_time_ms(1_000)

    assert window.target_video_time_ms() == 1500
    assert backend.position_ms == 1500
```

```python
def test_video_sync_window_follows_play_pause_speed_and_mute(qtbot):
    playback = PlaybackState(timestamps=[0.0, 1.0])
    backend = FakeVideoBackend()
    window = VideoSyncWindow(playback, video_path=Path("drive.mp4"), backend=backend)
    qtbot.addWidget(window)

    playback.set_speed(2.0)
    playback.play()
    window.set_video_muted(False)
    playback.pause()

    assert backend.playback_rate == 2.0
    assert backend.play_called == 1
    assert backend.muted is False
    assert backend.pause_called == 1
```

```python
def test_video_sync_window_keeps_warning_for_missing_video_file(qtbot, tmp_path):
    playback = PlaybackState(timestamps=[0.0, 1.0])
    missing = tmp_path / "missing.mp4"
    backend = FakeVideoBackend()
    window = VideoSyncWindow(playback, video_path=missing, backend=backend)
    qtbot.addWidget(window)

    assert "missing" in window.status_text().lower()
    assert backend.source_path is None
```

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_minimal_analysis_windows.py::test_video_sync_window_seeks_backend_from_playback_time_and_offset tests\test_minimal_analysis_windows.py::test_video_sync_window_clamps_target_time_and_updates_offset tests\test_minimal_analysis_windows.py::test_video_sync_window_follows_play_pause_speed_and_mute tests\test_minimal_analysis_windows.py::test_video_sync_window_keeps_warning_for_missing_video_file -v
```

Expected: import failure because `VideoSyncWindow` does not exist.

- [ ] **Step 3: Add Qt Multimedia imports and backend wrapper**

In `prototype/src/mflog_proto/ui/minimal_analysis_windows.py`, extend the PySide6 import:

```python
from PySide6 import QtCore, QtGui, QtMultimedia, QtMultimediaWidgets, QtWidgets
```

Add this class before `CurrentValuesWindow`:

```python
class _QtMediaVideoBackend(QtCore.QObject):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QtMultimedia.QMediaPlayer(self)

    @property
    def duration_ms(self) -> int:
        return int(self._player.duration())

    @property
    def position_ms(self) -> int:
        return int(self._player.position())

    @property
    def error_text(self) -> str:
        return self._player.errorString()

    def set_video_output(self, video_widget: QtMultimediaWidgets.QVideoWidget) -> None:
        self._player.setVideoOutput(video_widget)

    def set_source(self, path: Path) -> None:
        self._player.setSource(QtCore.QUrl.fromLocalFile(str(path)))

    def clear_source(self) -> None:
        self._player.setSource(QtCore.QUrl())

    def set_position(self, position_ms: int) -> None:
        self._player.setPosition(max(0, int(position_ms)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def set_muted(self, muted: bool) -> None:
        self._player.audioOutput().setMuted(bool(muted)) if self._player.audioOutput() else None

    def set_playback_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(float(rate))
```

If `audioOutput()` is unavailable or returns `None` in the installed PySide6 version, replace `set_muted()` in the implementation with an owned `QtMultimedia.QAudioOutput`:

```python
self._audio_output = QtMultimedia.QAudioOutput(self)
self._player.setAudioOutput(self._audio_output)
```

and:

```python
self._audio_output.setMuted(bool(muted))
```

- [ ] **Step 4: Implement `VideoSyncWindow`**

Add this class after `_QtMediaVideoBackend`:

```python
class VideoSyncWindow(QtWidgets.QWidget):
    def __init__(
        self,
        playback_state: PlaybackState,
        *,
        video_path: Path | None = None,
        video_offset_ms: int = 0,
        video_muted: bool = True,
        backend: object | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("videoSyncWindow")
        self._playback_state = playback_state
        self._video_path: Path | None = None
        self._video_offset_ms = int(video_offset_ms)
        self._video_muted = bool(video_muted)
        self._warning_text = ""
        self._backend = backend if backend is not None else _QtMediaVideoBackend(self)
        self._unsubscribe = playback_state.subscribe(self._handle_cursor_event)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        self.video_widget.setObjectName("videoSyncVideoWidget")
        self.video_widget.setMinimumSize(320, 180)
        self.video_widget.setStyleSheet("background: #11171b; border: 1px solid #53616b;")
        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("videoSyncStatusLabel")
        self.status_label.setWordWrap(True)
        self.offset_spin = QtWidgets.QSpinBox()
        self.offset_spin.setObjectName("videoSyncOffsetSpin")
        self.offset_spin.setRange(-3_600_000, 3_600_000)
        self.offset_spin.setSuffix(" ms")
        self.offset_spin.setValue(self._video_offset_ms)
        self.offset_spin.valueChanged.connect(self.set_video_offset_ms)
        control_row = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton("Load Video...")
        self.load_button.setObjectName("videoSyncLoadButton")
        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.setObjectName("videoSyncClearButton")
        self.mute_checkbox = QtWidgets.QCheckBox("Mute")
        self.mute_checkbox.setObjectName("videoSyncMuteCheckbox")
        self.mute_checkbox.setChecked(self._video_muted)
        self.mute_checkbox.toggled.connect(self.set_video_muted)
        for delta in (-1000, -100, 100, 1000):
            button = QtWidgets.QPushButton(f"{delta:+d}")
            button.setObjectName(f"videoSyncNudge{delta:+d}Button")
            button.clicked.connect(lambda _checked=False, value=delta: self.nudge_video_offset(value))
            control_row.addWidget(button)
        control_row.addWidget(self.offset_spin)
        control_row.addWidget(self.mute_checkbox)
        control_row.addStretch(1)
        control_row.addWidget(self.load_button)
        control_row.addWidget(self.clear_button)
        layout.addWidget(self.video_widget, 1)
        layout.addLayout(control_row)
        layout.addWidget(self.status_label)

        if hasattr(self._backend, "set_video_output"):
            self._backend.set_video_output(self.video_widget)
        if hasattr(self._backend, "set_muted"):
            self._backend.set_muted(self._video_muted)
        if video_path is not None:
            self.set_video_path(video_path)
        else:
            self._refresh_sync()

    def video_path(self) -> Path | None:
        return self._video_path

    def video_offset_ms(self) -> int:
        return self._video_offset_ms

    def video_muted(self) -> bool:
        return self._video_muted

    def target_video_time_ms(self) -> int:
        raw = self._playback_state.current_time_ms + self._video_offset_ms
        duration = int(getattr(self._backend, "duration_ms", 0) or 0)
        lower_clamped = max(0, raw)
        return min(lower_clamped, duration) if duration > 0 else lower_clamped

    def status_text(self) -> str:
        return self.status_label.text()

    def set_video_path(self, path: Path | str | None) -> None:
        self._warning_text = ""
        if path in (None, ""):
            self._video_path = None
            if hasattr(self._backend, "clear_source"):
                self._backend.clear_source()
            self._refresh_sync()
            return
        candidate = Path(path)
        self._video_path = candidate
        if not candidate.exists():
            self._warning_text = f"Video missing: {candidate}"
            self._refresh_sync()
            return
        if hasattr(self._backend, "set_source"):
            self._backend.set_source(candidate)
        self._refresh_sync()

    def set_video_offset_ms(self, offset_ms: int) -> None:
        self._video_offset_ms = int(offset_ms)
        if self.offset_spin.value() != self._video_offset_ms:
            self.offset_spin.blockSignals(True)
            self.offset_spin.setValue(self._video_offset_ms)
            self.offset_spin.blockSignals(False)
        self._refresh_sync()

    def nudge_video_offset(self, delta_ms: int) -> None:
        self.set_video_offset_ms(self._video_offset_ms + int(delta_ms))

    def set_video_muted(self, muted: bool) -> None:
        self._video_muted = bool(muted)
        if self.mute_checkbox.isChecked() != self._video_muted:
            self.mute_checkbox.blockSignals(True)
            self.mute_checkbox.setChecked(self._video_muted)
            self.mute_checkbox.blockSignals(False)
        if hasattr(self._backend, "set_muted"):
            self._backend.set_muted(self._video_muted)
        self._refresh_status()

    def dispose(self) -> None:
        self._unsubscribe()
        if hasattr(self._backend, "pause"):
            self._backend.pause()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.dispose()
        super().closeEvent(event)

    def _handle_cursor_event(self, event: CursorEvent) -> None:
        if event.kind is not CursorKind.PLAYBACK:
            return
        self._refresh_sync()
        if hasattr(self._backend, "set_playback_rate"):
            self._backend.set_playback_rate(self._playback_state.playback_speed)
        if self._playback_state.is_playing:
            if hasattr(self._backend, "play"):
                self._backend.play()
        elif hasattr(self._backend, "pause"):
            self._backend.pause()

    def _refresh_sync(self) -> None:
        if self._video_path is not None and not self._warning_text and hasattr(self._backend, "set_position"):
            self._backend.set_position(self.target_video_time_ms())
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._warning_text:
            self.status_label.setText(self._warning_text)
            return
        name = "-" if self._video_path is None else self._video_path.name
        self.status_label.setText(
            f"Video: {name} | CSV {_format_seconds(self._playback_state.current_time_ms)} | "
            f"Video {_format_seconds(self.target_video_time_ms())} | "
            f"Offset {self._video_offset_ms:+d} ms"
        )
```

- [ ] **Step 5: Run focused window tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_minimal_analysis_windows.py::test_video_sync_window_seeks_backend_from_playback_time_and_offset tests\test_minimal_analysis_windows.py::test_video_sync_window_clamps_target_time_and_updates_offset tests\test_minimal_analysis_windows.py::test_video_sync_window_follows_play_pause_speed_and_mute tests\test_minimal_analysis_windows.py::test_video_sync_window_keeps_warning_for_missing_video_file -v
```

Expected: all four tests pass.

- [ ] **Step 6: Commit Task 2**

Run:

```powershell
git add prototype/src/mflog_proto/ui/minimal_analysis_windows.py prototype/tests/test_minimal_analysis_windows.py
git commit -m "feat: add video sync window"
```

## Task 3: MainWindow Registration and Controls

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Modify: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write failing shell integration tests**

Add `VideoSyncWindow` to the imports from `mflog_proto.ui.minimal_analysis_windows`.

Add:

```python
def test_left_sidebar_adds_video_sync_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    video_window = window.add_analysis_window("Video Sync").widget()

    assert "Video Sync" in window.sidebar_item_titles("시각화")
    assert isinstance(video_window, VideoSyncWindow)
    assert video_window.video_offset_ms() == 0
```

Add:

```python
def test_right_properties_configure_video_sync_for_open_and_new_windows(qtbot, tmp_path):
    path = tmp_path / "drive.mp4"
    path.write_bytes(b"not a real video but exists")
    window = MainWindow()
    qtbot.addWidget(window)

    first = window.add_analysis_window("Video Sync").widget()
    window.load_video_sync_path(path)
    window.video_sync_offset_spin.setValue(750)
    window.video_sync_mute_checkbox.setChecked(False)

    second = window.add_analysis_window("Video Sync").widget()

    assert first.video_path() == path
    assert first.video_offset_ms() == 750
    assert first.video_muted() is False
    assert second.video_path() == path
    assert second.video_offset_ms() == 750
    assert second.video_muted() is False
```

- [ ] **Step 2: Run focused shell tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_shell.py::test_left_sidebar_adds_video_sync_window tests\test_ui_shell.py::test_right_properties_configure_video_sync_for_open_and_new_windows -v
```

Expected: import or attribute failures because `Video Sync` is not registered.

- [ ] **Step 3: Register `VideoSyncWindow`**

In `prototype/src/mflog_proto/ui/main_window.py`, add `VideoSyncWindow` to the `minimal_analysis_windows` import list.

Add `"Video Sync"` to `DEFAULT_ANALYSIS_ITEMS` after `"Tire Temperature"`.

Add `"Video Sync"` to the visualization tuple in `SIDEBAR_GROUPS` after `"Tire Temperature"`.

Add instance state in `MainWindow.__init__` after reference route state:

```python
        self.video_path: Path | None = None
        self.video_offset_ms = 0
        self.video_muted = True
```

Add builder near `_build_gauge_indicators_window`:

```python
    def _build_video_sync_window(self) -> VideoSyncWindow:
        widget = VideoSyncWindow(
            self.playback_state,
            video_path=self.video_path,
            video_offset_ms=self.video_offset_ms,
            video_muted=self.video_muted,
        )
        widget.load_button.clicked.connect(self._open_video_sync_dialog)
        widget.clear_button.clicked.connect(self.clear_video_sync)
        widget.offset_spin.valueChanged.connect(self.set_video_sync_offset_ms)
        widget.mute_checkbox.toggled.connect(self.set_video_sync_muted)
        return widget
```

Add to `add_analysis_window`:

```python
        elif title == "Video Sync":
            widget = self._build_video_sync_window()
```

Add to `_default_analysis_window_size`:

```python
        if title == "Video Sync":
            return QtCore.QSize(620, 420)
```

- [ ] **Step 4: Add right properties controls and sync methods**

In `_build_right_properties_panel`, add controls near vehicle controls:

```python
        self.video_sync_path_edit = QtWidgets.QLineEdit()
        self.video_sync_path_edit.setObjectName("videoSyncPathEdit")
        self.video_sync_path_edit.setReadOnly(True)
        self.video_sync_load_button = QtWidgets.QPushButton("Load Video...")
        self.video_sync_load_button.setObjectName("videoSyncLoadButton")
        self.video_sync_load_button.clicked.connect(self._open_video_sync_dialog)
        self.video_sync_clear_button = QtWidgets.QPushButton("Clear")
        self.video_sync_clear_button.setObjectName("videoSyncClearButton")
        self.video_sync_clear_button.clicked.connect(self.clear_video_sync)
        self.video_sync_offset_spin = QtWidgets.QSpinBox()
        self.video_sync_offset_spin.setObjectName("videoSyncOffsetSpin")
        self.video_sync_offset_spin.setRange(-3_600_000, 3_600_000)
        self.video_sync_offset_spin.setSuffix(" ms")
        self.video_sync_offset_spin.valueChanged.connect(self.set_video_sync_offset_ms)
        self.video_sync_mute_checkbox = QtWidgets.QCheckBox("Mute")
        self.video_sync_mute_checkbox.setObjectName("videoSyncMuteCheckbox")
        self.video_sync_mute_checkbox.setChecked(self.video_muted)
        self.video_sync_mute_checkbox.toggled.connect(self.set_video_sync_muted)
        self.video_sync_status_label = QtWidgets.QLabel("No video loaded")
        self.video_sync_status_label.setObjectName("videoSyncStatusLabel")
        self.video_sync_status_label.setWordWrap(True)
```

Add a properties page:

```python
        self.video_sync_properties_page = self._make_properties_page(
            "videoSyncPropertiesPage",
            (
                ("Video file", self.video_sync_path_edit),
                ("Load", self.video_sync_load_button),
                ("Clear", self.video_sync_clear_button),
                ("Offset", self.video_sync_offset_spin),
                ("Audio", self.video_sync_mute_checkbox),
                ("Status", self.video_sync_status_label),
            ),
        )
```

Add this page to `self.properties_stack`.

Add methods near vehicle/reference sync methods:

```python
    def load_video_sync_path(self, path: Path | str) -> None:
        self.video_path = Path(path)
        self._apply_video_sync_to_open_windows()
        self._sync_video_sync_controls()

    def clear_video_sync(self) -> None:
        self.video_path = None
        self._apply_video_sync_to_open_windows()
        self._sync_video_sync_controls()

    def set_video_sync_offset_ms(self, offset_ms: int) -> None:
        self.video_offset_ms = int(offset_ms)
        self._apply_video_sync_to_open_windows()
        self._sync_video_sync_controls()

    def set_video_sync_muted(self, muted: bool) -> None:
        self.video_muted = bool(muted)
        self._apply_video_sync_to_open_windows()
        self._sync_video_sync_controls()

    def _open_video_sync_dialog(self) -> None:
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load video",
            str(Path.cwd()),
            "Video files (*.mp4 *.mov *.m4v *.avi);;All files (*.*)",
        )
        if path:
            self.load_video_sync_path(path)

    def _apply_video_sync_to_open_windows(self) -> None:
        for sub_window in self.workspace.subWindowList():
            widget = sub_window.widget()
            if isinstance(widget, VideoSyncWindow):
                widget.set_video_path(self.video_path)
                widget.set_video_offset_ms(self.video_offset_ms)
                widget.set_video_muted(self.video_muted)

    def _sync_video_sync_controls(self) -> None:
        if not hasattr(self, "video_sync_path_edit"):
            return
        self.video_sync_path_edit.setText("" if self.video_path is None else str(self.video_path))
        self.video_sync_offset_spin.blockSignals(True)
        self.video_sync_offset_spin.setValue(self.video_offset_ms)
        self.video_sync_offset_spin.blockSignals(False)
        self.video_sync_mute_checkbox.blockSignals(True)
        self.video_sync_mute_checkbox.setChecked(self.video_muted)
        self.video_sync_mute_checkbox.blockSignals(False)
        self.video_sync_status_label.setText(
            "No video loaded" if self.video_path is None else f"Video: {self.video_path.name}"
        )
```

In `_update_properties_for_active_window`, add `VideoSyncWindow` routing:

```python
        elif isinstance(widget, VideoSyncWindow):
            self.properties_stack.setCurrentWidget(self.video_sync_properties_page)
            self._sync_video_sync_controls()
```

- [ ] **Step 5: Run focused shell tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_shell.py::test_left_sidebar_adds_video_sync_window tests\test_ui_shell.py::test_right_properties_configure_video_sync_for_open_and_new_windows -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add prototype/src/mflog_proto/ui/main_window.py prototype/tests/test_ui_shell.py
git commit -m "feat: wire video sync controls"
```

## Task 4: Project Capture/Restore Integration

**Files:**
- Modify: `prototype/src/mflog_proto/ui/main_window.py`
- Modify: `prototype/tests/test_ui_shell.py`

- [ ] **Step 1: Write failing project integration tests**

Add:

```python
def test_main_window_captures_video_sync_project_state(qtbot, tmp_path):
    video_path = tmp_path / "drive.mp4"
    video_path.write_bytes(b"placeholder")
    window = MainWindow()
    qtbot.addWidget(window)

    window.load_video_sync_path(video_path)
    window.set_video_sync_offset_ms(-400)
    window.set_video_sync_muted(False)
    state = window.capture_project_state()

    assert state.video_path == video_path
    assert state.video_offset_ms == -400
    assert state.video_muted is False
```

Add:

```python
def test_main_window_restores_video_sync_project_state_for_new_windows(qtbot, tmp_path):
    video_path = tmp_path / "drive.mp4"
    video_path.write_bytes(b"placeholder")
    state = ProjectState(
        video_path=video_path,
        video_offset_ms=900,
        video_muted=False,
        open_windows=(WindowState(title="Video Sync", x=10, y=20, width=500, height=320),),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.restore_project_state(state)
    video_window = window.workspace.subWindowList()[0].widget()

    assert isinstance(video_window, VideoSyncWindow)
    assert video_window.video_path() == video_path
    assert video_window.video_offset_ms() == 900
    assert video_window.video_muted() is False
```

Add:

```python
def test_main_window_restores_missing_video_without_blocking_project(qtbot, tmp_path):
    missing = tmp_path / "missing.mp4"
    state = ProjectState(
        video_path=missing,
        video_offset_ms=500,
        open_windows=(WindowState(title="Video Sync", x=0, y=0, width=500, height=320),),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    window.restore_project_state(state)
    video_window = window.workspace.subWindowList()[0].widget()

    assert isinstance(video_window, VideoSyncWindow)
    assert video_window.video_path() == missing
    assert video_window.video_offset_ms() == 500
    assert "missing" in video_window.status_text().lower()
```

- [ ] **Step 2: Run focused restore tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_shell.py::test_main_window_captures_video_sync_project_state tests\test_ui_shell.py::test_main_window_restores_video_sync_project_state_for_new_windows tests\test_ui_shell.py::test_main_window_restores_missing_video_without_blocking_project -v
```

Expected: capture/restore assertions fail until `MainWindow` is wired.

- [ ] **Step 3: Wire capture and restore**

In `capture_project_state()`, add:

```python
            video_path=self.video_path,
            video_offset_ms=self.video_offset_ms,
            video_muted=self.video_muted,
```

In `restore_project_state()`, add after reference route restore:

```python
        self.video_path = state.video_path
        self.video_offset_ms = state.video_offset_ms
        self.video_muted = state.video_muted
        self._sync_video_sync_controls()
```

The missing-file warning is handled inside `VideoSyncWindow.set_video_path()`, so do not block project restore.

- [ ] **Step 4: Run focused restore tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ui_shell.py::test_main_window_captures_video_sync_project_state tests\test_ui_shell.py::test_main_window_restores_video_sync_project_state_for_new_windows tests\test_ui_shell.py::test_main_window_restores_missing_video_without_blocking_project -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add prototype/src/mflog_proto/ui/main_window.py prototype/tests/test_ui_shell.py
git commit -m "feat: persist video sync in project state"
```

## Task 5: Acceptance Docs, Verification, Packaging

**Files:**
- Modify: `docs/ACCEPTANCE_TEST_KO.md`

- [ ] **Step 1: Update Korean acceptance test document**

Add this block near the GPS/3D/additional visualization checks:

```markdown
추가 GoPro / 주행 영상 싱크 확인:

- 좌측 분석 패널의 시각화 그룹에서 `Video Sync` 창을 추가할 수 있어야 합니다.
- `Load Video...`로 GoPro/MP4 영상을 선택하면 영상 viewport와 파일명, CSV 시간,
  영상 시간, offset 상태가 표시되어야 합니다.
- 하단 CSV 재생 바를 드래그하거나 이벤트로 이동하면 영상 위치도
  `CSV 시간 + offset`에 맞춰 이동해야 합니다.
- offset spin box 또는 nudge 버튼으로 ms 단위 오프셋을 조정하면 즉시 영상
  위치와 상태 표시가 갱신되어야 합니다.
- `.mflogproj` 저장/열기 후 영상 경로, offset, mute 상태가 복원되어야 합니다.
- 영상 파일이 삭제되거나 이동되어도 프로젝트는 열리고, `Video Sync` 창에는
  경고만 표시되며 CSV 재생은 계속 사용할 수 있어야 합니다.
```

- [ ] **Step 2: Run focused suites**

Run:

```powershell
cd C:\Users\hacki\Desktop\03_workspace\01_MF-26\03_DataAnalyzer\prototype
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
.\.venv\Scripts\python.exe -m pytest tests\test_project_state.py tests\test_minimal_analysis_windows.py tests\test_ui_shell.py -v
```

Expected: all selected tests pass.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Build EXE**

Run:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

Expected: build completes and this file exists:

```text
prototype\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe
```

- [ ] **Step 5: Smoke run EXE**

Run with escalation because it launches a GUI process:

```powershell
$exe = (Resolve-Path '.\dist\MF-LOG-ANALYZER-v2\MF-LOG-ANALYZER-v2.exe').Path
$proc = Start-Process -FilePath $exe -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 5
$alive = -not $proc.HasExited
if ($alive) { Stop-Process -Id $proc.Id -Force }
Write-Output "alive_after_5s=$alive"
```

Expected: `alive_after_5s=True`.

- [ ] **Step 6: Commit docs and any verification fixes**

Run:

```powershell
git add docs/ACCEPTANCE_TEST_KO.md
git commit -m "docs: add video sync acceptance checks"
```

If verification required code fixes, include only those related files in the final commit and use:

```powershell
git commit -m "fix: stabilize video sync integration"
```

## Task 6: GitHub Upload

**Files:**
- No source edits expected.

- [ ] **Step 1: Push feature branch**

Run:

```powershell
git push origin codex/gopro-video-sync
```

- [ ] **Step 2: Refresh upload worktree**

Run:

```powershell
git worktree add .github-mf26-upload codex/mf-26-data-logger-import
```

If the worktree already exists, use the existing folder only after `git -C .github-mf26-upload status --short` is clean.

- [ ] **Step 3: Export current committed tree into `MF-26_Data_Logger`**

Run:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command '$root = (Resolve-Path ''.'').Path; $worktree = (Resolve-Path ''.\.github-mf26-upload'').Path; $target = Join-Path $worktree ''MF-26_Data_Logger''; $archive = Join-Path $env:TEMP ''mflog_data_logger_export.zip''; if (-not $worktree.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Unexpected worktree path: $worktree" }; if (-not $target.StartsWith($worktree, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Unexpected target path: $target" }; if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }; New-Item -ItemType Directory -Path $target | Out-Null; if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }; git archive --format=zip -o $archive HEAD; Expand-Archive -LiteralPath $archive -DestinationPath $target -Force; Remove-Item -LiteralPath $archive -Force; Write-Output "exported=$target"'
```

- [ ] **Step 4: Commit and push upload branch**

Run:

```powershell
git -C .github-mf26-upload add MF-26_Data_Logger
git -C .github-mf26-upload commit -m "Update MF-26 data logger analyzer"
git -C .github-mf26-upload push origin codex/mf-26-data-logger-import
git worktree remove .github-mf26-upload
```

Expected: feature branch and upload branch are both pushed.

## Self-Review

- Spec coverage: Tasks 1 and 4 cover persistence; Task 2 covers video sync math, play/pause, mute, and missing-file warning; Task 3 covers sidebar and right-panel controls; Task 5 covers docs, tests, build, and EXE smoke; Task 6 covers GitHub upload.
- Placeholder scan: no placeholder tokens or deferred-detail steps are present. Each implementation task includes concrete tests, code snippets, and commands.
- Type consistency: `video_path`, `video_offset_ms`, `video_muted`, `VideoSyncWindow`, `set_video_path`, `set_video_offset_ms`, and `set_video_muted` are used consistently across state, UI, tests, and persistence.
