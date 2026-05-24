---
title: Disable Vite File Watching In E2E Runners
date: 2026-05-24
category: developer-experience
module: e2e
problem_type: developer_experience
component: testing_framework
severity: low
applies_when:
  - "Running Playwright against a short-lived Vite dev server"
  - "Testing from Windows subst paths, OneDrive paths, or non-ASCII worktrees"
tags:
  - playwright
  - vite
  - windows
  - e2e
---

# Disable Vite File Watching In E2E Runners

## Context

Playwright smoke tests can pass while the Vite dev server keeps watching the worktree and restarts during teardown. On Windows subst or OneDrive paths, those late restarts can print `EPERM` errors or keep server processes alive after the useful test result has already been produced.

## Guidance

For one-shot E2E runs or Windows desktop smoke launches, start Vite with an explicit environment flag and map that flag to `server.watch: null` in `vite.config.ts`.

```ts
server: {
  host: "127.0.0.1",
  port: 5173,
  ...(process.env.VITE_DISABLE_WATCH === "1" ? { watch: null } : {})
}
```

If a custom Node runner owns the server lifecycle, pass the same flag to the spawned Vite process and tear down the process tree explicitly on Windows:

```js
spawn(process.execPath, ["node_modules/vite/bin/vite.js"], {
  env: {
    ...process.env,
    VITE_DISABLE_WATCH: "1"
  }
});
```

Before starting the dev server, probe the chosen port with `node:net` and fail early if it is already occupied. Polling `fetch(baseUrl)` alone can accidentally accept an unrelated server that happens to be listening on the same port.

Also avoid naming child-process parameters `process`; that shadows Node's global `process` object and can accidentally skip Windows-specific cleanup branches such as `process.platform === "win32"`.

## Why This Matters

E2E verification should produce a clear pass or fail signal. File watching is useful during interactive development, but in short-lived test runners it can create noisy post-test errors, mask process cleanup problems, and make successful runs look suspicious.

## When to Apply

- Playwright starts or depends on a local Vite server.
- The test command needs to exit cleanly on Windows.
- The server is not meant to support interactive HMR during the test run.

## Examples

In MF Log Analyzer, `npm.cmd run test:e2e` now uses `scripts/run-e2e.mjs`, which starts Vite with `VITE_DISABLE_WATCH=1`, sets `PLAYWRIGHT_SKIP_WEB_SERVER=1` for the nested Playwright process, and kills the Vite process tree after Playwright exits.

The desktop development launcher also uses `scripts/run-vite-desktop.mjs` so `npm.cmd run electron:dev` does not depend on Vite file watching in OneDrive or non-ASCII Windows paths. This avoids a crash where Vite reports `vite.config.ts changed, restarting server...` and then exits before Electron can load `http://127.0.0.1:5173/`.

## Related

- `docs/solutions/developer-experience/preserve-windows-command-exit-code-before-reading-logs.md`
