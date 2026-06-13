---
title: "Use drawn icons for Qt toolbar controls"
date: "2026-06-13"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "qt"
  - "ui"
  - "toolbar"
  - "icons"
  - "playback"
---

# Use Drawn Icons For Qt Toolbar Controls

## Context

The CSV playback dock originally used Unicode media glyphs such as play, stop,
skip, and event-jump symbols as `QPushButton` text. On Windows this depended on
font fallback, so the transport controls rendered as tiny mismatched glyphs and
looked unfinished even when the button behavior was correct.

## Guidance

For compact Qt toolbars, draw or load real `QIcon` assets instead of putting
symbol glyphs in button text. Keep the button text empty, set an explicit icon
size, and expose a stable dynamic property that tests can assert.

```python
button.setText("")
button.setIcon(_drawn_playback_icon("play"))
button.setIconSize(QtCore.QSize(18, 18))
button.setProperty("playbackIcon", "play")
```

Style icon buttons through their dynamic properties so disabled, hover, and
active states remain visible in the dark theme:

```css
QPushButton[playbackSymbol="true"] { ... }
QPushButton[playbackIcon="play"] { ... }
QPushButton[playbackSymbol="true"]:disabled { ... }
```

## Why This Matters

Font-rendered symbols are not a reliable UI asset. They vary by Windows font,
locale, DPI, and fallback behavior, which makes a polished control strip look
random. Real icons make the toolbar stable and let tests catch regressions where
text glyphs are reintroduced.

## When to Apply

Apply this whenever adding transport controls, toolbar buttons, window controls,
plot tools, or other compact icon-first controls in the PySide6 UI.
