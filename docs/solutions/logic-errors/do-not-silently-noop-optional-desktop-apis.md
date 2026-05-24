---
title: Do Not Silently No-Op Optional Desktop APIs
date: 2026-05-24
category: logic-errors
module: desktop-integration
problem_type: bug
component: ui
severity: medium
symptoms:
  - "A toolbar button appears clickable but nothing happens"
  - "The app works in Electron tests with mocked preload APIs but fails silently in browser or preload-missing runs"
root_cause: "Renderer code used optional chaining against a desktop preload API and returned without fallback or visible status when the API was unavailable."
resolution_type: fallback
tags:
  - electron
  - preload
  - file-input
  - ui
---

# Do Not Silently No-Op Optional Desktop APIs

## Problem

`Open CSV` looked clickable but did nothing when `window.mfLogAnalyzer.openCsv` was unavailable. This can happen in a normal browser run, or if the Electron preload bridge fails to load.

## Symptoms

- Clicking `Open CSV` produces no dialog and no visible status change.
- Existing smoke tests pass because they inject a mocked `window.mfLogAnalyzer`.
- Browser-only development hides the problem unless the no-preload path is tested.

## What Didn't Work

Relying on optional chaining alone:

```ts
const result = await window.mfLogAnalyzer?.openCsv();
if (!result) return;
```

This avoids a crash, but it also turns a missing integration into a silent no-op.

## Solution

Keep the native Electron dialog as the preferred path, but provide a browser file-input fallback when the preload API is missing. The same session-loading pipeline should accept either source.

```tsx
if (window.mfLogAnalyzer?.openCsv) {
  await openCsv();
  return;
}

csvInputRef.current?.click();
```

Add a regression test that runs without `window.mfLogAnalyzer`, clicks the visible button, feeds a `File` through the hidden input, and asserts that a session loads.

## Why This Works

The renderer no longer depends on the preload bridge for basic CSV import. Electron users still get the native dialog, while browser and preload-failure cases can still choose a CSV and exercise the same analysis code.

## Prevention

- Any optional desktop API should have either a visible unavailable state or a local web fallback.
- Do not consider Electron integration covered if tests only mock the preload happy path.
- Add at least one browser/no-preload test for top-level import/export actions.
