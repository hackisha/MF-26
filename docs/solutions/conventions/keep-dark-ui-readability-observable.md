---
title: "Keep dark UI readability observable"
date: "2026-06-02"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "ui"
  - "readability"
  - "accessibility"
  - "theme"
---

# Keep Dark UI Readability Observable

## Context

The prototype uses a dark operational dashboard theme. When settings were added
incrementally, the right properties panel fell back to flat form rows and default
control colors. That made boundaries hard to see, checkbox indicators too dark,
and status labels nearly invisible when an analysis subwindow kept a light
default background.

## Guidance

- Give settings pages an explicit page/group/row structure, not only a
  `QFormLayout`.
- Style row labels, value labels, focus borders, disabled controls, and checkbox
  indicators separately.
- Keep analysis window backgrounds dark when their labels use light text.
- Make the style contract testable with object names such as
  `settingsGroupFrame`, `settingsRow`, and `settingsRowLabel`.
- Include disabled-state contrast in the acceptance surface; upload-disabled
  playback controls are visible often enough to matter.

## When to Apply

Use this when adding settings pages, dock panels, plot status labels, playback
controls, table/list widgets, or any dark-theme UI surface where default Qt
colors might leak in.
