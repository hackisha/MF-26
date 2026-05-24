---
title: Summary Duration Uses Timestamp Range
date: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer summary
problem_type: logic_error
component: service_object
severity: medium
symptoms:
  - "Non-monotonic log rows can under-report run duration when duration uses last timestamp minus first timestamp"
  - "Irregular CSV ordering can make summaries disagree with the actual logged time range"
root_cause: logic_error
resolution_type: code_fix
tags: [typescript, summary, timestamps, datalog, duration]
---

# Summary Duration Uses Timestamp Range

## Problem

MF Log Analyzer summaries originally computed duration as the last row timestamp minus the first row timestamp. That only works when rows are strictly ordered by time.

## Symptoms

- A log with timestamps `[0, 10, 5]` reported 5 seconds instead of 10 seconds.
- A reversed two-row log with timestamps `[10, 0]` could clamp to 0 seconds instead of preserving the 10 second range.

## What Didn't Work

- Relying on fixture logs with monotonic timestamps. The sample CSV stayed green while the summary logic still encoded an ordering assumption.
- Clamping `last - first` to zero. That avoids negative durations but hides reversed or irregular timestamp ordering.

## Solution

Scan all finite row timestamps and compute the clamped difference between the maximum and minimum timestamp:

```ts
function durationSec(log: AppliedLog): number {
  let minimum: number | null = null;
  let maximum: number | null = null;

  for (const row of log.rows) {
    if (!isFiniteNumber(row.timestampSec)) continue;
    minimum = minimum === null ? row.timestampSec : Math.min(minimum, row.timestampSec);
    maximum = maximum === null ? row.timestampSec : Math.max(maximum, row.timestampSec);
  }

  if (minimum === null || maximum === null) return 0;
  return Math.max(0, maximum - minimum);
}
```

## Why This Works

Duration is a property of the observed timestamp range, not row order. Scanning min and max handles sorted, reversed, and partially shuffled logs while still returning 0 for empty logs or logs without finite timestamps.

## Prevention

- Test summary duration with non-monotonic timestamp sequences such as `[0, 10, 5]` and `[10, 0]`.
- Treat CSV row order as input data, not as proof that timestamps are monotonic.
- Keep duration aggregation iterative so it remains safe for large datalogs.

## Related Issues

- `src/domain/summary.ts`
- `tests/domain/summary.test.ts`
