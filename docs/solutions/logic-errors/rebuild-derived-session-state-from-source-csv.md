---
title: Rebuild Derived Session State From Source CSV
date: 2026-05-24
category: logic-errors
module: MF Log Analyzer session store
problem_type: logic_error
component: service_object
symptoms:
  - Profile changes leave loaded log values, diagnostics, events, or event segments from the previous profile.
  - Profile updates change rules or channel definitions but keep old applied log calibration and source mapping.
  - Async snapshot publishes can let an older write overwrite a newer session snapshot.
root_cause: logic_error
resolution_type: code_fix
severity: high
tags: [session-state, source-data, profile-switching, snapshots, zustand]
---

# Rebuild Derived Session State From Source CSV

## Problem
The MF Log Analyzer session store treated applied logs, diagnostics, events, and event segments as if they could be safely updated in place after profile changes. Those values are derived from the original CSV plus the active vehicle profile, so changing profile mappings or calibrations without re-running the full pipeline leaves stale analysis state.

## Symptoms
- Switching from one vehicle profile to another changes `selectedProfileId`, but `session.log.profileId` and computed channel values still come from the previous profile.
- Updating a loaded profile's channel mapping, calibration, or revision does not change `session.log.rows` or `profileRevision`.
- A selected event can continue pointing at an event ID that no longer exists after recomputation.
- When snapshot IPC becomes async, fire-and-forget publishes can complete out of order.

## What Didn't Work
- Re-running diagnostics and events against the old `AppliedLog` was insufficient because `AppliedLog` already contains profile-specific source mapping, calibration, and revision data.
- Publishing snapshots without ordering was fine while IPC was missing, but would become unsafe once real persistence was added.

## Solution
Keep a serializable copy of the source CSV in the store and session snapshot:

```ts
type SourceCsv = {
  filePath: string;
  text: string;
};
```

When a loaded profile changes, rebuild the analysis session from source:

```ts
function createSession(sourceCsv: SourceCsv, profile: VehicleProfile, preservedManualSegments: Segment[] = []): AnalysisSession {
  const parsed = parseCsv(sourceCsv.text);
  const log = applyProfile(fileNameFromPath(sourceCsv.filePath), parsed, profile);
  const diagnostics = runDiagnostics(log, profile);
  const events = detectEvents(log, profile);

  return {
    filePath: sourceCsv.filePath,
    profileId: profile.id,
    log,
    diagnostics,
    events,
    segments: [...segmentsFromEvents(events), ...preservedManualSegments]
  };
}
```

Queue async snapshot publishes so later snapshots cannot be overwritten by older pending writes:

```ts
let snapshotPublishQueue: Promise<void> = Promise.resolve();

export async function publishSessionSnapshot(): Promise<void> {
  const setSessionSnapshot = window.mfLogAnalyzer?.setSessionSnapshot;
  if (!setSessionSnapshot) return;

  const snapshot = createSessionSnapshot();
  const publish = snapshotPublishQueue.then(() => setSessionSnapshot(snapshot));
  snapshotPublishQueue = publish.catch(() => undefined);
  await publish;
}
```

## Why This Works
The source CSV and selected profile are the authoritative inputs for the analysis pipeline. Rebuilding from those inputs ensures applied channel values, profile revision, diagnostics, events, and event segments all agree with the active profile. Manual segments are user-authored state, so they are preserved separately and appended after event segments are regenerated.

The publish queue captures each snapshot at invocation time, then serializes the actual writes. If an earlier write is slow, later writes wait rather than racing and being overwritten.

## Prevention
- Treat parsed/applied analysis outputs as derived state; keep the raw input required to recompute them when configuration changes.
- Add focused store tests for profile switching, profile updates, stale selection cleanup, optional runtime APIs, and async snapshot ordering.
- Sanitize selected IDs after recomputation or hydration against the newly available event/overlay lists.

## Related Issues
- `docs/solutions/design-patterns/plan-popout-views-with-shared-session-state.md`
