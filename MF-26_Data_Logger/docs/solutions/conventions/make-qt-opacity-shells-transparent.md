---
title: "Make Qt opacity shells transparent"
date: "2026-06-14"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "qt"
  - "ui"
  - "opacity"
  - "mdi"
  - "transparency"
---

# Make Qt Opacity Shells Transparent

## Context

An MDI analysis window used `QGraphicsOpacityEffect` on its content widget, but
lowering opacity did not reveal overlapping windows behind it. The content was
fading into the analysis frame and `QMdiSubWindow` backgrounds, which were still
opaque.

## Guidance

When a Qt child window needs to reveal sibling windows behind it, make the shell
transparent as well as the faded content:

```python
sub_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
sub_window.setAutoFillBackground(False)
frame.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
frame.setAutoFillBackground(False)
```

The stylesheet must also avoid repainting the shell as an opaque block:

```css
QMdiSubWindow#analysisSubWindow { background: transparent; border: none; }
QFrame#analysisWindowFrame { background: transparent; }
```

Keep the opacity control itself in the title bar or another unfaded shell area
when it needs to remain readable.

## Why This Matters

Opacity effects only blend against whatever the parent stack has already
painted. If the parent frame is opaque, users see a faded panel over a solid
background instead of the intended overlapping analysis window.

## When to Apply

Apply this for MDI child windows, floating analysis panels, preview overlays, or
any PySide6 widget where opacity is meant to expose sibling content behind the
active panel.
