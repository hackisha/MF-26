---
title: "Make visualization affordances observable"
date: "2026-05-26"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "visualization"
  - "hover"
  - "glb"
  - "ui"
---

# Make Visualization Affordances Observable

## Context

Time-series hover existed, but GPS and G-G plots did not expose visible hover
labels. The vehicle model window originally loaded GLB metadata and then drew a
bounds-only preview, which did not satisfy a requirement to load and show the
actual vehicle model.

## Guidance

Every visualization that claims an interaction should expose visible feedback in
the same window. For plot hover, provide both a tooltip and a stable label such
as `Hover | ...` so automated tests and users can verify the behavior. For GLB
or OBJ model loading, a successful metadata parse is not enough. Parse the actual
mesh primitives, render their vertices/triangles, and expose observable counts or
state in tests. A bounds box is acceptable only as an explicit fallback state.
For layered maps, make route layer roles observable too: faint all-route
background, highlighted active route, current marker, hover marker, and route
identity should each have state that tests can assert.

## Why This Matters

Without observable feedback, an implemented data path still feels broken. Tests
that assert visible labels, rendered mesh counts, and fallback states catch this
gap better than tests that only inspect internal metadata.

## When to Apply

Use this when adding or reviewing plot hover, playback cursors, current-position
markers, GLB/OBJ model previews, selectable model assets, map layers, and any
visualization where the user expects immediate visual confirmation.
