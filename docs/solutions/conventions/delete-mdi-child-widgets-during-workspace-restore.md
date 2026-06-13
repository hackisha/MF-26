---
title: "Delete MDI child widgets during workspace restore"
date: "2026-05-25"
last_updated: "2026-06-13"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "PySide6"
  - "QMdiArea"
  - "pyqtgraph"
  - "workspace-restore"
---

# Delete MDI Child Widgets During Workspace Restore

## Context

Workspace restore clears existing analysis windows before recreating the saved
layout. A first implementation called `removeSubWindow()` and closed the
`QMdiSubWindow`, but the child analysis widget could remain alive with no parent.
For pyqtgraph windows this leaves native scene/plot resources around and can
accumulate across repeated restore operations.

## Guidance

When clearing an MDI workspace, dispose application-level subscriptions first,
then schedule both the child widget and the MDI subwindow for Qt deferred
deletion.

```python
for sub_window in list(self.workspace.subWindowList()):
    widget = sub_window.widget()
    if widget is not None:
        _dispose_widget(widget)
        widget.hide()
        widget.setParent(None)
        widget.deleteLater()
    self.workspace.removeSubWindow(sub_window)
    sub_window.hide()
    sub_window.deleteLater()
```

Add a regression test that flushes deferred deletes and checks the old wrapper is
invalid:

```python
old_widget = window.workspace.subWindowList()[0].widget()
window.restore_project_state(state)
QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
QtWidgets.QApplication.processEvents()

assert not shiboken6.isValid(old_widget)
```

If an MDI child owns helper controllers that schedule delayed UI work, guard
those callbacks with `shiboken6.isValid(...)` before touching the subwindow or
content widget. Workspace restore can delete the native C++ object before a
queued geometry/update callback runs.

For pyqtgraph-backed widgets, `dispose()` should also stop future paint work
before clearing plot items or disconnecting scene signals. Long pytest runs can
leave a queued `GraphicsView.paintEvent`; if plot items are removed while that
paint is still possible, Windows may raise a native access violation or a
`ViewBox already deleted` teardown error.

```python
def dispose(self) -> None:
    if self._disposed:
        return
    self._disposed = True
    self.plot.setUpdatesEnabled(False)
    self.plot.viewport().setUpdatesEnabled(False)
    self.plot.hide()
    self.plot.scene().sigMouseMoved.disconnect(self._handle_mouse_moved)
    self.plot.clear()
```

Wrap Qt disconnect/clear operations in `try/except RuntimeError` for idempotent
dispose paths, because close events, explicit test cleanup, and workspace
restore can all race to clean the same native widget.

## Why This Matters

Playback subscriber cleanup only handles Python-level event fanout. It does not
destroy Qt/pyqtgraph C++ objects. Workspace restore touches many analysis
windows, so leaked child widgets can create memory growth, stale paint events,
or native crashes later in a test or app session.

## When to Apply

Apply this when replacing, closing, restoring, or bulk-clearing MDI/dock
analysis windows. Any widget that owns Qt scenes, plots, OpenGL resources, file
watchers, timers, or playback subscriptions should have a `dispose()` path plus
Qt deferred deletion.
