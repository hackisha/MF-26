---
title: Test React Three Fiber Canvas Pixels Through Wrapper
date: 2026-05-25
category: docs/solutions/test-failures
module: MF Log Analyzer vehicle behavior model
problem_type: test_failure
component: testing_framework
severity: low
symptoms:
  - "Playwright pixel checks time out even though the React Three Fiber scene is mounted"
  - "Selectors like canvas.behavior-canvas do not match when className is placed on Canvas"
  - "Drawing a WebGL canvas into a 2D probe can return blank pixels"
root_cause: wrong_api
resolution_type: test_fix
tags: [playwright, threejs, r3f, webgl, pixels]
---

# Test React Three Fiber Canvas Pixels Through Wrapper

## Problem

While adding GLB rendering checks for the vehicle behavior model, the e2e test timed out waiting for colored pixels. The GLB request succeeded, but the test was sampling the wrong DOM node and then reading a WebGL buffer that was not preserved.

## Symptoms

- `.behavior-canvas` exists but `canvas.behavior-canvas` does not.
- `drawImage(webglCanvas, ...)` followed by `getImageData(...)` returns zero colored pixels.
- The app view appears mounted in Playwright's snapshot, but the pixel assertion never becomes true.

## What Didn't Work

Assuming the `className` passed to `<Canvas className="behavior-canvas">` lands on the inner `<canvas>` is incorrect for this app's React Three Fiber output. The class is on a wrapper element, with the actual canvas nested below it.

## Solution

Select the nested canvas:

```ts
await canvasPixelSummary(page, ".behavior-canvas canvas");
```

For tests that need to read pixels from a WebGL canvas, preserve the drawing buffer:

```tsx
<Canvas gl={{ preserveDrawingBuffer: true }} />
```

Then the Playwright test can use a small 2D probe canvas to verify the 3D scene is nonblank without storing golden screenshots.

## Why This Works

The corrected selector targets the actual WebGL canvas. `preserveDrawingBuffer` keeps the rendered frame available long enough for `drawImage` and `getImageData` to inspect it in headless Chrome.

## Prevention

When testing React Three Fiber scenes, inspect the rendered DOM before writing selectors. For pixel assertions, verify the test can read nonzero pixels from a known rendered scene before relying on the assertion as evidence that a model asset is visible.
