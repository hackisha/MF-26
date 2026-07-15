---
title: "Align web map tiles with plot coordinates"
date: "2026-06-02"
track: "knowledge"
category: "conventions"
problem_type: "bug_prevention"
module: "mflog_proto.ui"
tags:
  - "gps"
  - "openstreetmap"
  - "pyqtgraph"
  - "visualization"
---

# Align Web Map Tiles With Plot Coordinates

## Context

OpenStreetMap tiles are 256 px images where the first image row is the northern
edge of the tile. A pyqtgraph `ImageItem` placed into a longitude/latitude plot
maps array rows into the plot's y axis, where larger latitude values are higher.
Passing the QImage rows through unchanged can make the visual map background
misalign with the GPS route. Loading a single center tile and stretching it over
the plot also creates a low-resolution, misleading background.

## Guidance

- Build a tile mosaic that covers the GPS bounds instead of stretching one tile.
- Clamp the mosaic to a small maximum tile count so the optional map background
  cannot freeze the UI on slow tile downloads.
- Set the mosaic rectangle from the actual western, eastern, southern, and
  northern Web Mercator tile bounds.
- Flip QImage rows vertically before passing them to pyqtgraph so image north
  appears at the higher-latitude side of the plot.
- Keep GPS route/current/hover items above the tile layer with explicit z-values.

## When to Apply

Use this rule for GPS map backgrounds, lap overlays, exported route thumbnails,
or any future map layer that combines web map rasters with latitude/longitude
plot data.
