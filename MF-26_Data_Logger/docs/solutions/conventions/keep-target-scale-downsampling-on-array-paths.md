---
title: "Keep Target-Scale Downsampling On Array Paths"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "performance"
module: "mflog_proto.data.downsample"
tags:
  - "performance"
  - "downsampling"
  - "numpy"
  - "benchmarking"
---

# Keep Target-Scale Downsampling On Array Paths

## Context

The 300k x 200 prototype benchmark initially spent 18 seconds in graph-cache
generation for 20 channels. The first fix replaced slow `repr(float)` cache
fingerprints with numpy binary fingerprints, but the benchmark still spent more
than 5 seconds converting large Polars columns into Python lists and then back
into numpy arrays.

## Guidance

For target-scale render preparation, keep the path columnar:

```text
Polars Series -> numpy array -> min/max bucket indices -> small render lists
```

Avoid this shape for large inputs:

```text
Polars Series -> Python list of 300k values -> numpy array -> small render lists
```

Only convert to Python lists after downsampling has reduced the data to the
actual render point count.

## Why This Matters

Python list round trips hide inside otherwise vectorized pipelines and can be
larger than the real algorithmic work. In this prototype, staying on the numpy
array path reduced 20-channel graph-cache generation from 18.3 seconds to 0.75
seconds and turned the target benchmark from failing to passing.

## When to Apply

Apply this to downsampling, filtering, interpolation, event detection, and report
image preparation. Any code path that touches hundreds of thousands of samples
should preserve columnar/numpy data until it reaches a UI boundary that truly
requires Python objects.
