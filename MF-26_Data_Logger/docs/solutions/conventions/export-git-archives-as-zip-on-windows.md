---
title: "Export git archives as zip on Windows"
date: "2026-06-02"
track: "knowledge"
category: "conventions"
problem_type: "bug_prevention"
module: "release"
tags:
  - "git"
  - "windows"
  - "archive"
  - "korean-paths"
---

# Export Git Archives As Zip On Windows

## Context

When mirroring this repository into a separate GitHub upload worktree on Windows,
`git archive --format=tar HEAD | tar -xf - -C <target>` produced a damaged tar
stream under PowerShell. Extracting a tar file also failed on a tracked Korean
filename with `Invalid empty pathname`. The command exited after noisy retry
output, which can leave a partially exported tree.

## Guidance

- Avoid piping binary git archives through PowerShell.
- Prefer `git archive --format=zip -o <archive.zip> HEAD` for Windows export
  workflows that may contain Korean or other non-ASCII paths.
- Extract with `Expand-Archive -LiteralPath <archive.zip> -DestinationPath <target> -Force`.
- Before deleting or replacing an export target, resolve the absolute paths and
  verify the target is inside the intended worktree.
- Treat any archive extraction warning as a failed export and rerun with a clean
  target.

## When to Apply

Use this for GitHub upload worktrees, release handoff folders, or any Windows
automation that exports tracked repository contents into another directory.
