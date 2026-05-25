---
title: "Centralize standard channel alias resolution"
date: "2026-05-25"
last_updated: "2026-05-26"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.data"
tags:
  - "channel-mapping"
  - "derived-channels"
  - "csv-loading"
---

# Centralize Standard Channel Alias Resolution

## Context

MF-LOG-ANALYZER separates raw CSV columns from stable standard channel IDs. During the prototype, mapping accepted some aliases while derived-channel calculation read different names directly. That allowed cases where a channel was marked missing even though derived calculation could use it, or mapping accepted an alias that derived calculation ignored.

## Guidance

Keep standard channel aliases in one source of truth. CSV loading, mapping review, derived calculations, UI views, and reports should all resolve raw CSV names through that shared mapping contract.

In the prototype, `channel_mapping.resolve_standard_sources()` is the shared boundary:

```python
standard_sources = resolve_standard_sources(list(columns))
store = ColumnStore(
    row_count=row_count,
    raw_columns=columns,
    standard_sources=standard_sources,
)
```

Derived calculations should prefer standard channel IDs and only use raw names as narrow compatibility fallbacks:

```python
_add_scaled(derived, "AX_CORRECTED_G", store, ("AX_RAW_G", "ax_g"), scale=1 / 8)
_add_difference(derived, "DBW_ERROR", store, "DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT")
```

## Why This Matters

Mapping state drives user review, reliability badges, analysis-window availability, and reports. If each layer carries its own alias table, those layers drift and users see contradictions such as "missing" channels that still plot or derived results that fail despite accepted mappings.

## When to Apply

Apply this whenever adding a standard channel, CSV alias, vehicle-profile alias, derived-channel formula, or report field. Add tests for both the raw CSV alias and the standard channel ID itself.

When real sample logs share a common header, promote the important columns into the central alias table immediately. The 2025 root sample CSVs all expose core fields such as `GPS_Speed_KPH`, `TPS_percent`, `VSS_kmh`, `Batt_V`, `gx_dps`, `gy_dps`, and `gz_dps`; leaving those outside `KNOWN_ALIASES` makes downstream UI and health modules rely on raw names again.

## Example Tests

```python
def test_map_columns_accepts_standard_channel_ids_as_direct_sources():
    mapping = map_columns(["AX_RAW_G", "DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT"])
    sources = resolve_standard_sources(
        ["AX_RAW_G", "DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT"]
    )

    assert mapping["AX_CORRECTED_G"].state is MappingState.DERIVED
    assert mapping["DBW_ERROR"].state is MappingState.DERIVED
    assert sources["AX_RAW_G"] == "AX_RAW_G"
```
