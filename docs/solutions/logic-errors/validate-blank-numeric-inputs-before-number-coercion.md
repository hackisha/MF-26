---
title: Validate Blank Numeric Inputs Before Number Coercion
date: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer forms
problem_type: logic_error
component: frontend_forms
severity: medium
applies_when:
  - "Validating numeric text inputs from form state"
  - "Calling domain/store actions that assume finite numbers"
  - "Using Number(value) before checking for blank strings"
tags: [forms, validation, numbers, react]
---

# Validate Blank Numeric Inputs Before Number Coercion

## Context

Task 11 added manual segment inputs for start and end seconds. Review caught that `Number("")` evaluates to `0`, so a named segment with blank time fields could be saved as `0s - 0s`.

## Guidance

Trim and reject blank strings before number coercion:

```tsx
const trimmedStart = startSec.trim();
const parsedStart = Number(trimmedStart);

if (!trimmedStart || !Number.isFinite(parsedStart)) {
  setError("Enter finite seconds.");
  return;
}
```

Then call store/domain actions only after validation passes. Add a regression test for the named-but-blank numeric input case, not only the fully empty form.

## Why This Matters

Form state is string-based even when an input has `type="number"`. JavaScript coercion can turn missing user input into a valid-looking domain value, causing bad segments, thresholds, or calibration values to be persisted.

## When to Apply

- Manual segment start/end fields.
- Settings fields for calibration scale/offset, valid ranges, thresholds, and sensor limits.
- Any future numeric form that writes directly into a profile or session snapshot.
