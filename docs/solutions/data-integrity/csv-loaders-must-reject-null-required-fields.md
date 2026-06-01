---
title: CSV Loaders Must Reject Null And Missing Required Fields
date: 2026-06-01
category: docs/solutions/data-integrity
module: mf-log-analyzer-v2/core/csv_loader.py
problem_type: bug_pattern
component: data_loading
severity: high
applies_when:
  - "Building CSV loaders for telemetry or analytics data"
  - "Using Polars casts to validate numeric columns"
  - "A profile has required channels such as Timestamp"
tags: [csv, polars, fail-fast, data-integrity, telemetry]
---

# CSV Loaders Must Reject Null And Missing Required Fields

## Context

The MF Log Analyzer v2 CSV loader originally used `cast(pl.Float64, strict=True)` and treated that as enough numeric validation. Final review found two gaps: blank cells or short rows became nulls that later turned into `NaN`, and a missing required `Timestamp` column was silently replaced by a synthetic time axis.

## Guidance

Validate three separate failure classes before exposing loaded data:

- Missing required profile channels, especially the configured time channel.
- Null values in mapped numeric source columns, including blank cells and short rows.
- Non-finite numeric values such as `NaN` or infinity after conversion.

The tests should lock each class independently. A test for `"not-a-number"` is not enough because it does not prove null handling.

## Why This Matters

Telemetry analysis depends on the time axis and mapped sensor values being trustworthy. Silent `NaN` values or a synthetic time axis can corrupt playback, cursor sync, lap segmentation, derived formulas, and safety checks without producing an obvious load error.

## When to Apply

Apply this whenever a loader maps external tabular data into a typed analytics model, especially when:

- The source file can have optional or malformed rows.
- The parser fills missing cells with nulls.
- A later NumPy conversion can turn nulls into `NaN`.
- Required channels are defined by a user-editable profile.

## Example

Weak validation:

```python
values = raw[source].cast(pl.Float64, strict=True).to_numpy()
```

Stronger validation:

```python
source_values = raw[source]
if source_values.null_count() > 0:
    raise ValueError(f"Missing numeric value in source column: {source}")

values = source_values.cast(pl.Float64, strict=True).to_numpy()
if not np.isfinite(values).all():
    raise ValueError(f"Non-finite numeric value in source column: {source}")
```

## Related

- mf-log-analyzer-v2/src/mf_log_analyzer_v2/core/csv_loader.py
- mf-log-analyzer-v2/tests/core/test_csv_loader.py
