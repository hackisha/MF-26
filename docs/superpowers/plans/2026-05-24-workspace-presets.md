# Workspace Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-app Workspace tab where multiple analysis panels can be viewed together and saved as reusable layout presets.

**Architecture:** Store workspace presets as small serializable layout records, render them through a new `WorkspaceView`, and reuse existing analysis views inside movable/resizable panel shells. Keep OS-level pop-out as a separate action and make the first version reliable without new package installs.

**Tech Stack:** React 19, Zustand session state, Vitest, Testing Library, Playwright, CSS grid.

---

### Files

- Create: `src/domain/workspacePresets.ts`
- Create: `src/ui/WorkspaceView.tsx`
- Create: `tests/domain/workspacePresets.test.ts`
- Create: `tests/ui/workspaceView.test.tsx`
- Modify: `src/ui/Tabs.tsx`
- Modify: `src/ui/Layout.tsx`
- Modify: `src/styles.css`
- Modify: `tests/e2e/app-smoke.spec.ts`

### Task 1: Workspace Preset Domain

- [ ] Write failing tests in `tests/domain/workspacePresets.test.ts` for default presets, localStorage persistence, invalid JSON fallback, and panel geometry clamping.
- [ ] Run `npm.cmd test -- tests/domain/workspacePresets.test.ts` and confirm it fails because `workspacePresets` does not exist.
- [ ] Implement `src/domain/workspacePresets.ts` with `WorkspacePanelView`, `WorkspacePanel`, `WorkspacePreset`, `defaultWorkspacePresets`, `loadWorkspacePresets`, `saveWorkspacePresets`, `normalizeWorkspacePreset`, and `createWorkspacePanel`.
- [ ] Run `npm.cmd test -- tests/domain/workspacePresets.test.ts` and confirm it passes.

### Task 2: Workspace View UI

- [ ] Write failing tests in `tests/ui/workspaceView.test.tsx` for rendering the Workspace tab controls, selecting a preset, adding/removing a panel, moving/resizing a panel, saving a preset, and rendering panel content through an injectable test renderer.
- [ ] Run `npm.cmd test -- tests/ui/workspaceView.test.tsx` and confirm it fails because `WorkspaceView` does not exist.
- [ ] Implement `src/ui/WorkspaceView.tsx` with a preset selector, save/reset controls, add-panel controls, grid-based panel shell, panel move/resize buttons, close buttons, and existing analysis views as content.
- [ ] Run `npm.cmd test -- tests/ui/workspaceView.test.tsx` and confirm it passes.

### Task 3: Routing, Tabs, And Styles

- [ ] Add `workspace` to `TabId`, tab labels, tab refs, and route handling.
- [ ] Lazy-load `WorkspaceView` in `Layout` and render it at `/workspace`.
- [ ] Add Workspace CSS for a dense desktop-like surface, compact title bars, stable panel dimensions, scrollable panel bodies, and responsive fallback.
- [ ] Update `tests/e2e/app-smoke.spec.ts` to expect the `Workspace` tab.

### Task 4: Verification

- [ ] Run focused tests: `npm.cmd test -- tests/domain/workspacePresets.test.ts tests/ui/workspaceView.test.tsx tests/e2e/app-smoke.spec.ts`.
- [ ] Run full unit tests: `npm.cmd test`.
- [ ] Run type check: `npm.cmd run lint`.
- [ ] Run production build: `npm.cmd run build`.
- [ ] Run E2E smoke with system Chrome: `PLAYWRIGHT_USE_SYSTEM_CHROME=1 PLAYWRIGHT_PORT=5193 npm.cmd run test:e2e -- tests/e2e/app-smoke.spec.ts`.
- [ ] Do a quick visual pass on the Workspace tab and fix obvious layout breakage before completion.
