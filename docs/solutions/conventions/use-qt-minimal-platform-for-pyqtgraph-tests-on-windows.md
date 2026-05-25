---
title: "Use Qt minimal platform for pyqtgraph tests on Windows"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "prototype.tests"
tags:
  - "PySide6"
  - "pyqtgraph"
  - "pytest"
  - "windows"
---

# Use Qt Minimal Platform For Pyqtgraph Tests On Windows

## Context

PySide6/pyqtgraph UI tests intermittently crashed on Windows while using
`QT_QPA_PLATFORM=offscreen`. The Python process exited with a native access
violation during `pyqtgraph.widgets.GraphicsView.paintEvent`, which left a
Windows `python.exe` application error dialog on the user's desktop.

## Guidance

Use Qt's `minimal` platform for pytest-based UI tests on Windows. Reserve
`offscreen` for explicit screenshot smoke scripts where `QWidget.grab()` output
is needed.

```python
# prototype/tests/conftest.py
import os

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
```

Keep Korean font discovery explicit so UI tests and screenshots render labels
consistently:

```powershell
$env:QT_QPA_PLATFORM='minimal'
$env:QT_QPA_FONTDIR='C:\Windows\Fonts'
.\.venv\Scripts\python -m pytest tests
```

## Why This Matters

The crash is below Python exception handling, so pytest cannot report it cleanly
and Windows may show a modal error dialog. That makes unattended test runs
unpleasant and can block long autonomous implementation sessions.

## When to Apply

Apply this to pytest/pytest-qt tests that instantiate pyqtgraph widgets on
Windows. If a test must verify actual image pixels, run that smoke test in a
separate process with `offscreen` and keep it outside the normal test teardown
path.
