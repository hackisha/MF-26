---
module: packaging
date: "2026-06-03"
problem_type: build_error
component: tooling
severity: medium
symptoms:
  - "PyInstaller clean build fails with WinError 5 while removing files under prototype/dist."
  - "The locked file can be a packaged dependency such as numpy linalg pyd."
root_cause: missing_workflow_step
resolution_type: workflow_improvement
tags:
  - pyinstaller
  - windows
  - exe-smoke
  - dist-lock
---

# Stop Packaged EXE Before PyInstaller Clean Build

## Problem

On Windows, `python -m PyInstaller --noconfirm --clean packaging/mflog_analyzer.spec`
can fail during the `COLLECT` cleanup phase if a previously built
`MF-LOG-ANALYZER-v2.exe` is still running from `prototype/dist`.

## Symptoms

The build reaches `Removing dir ...\prototype\dist\MF-LOG-ANALYZER-v2` and then
fails with `PermissionError: [WinError 5] Access is denied` for a file inside
the old dist folder, for example `numpy\linalg\_umath_linalg.cp312-win_amd64.pyd`.

## Root Cause

The packaged application process keeps DLL/PYD files loaded from the previous
dist directory. PyInstaller's clean build needs to delete that directory before
assembling the new one, so any still-running packaged EXE can lock dependency
files and block cleanup.

## Solution

Before rerunning a clean build, check for an existing packaged process and stop
only that process if it is running from this workspace:

```powershell
Get-Process | Where-Object {
    $_.ProcessName -like '*MF-LOG*'
} | Select-Object Id, ProcessName, Path
```

If the path points at this project's `prototype\dist\MF-LOG-ANALYZER-v2`, stop
it and rerun PyInstaller:

```powershell
Stop-Process -Id <pid> -Force
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean .\packaging\mflog_analyzer.spec
```

## Prevention

After EXE smoke tests, always terminate the smoke process in the same script
that launched it:

```powershell
$proc = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
$alive = -not $proc.HasExited
if ($alive) { Stop-Process -Id $proc.Id -Force }
```

If a build fails with WinError 5, investigate process locks before changing
packaging code or deleting broader folders.
