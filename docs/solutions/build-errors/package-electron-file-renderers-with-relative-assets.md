---
title: Package Electron File Renderers With Relative Assets
date: 2026-05-25
category: docs/solutions/build-errors
module: MF Log Analyzer portable Electron packaging
problem_type: build_error
component: tooling
severity: medium
symptoms:
  - "Portable Electron exe opens a window but the app UI is blank"
  - "Packaged window loads file:///.../dist/index.html but not the bundled JS or CSS"
  - "Loose resources/app builds can be mistaken for dev mode when app.isPackaged is false"
root_cause: config_error
resolution_type: config_change
tags: [electron, vite, packaging, file-url, portable]
---

# Package Electron File Renderers With Relative Assets

## Problem

The manually assembled portable Electron build opened a window but showed no app UI. The first fix made Electron load `resources/app/dist/index.html` instead of the Vite dev server, but the renderer still stayed blank because Vite emitted root-relative asset URLs.

## Symptoms

- Electron starts and creates a BrowserWindow.
- The loaded URL is `file:///.../resources/app/dist/index.html`.
- The generated HTML references `/assets/...`, which resolves to `file:///assets/...` instead of the local `dist/assets/...` folder.

## What Didn't Work

Checking only whether the exe process started was not enough. A process can remain alive while the renderer is blank. Checking only the top-level loaded URL was also incomplete because `index.html` can load successfully while scripts and styles fail.

## Solution

Use a runtime-mode helper that treats loose portable builds with existing `dist/index.html` as production, even if `app.isPackaged` is false. Also configure Vite with a relative base:

```ts
export default defineConfig({
  base: "./"
});
```

Verify packaged output by inspecting the built `dist/index.html`:

```html
<script type="module" crossorigin src="./assets/index-...js"></script>
```

For manual exe verification, start the app with a remote debugging port and inspect `document.body.innerText` through CDP. The app is not verified unless expected UI text such as `MF Log Analyzer` and `Open CSV` appears.

## Why This Works

Electron file-based renderers do not have a web server root. Relative asset URLs keep JS, CSS, and lazy chunks anchored beside `index.html`, which matches the portable folder layout under `resources/app/dist`.

## Prevention

When building Electron from Vite output without a local server, keep `base: "./"` covered by a regression test. For portable packaging, verify both the loaded URL and a real DOM marker after launching the exe.
