---
title: Use Real Tab Semantics For Dashboard Tabs
date: 2026-05-24
category: docs/solutions/design-patterns
module: MF Log Analyzer dashboard
problem_type: design_pattern
component: frontend_stimulus
severity: low
applies_when:
  - "Building tabbed dashboard navigation with only one active panel visible"
  - "Using buttons to switch views in React or similar frontend apps"
  - "Adding keyboard support for dense analysis workspaces"
tags: [accessibility, tabs, keyboard-navigation, dashboard]
---

# Use Real Tab Semantics For Dashboard Tabs

## Context

During Task 8 review, the dashboard tabs looked and behaved like tabs visually, but were implemented as a navigation region with buttons and `aria-current`. That left screen reader and keyboard behavior weaker than the actual UI contract.

## Guidance

When a dashboard has one active view panel controlled by a horizontal tab strip, implement the full tab pattern:

- The tab container uses `role="tablist"` and an accessible label.
- Each tab button uses `role="tab"`, `aria-selected`, `aria-controls`, a stable `id`, and roving `tabIndex`.
- The active content wrapper uses `role="tabpanel"`, an `id`, and `aria-labelledby` pointing back to the active tab.
- ArrowLeft, ArrowRight, Home, and End update the active tab deterministically.

For MF Log Analyzer, `src/ui/Tabs.tsx` owns stable tab ids and keyboard movement, while `src/ui/Layout.tsx` applies the matching `tabpanel` attributes around the active view.

## Why This Matters

Visual tab styling alone is not enough for assistive technology or keyboard-only workflows. Analytics dashboards are often scanned quickly under pressure, so navigation should be predictable by mouse, keyboard, and screen reader.

## When to Apply

- Use this pattern for true tabbed interfaces with one active panel.
- Use ordinary links or `nav` when changing routes or moving to separate pages instead.
- Keep the implementation local and deterministic; a small id helper is enough for simple dashboards.

## Examples

Weak pattern:

```tsx
<nav aria-label="Analysis views">
  <button aria-current="page">Summary</button>
</nav>
```

Better pattern:

```tsx
<div role="tablist" aria-label="Analysis views">
  <button role="tab" aria-selected={isActive} aria-controls="summary-panel" id="summary-tab">
    Summary
  </button>
</div>
<section role="tabpanel" id="summary-panel" aria-labelledby="summary-tab">
  ...
</section>
```
