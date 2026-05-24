---
module: verification
date: 2026-05-24
problem_type: developer_experience
component: tooling
severity: low
applies_when:
  - "Capturing Windows npm, Playwright, Vitest, or TypeScript command output through cmd"
  - "Printing a redirected log file after a command completes"
tags:
  - windows
  - cmd
  - verification
  - exit-code
---

# Preserve Windows Command Exit Code Before Reading Logs

## Context

When a Windows command redirects test output to a log and then prints that log with `type`, `%ERRORLEVEL%` can report the status of `type` instead of the original test command. That can make a crashed or failed verification look successful.

## Guidance

Capture the command exit code immediately after the command finishes, then print the log:

```cmd
cmd /v:on /c "npm.cmd run test:e2e > %TEMP%\e2e.log 2>&1 & set EXITCODE=!ERRORLEVEL! & type %TEMP%\e2e.log & echo EXIT:!EXITCODE!"
```

Use delayed expansion (`/v:on` and `!ERRORLEVEL!`) when the command is inside a quoted `cmd /c` string. This preserves the original status before later commands overwrite it.

## Why This Matters

Verification reports are only useful when they reflect the command that matters. In this session, reading the log after the command initially masked a Windows access violation exit code (`-1073741819`) as `0`.

## When to Apply

Use this pattern whenever a Windows verification command redirects output, prints a log, and needs to report the original exit code in the same shell invocation.
