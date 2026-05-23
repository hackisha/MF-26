---
title: Avoid Spread For Large Log Aggregations
date: 2026-05-24
category: docs/solutions/performance-issues
module: MF Log Analyzer diagnostics
problem_type: performance_issue
component: service_object
severity: medium
symptoms:
  - "Large CSV logs can trigger argument-limit failures when arrays are spread into Math.min or Math.max"
  - "Diagnostics, summaries, or event scans may fail before producing user-visible findings"
root_cause: wrong_api
resolution_type: code_fix
tags: [typescript, diagnostics, large-logs, aggregation, performance]
---

# Avoid Spread For Large Log Aggregations

## Problem

MF Log Analyzer diagnostics originally computed aggregate values with `Math.min(...values)` and `Math.max(...values.map(...))`. That works on small fixtures but can fail on real datalogs with many rows because the spread turns every value into a function argument.

## Symptoms

- Code review flagged a likely `RangeError` risk for large CSV logs.
- A 150,000-row regression test reproduced the failure before the diagnostic aggregation was rewritten.
- The failure would prevent downstream diagnostics, summaries, reports, or views from receiving findings.

## What Didn't Work

- Keeping fixture-only tests. The small 2025 sample passed while still leaving the large-log failure mode open.
- Building an intermediate array and then spreading it into `Math.min` or `Math.max`. The memory footprint is less important than the JavaScript function argument limit.

## Solution

Use iterative accumulation for log-wide aggregates:

```ts
function minValue(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId);
  let minimum: number | null = null;

  for (const value of values) {
    minimum = minimum === null ? value : Math.min(minimum, value);
  }

  return minimum;
}
```

The same pattern applies to maximum absolute values:

```ts
function maxAbs(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId);
  let maximum: number | null = null;

  for (const value of values) {
    const absoluteValue = Math.abs(value);
    maximum = maximum === null ? absoluteValue : Math.max(maximum, absoluteValue);
  }

  return maximum;
}
```

## Why This Works

The aggregation still inspects every numeric point, but each value is processed as loop data instead of becoming a separate function argument. Runtime behavior stays stable as log size grows.

## Prevention

- Do not use `Math.min(...values)`, `Math.max(...values)`, or similar spread patterns on full datalog channels.
- Add at least one synthetic large-log regression test for shared aggregate helpers.
- Treat diagnostics, event detection, summaries, and report generation as large-data paths even when the fixture is small.

## Related Issues

- `src/domain/diagnostics.ts`
- `tests/domain/diagnostics.test.ts`
