---
title: Use CommonJS Electron Preloads In Portable Packages
date: 2026-05-25
category: docs/solutions/build-errors
module: MF Log Analyzer portable Electron packaging
problem_type: build_error
component: tooling
severity: medium
symptoms:
  - "Packaged portable exe renders the app shell but desktop actions are unavailable"
  - "window.mfLogAnalyzer is undefined in the packaged renderer"
  - "File menu commands cannot trigger CSV import because the preload bridge never registers"
root_cause: config_error
resolution_type: config_change
tags: [electron, preload, commonjs, packaging, portable]
---

# Use CommonJS Electron Preloads In Portable Packages

## Problem

The manually assembled portable Electron build could load `resources/app/dist/index.html`, but the desktop bridge was missing. The app showed the React shell, yet native actions such as File > Open CSV could not reach the renderer because `window.mfLogAnalyzer` was never exposed.

## Symptoms

- CDP inspection of the exe showed `loaded: true` but `desktopApi: false` and `menuApi: false`.
- The top-level Open CSV fallback still appeared, but Electron-native file open behavior was unavailable.
- The File menu item could send `menu:openCsv`, but no preload listener existed in the renderer.

## What Didn't Work

- Verifying only that `index.html` loaded was insufficient. The renderer can be visible while the preload bridge is absent.
- Adding renderer fallbacks prevents a dead button, but it does not fix missing Electron IPC or native menu integration.

## Solution

Build the preload as CommonJS and point `BrowserWindow` at that output:

```ts
// electron/main.ts
webPreferences: {
  preload: path.join(__dirname, "preload.cjs"),
  contextIsolation: true,
  nodeIntegration: false
}
```

Use a `.cts` preload source so TypeScript emits `.cjs` under `module: "NodeNext"`:

```json
{
  "include": ["electron/**/*.ts", "electron/**/*.cts"]
}
```

Also update development wait conditions to expect `dist-electron/preload.cjs`, and add a regression test that asserts the packaged main process loads the CommonJS preload.

## Why This Works

The app package is `type: "module"`, so a generated `preload.js` is treated as ESM in the loose portable package. Electron preload scripts are safest as CommonJS in this packaging style because they execute before the isolated renderer and must reliably call `contextBridge.exposeInMainWorld`.

## Prevention

- Treat a packaged Electron smoke test as incomplete unless it verifies both visible DOM text and preload API availability.
- For portable builds, inspect `typeof window.mfLogAnalyzer?.openCsv` and `typeof window.mfLogAnalyzer?.onOpenCsvMenu` through CDP before handing over the exe.
- Keep a test covering the exact preload filename used by `BrowserWindow`.

## Related Issues

- [Package Electron File Renderers With Relative Assets](./package-electron-file-renderers-with-relative-assets.md)
- [Do Not Silently Noop Optional Desktop APIs](../logic-errors/do-not-silently-noop-optional-desktop-apis.md)
