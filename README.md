# MF Log Analyzer

MF Log Analyzer is a desktop-oriented CSV datalog viewer for MF race car logs. It runs as a Vite/React app inside Electron, with the same UI shell testable in a normal browser.

## What It Does

- Opens CSV logs and applies a vehicle profile to known channels.
- Summarizes run duration, speed, RPM, corrected G, EOT, oil pressure, and event counts.
- Runs diagnostics for missing/stale channels and threshold-driven vehicle events.
- Provides tabs for Summary, Diagnostics, Time-Series, Vehicle Behavior, Map/Lap, Report, and Settings.
- Supports pop-out views backed by a shared session snapshot.
- Generates an HTML report from the selected profile sections.

## Data Notes

- Raw ADXL acceleration channels are corrected with a `/8` scale factor through the `ax_corrected_g`, `ay_corrected_g`, and `az_corrected_g` channels.
- `OilTemp_C` is accepted as a source column for `EOT_IN` so older logs still populate engine oil temperature in.
- The 2026 vehicle profile adds suspension channels (`Susp_FL_mm`, `Susp_FR_mm`, `Susp_RL_mm`, `Susp_RR_mm`), pitot/aero channels (`Pitot_dP_Pa`, `Pitot_AirSpeed_KPH`), and `SteeringAngle_deg`.

## Commands

Use `npm.cmd` on Windows PowerShell if `npm.ps1` is blocked by execution policy.

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
```

`npm.cmd run test:e2e` starts a Vite server through `scripts/run-e2e.mjs` with file watching disabled, then tears it down after Playwright exits. You can pass a specific spec after `--`, or set `PLAYWRIGHT_PORT` if the default port is already occupied.

If Playwright browser binaries are unavailable but Google Chrome is installed at `C:\Program Files\Google\Chrome\Application\chrome.exe`, run:

```powershell
$env:PLAYWRIGHT_USE_SYSTEM_CHROME = "1"
npm.cmd run test:e2e -- tests/e2e/app-smoke.spec.ts
```

In some Windows environments, Node/Playwright can fail under OneDrive or non-ASCII paths. A practical workaround is to map the worktree to an ASCII drive path before running E2E:

```cmd
subst M: "C:\path\to\mf-log-analyzer-worktree"
cd /d M:\
npm.cmd run test:e2e
subst M: /d
```
