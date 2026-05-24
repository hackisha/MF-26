---
title: Windows Unicode Worktree Node Builds
date: 2026-05-24
category: docs/solutions/build-errors
module: MF Log Analyzer scaffold
problem_type: build_error
component: tooling
severity: medium
symptoms:
  - "node exits with -1073741819 when loading TypeScript or Vite from a Korean OneDrive path"
  - "npm install postinstall scripts for electron or esbuild fail with code 3221225477"
root_cause: incomplete_setup
resolution_type: environment_setup
tags: [windows, node, vite, typescript, unicode-paths]
---

# Windows Unicode Worktree Node Builds

## Problem

During the MF Log Analyzer Electron/Vite scaffold, `npm install` and `npm run build` failed under a non-ASCII OneDrive worktree path even though the project files were valid.

## Symptoms

- `npm install` failed in dependency postinstall scripts with `code 3221225477`.
- `node .\node_modules\typescript\bin\tsc --version` exited with `-1073741819` and no TypeScript output.
- Directly loading large TypeScript/Vite bundles from the worktree path crashed Node.
- Copying the same TypeScript package to `C:\Temp` allowed `tsc --version` to run.

## What Didn't Work

- Re-running `npm install` from the real worktree path.
- Installing with `--ignore-scripts` alone. It created dependencies, but TypeScript and Vite still crashed from the real path.
- Downgrading TypeScript inside the semver range. The crash reproduced across tested TypeScript versions because the path/runtime combination was the issue.

## Solution

Map the implementation worktree to an ASCII drive path for install/build verification:

```cmd
subst M: "<non-ASCII OneDrive repo path>\.worktrees\codex-mf-log-analyzer-implementation"
cd /d M:\
npm.cmd install
npm.cmd run build
subst M: /D
```

If Vite realpaths the mapped drive back to the original non-ASCII path, keep the Vite root and Rollup input anchored to the current working directory and preserve symlink/subst resolution:

```ts
export default defineConfig({
  root: process.cwd(),
  plugins: [react()],
  resolve: {
    preserveSymlinks: true
  },
  build: {
    rollupOptions: {
      input: path.join(process.cwd(), "index.html")
    }
  }
});
```

## Why This Works

The files still live in the required worktree, but Node executes tooling through an ASCII path (`M:\...`) rather than the Unicode OneDrive path that triggered the access violation. `preserveSymlinks` prevents Vite/Rollup from resolving the HTML entry back to the original absolute path when that causes invalid output naming or crashes.

## Prevention

- On Windows repositories under OneDrive or non-ASCII paths, try an ASCII `subst` mapping before changing application code when Node toolchains crash with `3221225477` or `-1073741819`.
- When using `subst` with Vite, verify that the config does not realpath the entry back to the original Unicode path.
- In Codex desktop, prefer absolute paths with `apply_patch` when editing inside a worktree under the main workspace; otherwise patches may target the parent checkout.
