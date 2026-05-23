---
title: "Preserve uploaded CSV across workspace tabs"
date: 2026-05-24
category: frontend
problem_type: ui_bug
component: Elec_app log replay analysis
tags:
  - react
  - csv-upload
  - state-persistence
  - local-storage
  - testing-library
symptoms:
  - "Uploaded CSV disappears after leaving and returning to the log analysis workspace"
  - "The issue reproduces when browser storage fails or a CSV is too large for localStorage"
root_cause: async_timing
resolution_type: code_fix
---

# Preserve uploaded CSV across workspace tabs

## Problem

The log analysis workspace accepted CSV uploads, but switching to another workspace and back could reset the replay session. This was most visible when browser storage failed, because the uploaded CSV only lived inside the `LogReplayTab` component state.

## Root Cause

`App` conditionally rendered `LogReplayTab` only while the log workspace was active. Leaving the workspace unmounted the component, clearing its in-memory CSV session. If `saveStoredLogReplayState` failed because the CSV exceeded the browser storage limit, there was no persisted copy to restore from.

There was also a smaller async file-input hazard: `CsvLogUploader` read `event.currentTarget` after awaiting `file.text()`. In React event handling, capture the input element before the await so the file input can be reset reliably.

## Solution

Keep the log replay workspace mounted and hide it when another workspace is active:

```tsx
<section className="workspace-view" hidden={activeWorkspace !== "logReplay"} aria-hidden={activeWorkspace !== "logReplay"}>
  <LogReplayTab />
</section>
```

Then cover the failure mode with a test that forces storage writes to fail:

```tsx
await user.upload(screen.getByLabelText("CSV 로그 파일"), file);
expect(await screen.findByText("파일: track-day.csv")).toBeInTheDocument();

await user.click(screen.getByRole("button", { name: "배선 디버거 핀/커넥터 추적" }));
await user.click(screen.getByRole("button", { name: "로그 분석 CSV 분석/재생" }));

expect(await screen.findByText("파일: track-day.csv")).toBeInTheDocument();
```

For file inputs, capture the input before async reads:

```tsx
async function handleChange(event: ChangeEvent<HTMLInputElement>) {
  const input = event.currentTarget;
  const file = event.target.files?.[0];
  if (!file) return;

  onFileText(file.name, await file.text());
  input.value = "";
}
```

## Prevention

For upload-driven tools, test tab or workspace navigation with storage mocked to fail. Browser persistence is a recovery path, not the only source of truth for data the user just uploaded in the current session.
