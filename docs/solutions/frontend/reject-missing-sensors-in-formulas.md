---
title: "Reject missing sensors in telemetry formulas"
date: 2026-05-24
category: frontend
problem_type: data_integrity
component: Elec_app log replay
tags:
  - telemetry
  - formulas
  - event-rules
  - testing
---

# Reject missing sensors in telemetry formulas

## Problem

Telemetry formula engines can accidentally treat missing sensor keys as `0`. That is dangerous for event rules because a CSV without `OilPressure_bar` would make `OilPressure_bar < 1` evaluate as true and show a false low-oil-pressure warning.

## Symptoms

- Default event rules fire on logs that do not contain the referenced sensor column.
- A typo in a derived sensor expression silently produces plausible-looking output.
- Missing data and real zero values are indistinguishable in analysis results.

## Solution

Distinguish a missing key from a non-numeric value. Missing keys should throw so rule evaluation can skip the rule for that sample, while present non-numeric/null values can still coerce to `0` if that is the product decision.

```ts
function toNumber(name: string, value: SensorValue | undefined): number {
  if (value === undefined) throw new Error(`알 수 없는 센서입니다: ${name}`);
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
```

Cover it with both formula and rule-level tests:

```ts
expect(() => evaluateFormula("MissingSensor < 1", {})).toThrow("알 수 없는 센서");
expect(extractLogEvents(missingOilSession, settings).map((event) => event.type)).not.toContain("low-oil-pressure");
```

## Prevention

When adding formula/event-rule features, always test three cases separately: valid numeric sensor, present-but-empty sensor, and completely missing sensor. Event rules should not turn absent columns into safety warnings.
