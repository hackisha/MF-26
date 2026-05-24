---
title: Honor Profile Report Sections In Renderers
date: 2026-05-24
category: docs/solutions/logic-errors
module: report
problem_type: logic_error
component: documentation
severity: medium
symptoms:
  - "Settings can edit profile.reportSections, but exported reports still render fixed sections"
root_cause: logic_error
resolution_type: code_fix
tags:
  - reports
  - settings
  - profile-contracts
  - regression-tests
---

# Honor Profile Report Sections In Renderers

## Problem

Profile settings exposed `reportSections` as configurable data, but the HTML report renderer ignored that field and always rendered the same Summary, Diagnostics, and Events sections.

## Symptoms

- Editing `reportSections` in Settings appears to succeed.
- Report output does not change after the setting is edited.
- Defaults list sections such as `overlays`, `behavior`, `map`, and `segments`, but those sections never appear in exported HTML.

## What Didn't Work

- Validating that `reportSections` is an array only protects the Settings editor shape. It does not prove downstream renderers consume the contract.
- UI tests that only assert "report renders" miss configuration fields that should affect output composition.

## Solution

Add a focused regression test that builds a report with a profile whose `reportSections` contains only `summary`, then assert disabled sections are absent:

```ts
const html = buildReportHtml({
  log,
  profile: { ...profile2025, reportSections: ["summary"] },
  events,
  diagnostics,
  summary
});

expect(html).toContain("<h2>Summary</h2>");
expect(html).not.toContain("<h2>Diagnostics</h2>");
expect(html).not.toContain("<h2>Events</h2>");
```

Then render optional report sections from the profile contract instead of hardcoding the report body. If a report needs session-owned data, pass it into the renderer explicitly, such as `segments: session.segments`.

## Why This Works

The profile is the source of truth for team-configurable report composition. Testing the output HTML against a deliberately narrow section list proves the renderer honors that contract rather than merely validating the JSON shape.

## Prevention

- For every editable profile field, add at least one test proving it changes the analysis or output path it configures.
- Keep validation tests and consumption tests separate: one checks shape, the other checks behavior.
- When adding new report section IDs to default profiles, update the report renderer in the same change.

## Related Issues

- `docs/solutions/logic-errors/validate-json-editors-against-runtime-contracts.md`
