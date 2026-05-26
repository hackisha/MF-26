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
labels. The vehicle model window loaded GLB metadata, but the viewport only
showed status text, which looked like the model had not loaded.

## Guidance

Every visualization that claims an interaction should expose visible feedback in
the same window. For plot hover, provide both a tooltip and a stable label such
as `Hover | ...` so automated tests and users can verify the behavior. For model
loading, a successful metadata parse is not enough; the viewport should show a
visible preview, fallback render, or explicit failure state.

## Why This Matters

Without observable feedback, an implemented data path still feels broken. Tests
that assert visible labels/previews catch this gap better than tests that only
inspect internal metadata.

## When to Apply

Use this when adding or reviewing plot hover, playback cursors, current-position
markers, GLB/OBJ model previews, map layers, and any visualization where the user
expects immediate visual confirmation.
