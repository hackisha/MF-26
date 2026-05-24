---
title: Stable Event IDs For High Frequency Log Windows
date: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer events
problem_type: logic_error
component: service_object
severity: medium
symptoms:
  - "Same-rule event windows can produce duplicate IDs when IDs are based only on rounded timestamps"
  - "High-frequency logs can contain multiple windows whose start times round to the same centisecond"
root_cause: logic_error
resolution_type: code_fix
tags: [typescript, events, ids, high-frequency-logs, regression-tests]
---

# Stable Event IDs For High Frequency Log Windows

## Problem

Event detection originally generated IDs from the rule ID plus `startSec.toFixed(2)`. That was deterministic, but not unique for high-frequency logs where two same-rule windows can start inside the same centisecond bucket.

## Symptoms

- Two distinct same-rule windows can share the same event ID.
- Event-backed segments inherit the duplicate event ID through `segment-${event.id}`.
- UI state keyed by segment or event ID can collapse distinct windows into one item.

## What Didn't Work

- Increasing timestamp precision alone reduces the collision window but does not define uniqueness.
- Treating fixture coverage as enough missed the high-frequency case because the sample log has coarse timestamps.

## Solution

Include a deterministic per-rule ordinal in each emitted event ID, alongside the timestamp for readability:

```ts
id: `${rule.id}-${eventOrdinal}-${startSec.toFixed(3)}`
```

Increment the ordinal only when a same-rule event is emitted. This keeps output stable for the same input while making multiple windows for the same rule distinct.

## Why This Works

The ordinal is assigned during the deterministic rule scan, so repeated runs over the same log and profile produce the same IDs. Because each emitted window for a rule gets a different ordinal, rounded timestamp collisions no longer collapse distinct events.

## Prevention

- Avoid using rounded timestamps as the only uniqueness component for domain IDs.
- Add regression tests with high-frequency windows whose starts collide under the old rounding scheme.
- When defining event duration semantics, test irregular timestamps explicitly so sample spacing is not inferred from non-matching rows.

## Related Issues

- `src/domain/events.ts`
- `tests/domain/events.test.ts`
