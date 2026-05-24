---
title: Tolerate Malformed CSV Log Rows
date: 2026-05-24
category: logic-errors
module: csv-import
problem_type: bug
component: parser
severity: medium
symptoms:
  - "Opening a real data log fails with a single malformed row error"
  - "PapaParse reports TooFewFields or TooManyFields even though most rows are valid"
root_cause: "The CSV importer treated every parse error as fatal, including recoverable row-level field-count mismatches."
resolution_type: fallback
tags:
  - csv
  - parser
  - diagnostics
  - datalog
---

# Tolerate Malformed CSV Log Rows

## Problem

Real vehicle logs can contain a bad partial row, logger glitch, or interrupted write. Failing the entire import for one field-count mismatch makes the analyzer unusable even when the rest of the run is valid.

## Symptoms

- `Open CSV` shows an error such as `Too few fields: expected 63 fields but parsed 1`.
- The file has mostly valid rows, but one malformed line prevents all analysis views from loading.
- The user sees no way to inspect the rest of the run.

## What Didn't Work

Throwing on every `PapaParse` error:

```ts
if (parsed.errors.length > 0) {
  throw new Error(parsed.errors[0].message);
}
```

This is correct for unrecoverable syntax errors, but too strict for isolated `FieldMismatch` rows in telemetry logs.

## Solution

Keep the CSV delimiter explicit, treat row-level field-count mismatches as recoverable, skip those malformed rows, and preserve them as diagnostics.

```ts
const malformedRows = new Set(warnings.flatMap((warning) => (warning.row === null ? [] : [warning.row])));

return {
  headers: parsed.meta.fields ?? [],
  rows: parsed.data.filter((_row, index) => !malformedRows.has(index)),
  warnings
};
```

Then append import warnings to the session diagnostics so the user knows data was skipped.

## Why This Works

The analyzer can still run on the healthy majority of a log while preserving traceability for bad input rows. Critical parse errors remain fatal, but common datalog corruption becomes visible rather than blocking.

## Prevention

- Test CSV import with malformed middle rows, not only perfect fixtures.
- Treat recoverable row-level parser errors differently from unrecoverable file-level parser errors.
- Surface skipped-row counts and row numbers in Diagnostics so analysis is never silently lossy.
