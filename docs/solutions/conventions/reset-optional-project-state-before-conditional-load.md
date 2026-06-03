---
title: "Reset optional project state before conditional load"
date: "2026-06-04"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "PySide6"
  - "project-restore"
  - "optional-state"
  - "reference-route"
---

# Reset Optional Project State Before Conditional Load

## Context

`MainWindow.restore_project_state()` restores optional project-owned state such
as reference routes. A reviewed implementation renamed the current
`ReferenceRoute` when a saved route path was missing, but accidentally preserved
the old route points from the previous project.

## Guidance

When a project state field points to an optional external artifact, restore from
the artifact only if it exists and loads. If it is absent or missing, create a
fresh empty domain object from the saved metadata instead of mutating or
renaming the previous in-memory object.

```python
if state.reference_route_path is not None and state.reference_route_path.exists():
    self.load_reference_route_path(state.reference_route_path)
else:
    self.set_reference_route(
        ReferenceRoute(
            name=state.reference_route_name or "Reference route",
            points=(),
        )
    )
```

Add regression coverage that starts with non-empty old state, restores a project
with no artifact, and checks both the main state and any open/new analysis
windows show zero reference points.

## Why This Matters

Project restore crosses session boundaries. Reusing an old optional object can
silently leak data from one project into another, especially when only metadata
such as a display name is present. Empty fallback objects make the absence of an
external artifact explicit and keep UI windows synchronized with the restored
project.

## When to Apply

Apply this pattern when restoring any project setting backed by an optional file,
cache, external asset, or derived object. The fallback path should reset the
whole domain object, not partially edit the prior one.
