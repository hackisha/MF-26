# MF Log Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice of MF Log Analyzer: a Windows desktop CSV datalog analyzer with profile-based sensor mapping, calibration, diagnostics, event detection, summary, graph overlays, vehicle-behavior visualization, report export, settings, and pop-out view foundations.

**Architecture:** Use Electron for the Windows desktop shell and pop-out windows, React + TypeScript for the UI, and a pure TypeScript domain layer for parsing, calibration, diagnostics, event detection, summaries, and report generation. Keep domain code independent from React so it can be unit tested without the desktop runtime.

**Tech Stack:** Electron, Vite, React, TypeScript, Vitest, Testing Library, Papa Parse, Zustand, Plotly.js, Leaflet, Three.js, Zod, Playwright.

---

## Scope Check

The design spec contains several subsystems. This plan implements a first complete vertical slice that touches each core product area while keeping advanced depth small enough to ship and test.

Included in this plan:

- Project scaffold and desktop shell
- Default 2025 and 2026 vehicle profiles
- CSV parsing
- Profile-based column aliases and calibration
- ADXL345 `/8` corrected acceleration channels
- Log diagnostics
- Threshold and composite event detection
- Session state shared across tabs and pop-out windows
- Summary tab
- Log Diagnostics tab
- Time-Series Graph tab with overlay presets and normalized mode
- Vehicle Behavior tab with G-G diagram and simple car attitude visualization
- Map / Lap tab with coordinate fallback and basic manual/event segments
- Report tab with HTML export
- Settings tab with profile/channel/rule/preset JSON editing
- Unit tests for the domain layer
- Browser-level smoke test for the main UI

Deferred to follow-up plans:

- Signed Windows installer
- PDF export quality pass
- High-fidelity online map tile cache
- Advanced GPS start/finish crossing geometry
- Drift-corrected attitude estimation
- Large-file streaming optimization

## File Structure

Create this structure:

```text
package.json
tsconfig.json
tsconfig.node.json
vite.config.ts
vitest.config.ts
playwright.config.ts
electron/main.ts
electron/preload.ts
src/main.tsx
src/App.tsx
src/styles.css
src/domain/types.ts
src/domain/defaultProfiles.ts
src/domain/csvImport.ts
src/domain/profileApply.ts
src/domain/diagnostics.ts
src/domain/events.ts
src/domain/summary.ts
src/domain/segments.ts
src/domain/reportHtml.ts
src/state/sessionStore.ts
src/ui/Layout.tsx
src/ui/Tabs.tsx
src/ui/SummaryView.tsx
src/ui/DiagnosticsView.tsx
src/ui/TimeSeriesView.tsx
src/ui/BehaviorView.tsx
src/ui/MapLapView.tsx
src/ui/ReportView.tsx
src/ui/SettingsView.tsx
src/ui/PopoutButton.tsx
src/ui/ChannelPicker.tsx
src/ui/SeverityBadge.tsx
tests/fixtures/2025-sample.csv
tests/domain/profileApply.test.ts
tests/domain/diagnostics.test.ts
tests/domain/events.test.ts
tests/domain/summary.test.ts
tests/e2e/app-smoke.spec.ts
```

Responsibilities:

- `electron/`: Desktop window creation, file open/save dialogs, pop-out windows.
- `src/domain/`: Pure data logic. No React, no Electron.
- `src/state/`: Shared app session state and cross-view synchronization.
- `src/ui/`: Presentation components and view tabs.
- `tests/domain/`: Fast unit tests for data behavior.
- `tests/e2e/`: Desktop UI smoke tests.

## Task 1: Scaffold Electron + React + TypeScript

**Files:**

- Create: `package.json`
- Create: `tsconfig.json`
- Create: `tsconfig.node.json`
- Create: `vite.config.ts`
- Create: `vitest.config.ts`
- Create: `playwright.config.ts`
- Create: `electron/main.ts`
- Create: `electron/preload.ts`
- Create: `src/main.tsx`
- Create: `src/App.tsx`
- Create: `src/styles.css`

- [ ] **Step 1: Create package manifest**

Create `package.json`:

```json
{
  "name": "mf-log-analyzer",
  "version": "0.1.0",
  "private": true,
  "description": "Desktop CSV datalog analyzer for MF race car logs",
  "main": "dist-electron/main.js",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "electron:dev": "concurrently \"npm run dev\" \"wait-on http://127.0.0.1:5173 && electron .\"",
    "build": "tsc -b && vite build && tsc -p tsconfig.node.json",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "lint": "tsc -b --pretty false"
  },
  "dependencies": {
    "@react-three/fiber": "^9.0.0",
    "electron": "^35.0.0",
    "leaflet": "^1.9.4",
    "papaparse": "^5.5.0",
    "plotly.js-dist-min": "^2.35.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-plotly.js": "^2.6.0",
    "three": "^0.174.0",
    "zod": "^3.24.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.51.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.2.0",
    "@types/leaflet": "^1.9.16",
    "@types/node": "^22.13.0",
    "@types/papaparse": "^5.3.15",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "concurrently": "^9.1.0",
    "jsdom": "^26.0.0",
    "typescript": "^5.8.0",
    "vite": "^6.2.0",
    "vitest": "^3.0.0",
    "wait-on": "^8.0.0"
  }
}
```

- [ ] **Step 2: Create TypeScript and Vite configs**

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src", "tests"]
}
```

Create `tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2022",
    "strict": true,
    "outDir": "dist-electron",
    "skipLibCheck": true
  },
  "include": ["electron/**/*.ts"]
}
```

Create `vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
```

Add `@vitejs/plugin-react` to `devDependencies` before installing:

```json
"@vitejs/plugin-react": "^4.3.0"
```

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"]
  }
});
```

Create `playwright.config.ts`:

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173"
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true
  }
});
```

- [ ] **Step 3: Create Electron entry files**

Create `electron/main.ts`:

```ts
import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs/promises";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = process.env.VITE_DEV_SERVER_URL !== undefined || !app.isPackaged;

function rendererUrl(route = "/") {
  if (isDev) {
    return `http://127.0.0.1:5173${route}`;
  }
  return `file://${path.join(__dirname, "../dist/index.html")}${route === "/" ? "" : `#${route}`}`;
}

function createWindow(route = "/") {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    title: "MF Log Analyzer",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  void win.loadURL(rendererUrl(route));
  return win;
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("file:openCsv", async () => {
  const result = await dialog.showOpenDialog({
    title: "Open CSV log",
    filters: [{ name: "CSV files", extensions: ["csv"] }],
    properties: ["openFile"]
  });

  if (result.canceled || result.filePaths.length === 0) return null;
  const filePath = result.filePaths[0];
  const text = await fs.readFile(filePath, "utf8");
  return { filePath, text };
});

ipcMain.handle("file:saveHtmlReport", async (_event, html: string) => {
  const result = await dialog.showSaveDialog({
    title: "Save HTML report",
    defaultPath: "mf-log-analyzer-report.html",
    filters: [{ name: "HTML files", extensions: ["html"] }]
  });

  if (result.canceled || !result.filePath) return null;
  await fs.writeFile(result.filePath, html, "utf8");
  return result.filePath;
});

ipcMain.handle("view:popout", async (_event, route: string) => {
  createWindow(route);
  return true;
});
```

Create `electron/preload.ts`:

```ts
import { contextBridge, ipcRenderer } from "electron";

export type DesktopApi = {
  openCsv: () => Promise<{ filePath: string; text: string } | null>;
  saveHtmlReport: (html: string) => Promise<string | null>;
  popout: (route: string) => Promise<boolean>;
};

const api: DesktopApi = {
  openCsv: () => ipcRenderer.invoke("file:openCsv"),
  saveHtmlReport: (html) => ipcRenderer.invoke("file:saveHtmlReport", html),
  popout: (route) => ipcRenderer.invoke("view:popout", route)
};

contextBridge.exposeInMainWorld("mfLogAnalyzer", api);
```

- [ ] **Step 4: Create renderer shell**

Create `src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `src/App.tsx`:

```tsx
export default function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MF Log Analyzer</h1>
          <p>Open a CSV log to inspect vehicle health, behavior, and report outputs.</p>
        </div>
        <button type="button">Open CSV</button>
      </header>
      <section className="empty-state">No log loaded.</section>
    </main>
  );
}
```

Create `src/styles.css`:

```css
:root {
  color: #172026;
  background: #f5f7f8;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

button {
  border: 1px solid #a9b4bc;
  background: #ffffff;
  color: #172026;
  border-radius: 6px;
  padding: 8px 12px;
  font: inherit;
  cursor: pointer;
}

.app-shell {
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 24px;
  border-bottom: 1px solid #d8e0e5;
  background: #ffffff;
}

.topbar h1 {
  margin: 0;
  font-size: 22px;
}

.topbar p {
  margin: 4px 0 0;
  color: #51606a;
}

.empty-state {
  margin: 24px;
  padding: 24px;
  border: 1px solid #d8e0e5;
  border-radius: 8px;
  background: #ffffff;
}
```

- [ ] **Step 5: Install dependencies**

Run:

```bash
npm install
```

Expected: `package-lock.json` is created and npm exits with code 0.

- [ ] **Step 6: Run build**

Run:

```bash
npm run build
```

Expected: TypeScript, Vite, and Electron TypeScript compilation exit with code 0.

- [ ] **Step 7: Commit scaffold**

Run:

```bash
git add package.json package-lock.json tsconfig.json tsconfig.node.json vite.config.ts vitest.config.ts playwright.config.ts electron src
git commit -m "feat: scaffold MF Log Analyzer desktop app"
```

## Task 2: Define Domain Types And Default Profiles

**Files:**

- Create: `src/domain/types.ts`
- Create: `src/domain/defaultProfiles.ts`
- Create: `tests/domain/profileApply.test.ts`

- [ ] **Step 1: Write type-level test expectations**

Create `tests/domain/profileApply.test.ts` with an initial profile smoke test:

```ts
import { describe, expect, it } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";

describe("defaultProfiles", () => {
  it("ships 2025 and 2026 vehicle profiles", () => {
    expect(defaultProfiles.map((profile) => profile.id)).toEqual(["2025-vehicle", "2026-vehicle"]);
  });

  it("maps OilTemp_C as the 2025 source for EOT_IN", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.EOT_IN.sourceColumns).toContain("OilTemp_C");
  });

  it("defines corrected ADXL345 acceleration channels", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.ax_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.ay_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.az_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
  });
});
```

- [ ] **Step 2: Run failing test**

Run:

```bash
npm test -- tests/domain/profileApply.test.ts
```

Expected: FAIL because `src/domain/defaultProfiles.ts` does not exist.

- [ ] **Step 3: Create shared domain types**

Create `src/domain/types.ts`:

```ts
export type Severity = "info" | "warning" | "critical";

export type SensorGroup =
  | "Engine"
  | "CoolingOil"
  | "Fuel"
  | "GPS"
  | "IMU"
  | "Suspension"
  | "Aero"
  | "DriverInput"
  | "Electrical"
  | "Diagnostics";

export type Calibration =
  | { type: "identity" }
  | { type: "scaleOffset"; scale: number; offset: number }
  | { type: "invert" };

export type SensorChannel = {
  id: string;
  displayName: string;
  sourceColumns: string[];
  unit: string;
  group: SensorGroup;
  calibration: Calibration;
  validRange?: { min: number; max: number };
  defaultVisible: boolean;
  color: string;
};

export type ThresholdRule = {
  id: string;
  name: string;
  severity: Severity;
  all?: RuleCondition[];
  any?: RuleCondition[];
  minDurationSec: number;
  description: string;
  views: Array<"summary" | "diagnostics" | "graph" | "behavior" | "map" | "report">;
};

export type RuleCondition = {
  channelId: string;
  op: ">" | ">=" | "<" | "<=" | "==" | "!=";
  value: number;
};

export type OverlayPreset = {
  id: string;
  name: string;
  channelIds: string[];
  mode: "separateAxes" | "normalized";
};

export type VehicleProfile = {
  id: string;
  name: string;
  revision: string;
  channels: Record<string, SensorChannel>;
  rules: ThresholdRule[];
  overlays: OverlayPreset[];
  reportSections: string[];
};

export type RawLogRow = Record<string, string>;

export type NumericLogRow = {
  index: number;
  timestampSec: number;
  values: Record<string, number | null>;
};

export type AppliedLog = {
  fileName: string;
  profileId: string;
  profileRevision: string;
  rawHeaders: string[];
  rows: NumericLogRow[];
};

export type DiagnosticFinding = {
  id: string;
  severity: Severity;
  title: string;
  detail: string;
  affectedChannelIds: string[];
  startSec?: number;
  endSec?: number;
};

export type DetectedEvent = {
  id: string;
  ruleId: string;
  name: string;
  severity: Severity;
  startSec: number;
  endSec: number;
  description: string;
};

export type Segment = {
  id: string;
  name: string;
  startSec: number;
  endSec: number;
  source: "manual" | "event" | "gps";
};
```

- [ ] **Step 4: Create default profiles**

Create `src/domain/defaultProfiles.ts`:

```ts
import type { SensorChannel, ThresholdRule, VehicleProfile } from "./types";

const identity = { type: "identity" } as const;
const adxlCorrection = { type: "scaleOffset", scale: 0.125, offset: 0 } as const;

function channel(
  id: string,
  displayName: string,
  sourceColumns: string[],
  unit: string,
  group: SensorChannel["group"],
  color: string,
  calibration: SensorChannel["calibration"] = identity,
  validRange?: { min: number; max: number }
): SensorChannel {
  return {
    id,
    displayName,
    sourceColumns,
    unit,
    group,
    calibration,
    validRange,
    defaultVisible: false,
    color
  };
}

const baseChannels: Record<string, SensorChannel> = {
  Timestamp: channel("Timestamp", "Timestamp", ["Timestamp"], "s", "Diagnostics", "#5f6b73"),
  Latitude: channel("Latitude", "Latitude", ["Latitude"], "deg", "GPS", "#3887be"),
  Longitude: channel("Longitude", "Longitude", ["Longitude"], "deg", "GPS", "#38a169"),
  GPS_Speed_KPH: channel("GPS_Speed_KPH", "GPS Speed", ["GPS_Speed_KPH"], "km/h", "GPS", "#2563eb", identity, { min: 0, max: 180 }),
  Satellites: channel("Satellites", "Satellites", ["Satellites"], "count", "GPS", "#64748b", identity, { min: 0, max: 32 }),
  RPM: channel("RPM", "RPM", ["RPM"], "rpm", "Engine", "#dc2626", identity, { min: 0, max: 15000 }),
  TPS_percent: channel("TPS_percent", "Throttle Position", ["TPS_percent"], "%", "DriverInput", "#ea580c", identity, { min: 0, max: 100 }),
  MAP_kPa: channel("MAP_kPa", "MAP", ["MAP_kPa"], "kPa", "Engine", "#7c3aed"),
  VSS_kmh: channel("VSS_kmh", "Vehicle Speed", ["VSS_kmh"], "km/h", "Engine", "#0891b2", identity, { min: 0, max: 180 }),
  EOT_IN: channel("EOT_IN", "Engine Oil Temp In", ["EOT_IN", "OilTemp_C"], "C", "CoolingOil", "#f59e0b", identity, { min: -20, max: 180 }),
  EOT_OUT: channel("EOT_OUT", "Engine Oil Temp Out", ["EOT_OUT"], "C", "CoolingOil", "#d97706", identity, { min: -20, max: 180 }),
  OilPressure_bar: channel("OilPressure_bar", "Oil Pressure", ["OilPressure_bar"], "bar", "CoolingOil", "#0f766e", identity, { min: 0, max: 12 }),
  FuelPressure_bar: channel("FuelPressure_bar", "Fuel Pressure", ["FuelPressure_bar"], "bar", "Fuel", "#16a34a", identity, { min: 0, max: 12 }),
  CLT_C: channel("CLT_C", "Coolant Temp", ["CLT_C"], "C", "CoolingOil", "#ef4444", identity, { min: -20, max: 140 }),
  WBO_Lambda: channel("WBO_Lambda", "Lambda", ["WBO_Lambda"], "lambda", "Engine", "#9333ea", identity, { min: 0.5, max: 1.5 }),
  EGT1_C: channel("EGT1_C", "EGT 1", ["EGT1_C"], "C", "Engine", "#b45309", identity, { min: 0, max: 1100 }),
  EGT2_C: channel("EGT2_C", "EGT 2", ["EGT2_C"], "C", "Engine", "#92400e", identity, { min: 0, max: 1100 }),
  Batt_V: channel("Batt_V", "Battery Voltage", ["Batt_V"], "V", "Electrical", "#475569", identity, { min: 8, max: 16 }),
  ax_g: channel("ax_g", "Raw Longitudinal G", ["ax_g"], "g", "IMU", "#94a3b8"),
  ay_g: channel("ay_g", "Raw Lateral G", ["ay_g"], "g", "IMU", "#94a3b8"),
  az_g: channel("az_g", "Raw Vertical G", ["az_g"], "g", "IMU", "#94a3b8"),
  ax_corrected_g: channel("ax_corrected_g", "Corrected Longitudinal G", ["ax_g"], "g", "IMU", "#1d4ed8", adxlCorrection, { min: -4, max: 4 }),
  ay_corrected_g: channel("ay_corrected_g", "Corrected Lateral G", ["ay_g"], "g", "IMU", "#be123c", adxlCorrection, { min: -4, max: 4 }),
  az_corrected_g: channel("az_corrected_g", "Corrected Vertical G", ["az_g"], "g", "IMU", "#15803d", adxlCorrection, { min: -4, max: 4 }),
  gx_dps: channel("gx_dps", "Roll Rate", ["gx_dps"], "deg/s", "IMU", "#0f766e"),
  gy_dps: channel("gy_dps", "Pitch Rate", ["gy_dps"], "deg/s", "IMU", "#7c2d12"),
  gz_dps: channel("gz_dps", "Yaw Rate", ["gz_dps"], "deg/s", "IMU", "#6d28d9")
};

const defaultRules: ThresholdRule[] = [
  {
    id: "high-rpm-low-oil-pressure",
    name: "High RPM Oil Pressure Drop",
    severity: "critical",
    all: [
      { channelId: "RPM", op: ">", value: 6000 },
      { channelId: "OilPressure_bar", op: "<", value: 2.5 }
    ],
    minDurationSec: 0.5,
    description: "Oil pressure is low while engine speed is high.",
    views: ["summary", "graph", "report"]
  },
  {
    id: "low-battery-voltage",
    name: "Low Battery Voltage",
    severity: "warning",
    all: [{ channelId: "Batt_V", op: "<", value: 11.8 }],
    minDurationSec: 1,
    description: "Battery voltage may be low enough to reduce sensor confidence.",
    views: ["summary", "diagnostics", "graph", "report"]
  },
  {
    id: "high-lateral-g",
    name: "High Lateral G",
    severity: "info",
    all: [{ channelId: "ay_corrected_g", op: ">", value: 1.1 }],
    minDurationSec: 0.2,
    description: "Lateral acceleration exceeds the configured cornering threshold.",
    views: ["behavior", "graph", "map", "report"]
  }
];

const baseOverlays = [
  { id: "cooling", name: "Cooling", channelIds: ["EOT_IN", "EOT_OUT", "CLT_C"], mode: "separateAxes" as const },
  { id: "oil-stability", name: "Oil Stability", channelIds: ["RPM", "OilPressure_bar", "EOT_IN"], mode: "separateAxes" as const },
  { id: "gg-inputs", name: "Driver Input vs Response", channelIds: ["TPS_percent", "ay_corrected_g"], mode: "normalized" as const }
];

const suspensionChannels: Record<string, SensorChannel> = {
  Susp_FL_mm: channel("Susp_FL_mm", "Suspension FL", ["Susp_FL_mm"], "mm", "Suspension", "#1d4ed8"),
  Susp_FR_mm: channel("Susp_FR_mm", "Suspension FR", ["Susp_FR_mm"], "mm", "Suspension", "#be123c"),
  Susp_RL_mm: channel("Susp_RL_mm", "Suspension RL", ["Susp_RL_mm"], "mm", "Suspension", "#15803d"),
  Susp_RR_mm: channel("Susp_RR_mm", "Suspension RR", ["Susp_RR_mm"], "mm", "Suspension", "#b45309"),
  Pitot_dP_Pa: channel("Pitot_dP_Pa", "Pitot Differential Pressure", ["Pitot_dP_Pa"], "Pa", "Aero", "#0e7490"),
  Pitot_AirSpeed_KPH: channel("Pitot_AirSpeed_KPH", "Pitot Airspeed", ["Pitot_AirSpeed_KPH"], "km/h", "Aero", "#0369a1"),
  SteeringAngle_deg: channel("SteeringAngle_deg", "Steering Angle", ["SteeringAngle_deg"], "deg", "DriverInput", "#db2777")
};

export const defaultProfiles: VehicleProfile[] = [
  {
    id: "2025-vehicle",
    name: "2025 Vehicle",
    revision: "2026-05-24-initial",
    channels: baseChannels,
    rules: defaultRules,
    overlays: baseOverlays,
    reportSections: ["summary", "diagnostics", "events", "overlays", "behavior", "segments"]
  },
  {
    id: "2026-vehicle",
    name: "2026 Vehicle",
    revision: "2026-05-24-initial",
    channels: { ...baseChannels, ...suspensionChannels },
    rules: defaultRules,
    overlays: [
      ...baseOverlays,
      { id: "suspension-balance", name: "Suspension Balance", channelIds: ["Susp_FL_mm", "Susp_FR_mm", "Susp_RL_mm", "Susp_RR_mm"], mode: "separateAxes" }
    ],
    reportSections: ["summary", "diagnostics", "events", "overlays", "behavior", "map", "segments"]
  }
];
```

- [ ] **Step 5: Run profile tests**

Run:

```bash
npm test -- tests/domain/profileApply.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit domain profiles**

Run:

```bash
git add src/domain/types.ts src/domain/defaultProfiles.ts tests/domain/profileApply.test.ts
git commit -m "feat: define vehicle profiles and sensor channels"
```

## Task 3: Parse CSV And Apply Vehicle Profile

**Files:**

- Create: `src/domain/csvImport.ts`
- Create: `src/domain/profileApply.ts`
- Modify: `tests/domain/profileApply.test.ts`
- Create: `tests/fixtures/2025-sample.csv`

- [ ] **Step 1: Add sample CSV fixture**

Create `tests/fixtures/2025-sample.csv`:

```csv
Timestamp,GPS_Speed_KPH,VSS_kmh,Satellites,RPM,TPS_percent,OilTemp_C,EOT_OUT,OilPressure_bar,FuelPressure_bar,CLT_C,WBO_Lambda,EGT1_C,EGT2_C,Batt_V,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,Latitude,Longitude
0.00,0,0,12,1800,3,72,70,4.1,3.4,68,0.98,410,415,13.6,0.80,0.16,8.00,0.1,0.2,0.0,37.000000,127.000000
0.10,12,11,12,3200,45,73,71,4.0,3.4,69,0.97,470,475,13.5,1.60,2.40,8.08,0.4,0.3,3.0,37.000010,127.000010
0.20,28,27,11,6400,92,74,72,2.1,3.2,70,1.08,820,825,13.4,2.40,9.60,8.16,0.8,0.5,8.0,37.000020,127.000025
0.30,40,39,10,7000,96,75,73,2.0,3.1,71,1.09,850,852,11.5,3.20,10.40,8.24,1.2,0.7,12.0,37.000030,127.000040
1.50,40,39,10,6900,94,76,74,2.0,3.1,72,1.08,848,850,11.4,3.00,10.00,8.20,1.0,0.6,10.0,37.000035,127.000045
```

- [ ] **Step 2: Add failing CSV/profile tests**

Append to `tests/domain/profileApply.test.ts`:

```ts
import fs from "node:fs";
import path from "node:path";
import { parseCsv } from "../../src/domain/csvImport";
import { applyProfile } from "../../src/domain/profileApply";

describe("applyProfile", () => {
  it("creates numeric rows and corrected ADXL345 channels", () => {
    const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
    const parsed = parseCsv(csv);
    const profile2025 = defaultProfiles[0];
    const applied = applyProfile("2025-sample.csv", parsed, profile2025);

    expect(applied.rows).toHaveLength(5);
    expect(applied.rows[1].values.EOT_IN).toBe(73);
    expect(applied.rows[1].values.ax_corrected_g).toBeCloseTo(0.2);
    expect(applied.rows[1].values.ay_corrected_g).toBeCloseTo(0.3);
    expect(applied.rows[1].values.az_corrected_g).toBeCloseTo(1.01);
  });
});
```

- [ ] **Step 3: Run failing test**

Run:

```bash
npm test -- tests/domain/profileApply.test.ts
```

Expected: FAIL because `parseCsv` and `applyProfile` do not exist.

- [ ] **Step 4: Implement CSV parser**

Create `src/domain/csvImport.ts`:

```ts
import Papa from "papaparse";
import type { RawLogRow } from "./types";

export type ParsedCsv = {
  headers: string[];
  rows: RawLogRow[];
};

export function parseCsv(text: string): ParsedCsv {
  const parsed = Papa.parse<RawLogRow>(text, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false
  });

  if (parsed.errors.length > 0) {
    const first = parsed.errors[0];
    throw new Error(`CSV parse error at row ${first.row ?? "unknown"}: ${first.message}`);
  }

  return {
    headers: parsed.meta.fields ?? [],
    rows: parsed.data
  };
}
```

- [ ] **Step 5: Implement profile application**

Create `src/domain/profileApply.ts`:

```ts
import type { AppliedLog, Calibration, NumericLogRow, VehicleProfile } from "./types";
import type { ParsedCsv } from "./csvImport";

function parseNumber(value: string | undefined): number | null {
  if (value === undefined || value.trim() === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function applyCalibration(value: number | null, calibration: Calibration): number | null {
  if (value === null) return null;
  if (calibration.type === "identity") return value;
  if (calibration.type === "invert") return -value;
  return value * calibration.scale + calibration.offset;
}

function readSourceValue(row: Record<string, string>, sourceColumns: string[]): number | null {
  for (const column of sourceColumns) {
    const value = parseNumber(row[column]);
    if (value !== null) return value;
  }
  return null;
}

function readTimestamp(row: Record<string, string>, index: number): number {
  const timestamp = parseNumber(row.Timestamp);
  return timestamp ?? index;
}

export function applyProfile(fileName: string, parsed: ParsedCsv, profile: VehicleProfile): AppliedLog {
  const rows: NumericLogRow[] = parsed.rows.map((row, index) => {
    const values: Record<string, number | null> = {};

    for (const [channelId, channel] of Object.entries(profile.channels)) {
      const sourceValue = readSourceValue(row, channel.sourceColumns);
      values[channelId] = applyCalibration(sourceValue, channel.calibration);
    }

    return {
      index,
      timestampSec: readTimestamp(row, index),
      values
    };
  });

  return {
    fileName,
    profileId: profile.id,
    profileRevision: profile.revision,
    rawHeaders: parsed.headers,
    rows
  };
}
```

- [ ] **Step 6: Run profile application tests**

Run:

```bash
npm test -- tests/domain/profileApply.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit CSV import and profile application**

Run:

```bash
git add src/domain/csvImport.ts src/domain/profileApply.ts tests/domain/profileApply.test.ts tests/fixtures/2025-sample.csv
git commit -m "feat: parse CSV logs through vehicle profiles"
```

## Task 4: Implement Log Diagnostics

**Files:**

- Create: `src/domain/diagnostics.ts`
- Create: `tests/domain/diagnostics.test.ts`

- [ ] **Step 1: Write diagnostics tests**

Create `tests/domain/diagnostics.test.ts`:

```ts
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { parseCsv } from "../../src/domain/csvImport";
import { applyProfile } from "../../src/domain/profileApply";
import { runDiagnostics } from "../../src/domain/diagnostics";

function loadAppliedLog() {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), defaultProfiles[0]);
}

describe("runDiagnostics", () => {
  it("flags low battery and suspicious raw acceleration scale", () => {
    const findings = runDiagnostics(loadAppliedLog(), defaultProfiles[0]);

    expect(findings.some((finding) => finding.id === "low-battery-voltage")).toBe(true);
    expect(findings.some((finding) => finding.id === "suspicious-raw-adxl-scale")).toBe(true);
  });

  it("keeps diagnostics scoped to affected channels", () => {
    const finding = runDiagnostics(loadAppliedLog(), defaultProfiles[0]).find((item) => item.id === "low-battery-voltage");

    expect(finding?.affectedChannelIds).toEqual(["Batt_V"]);
    expect(finding?.severity).toBe("warning");
  });
});
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
npm test -- tests/domain/diagnostics.test.ts
```

Expected: FAIL because `runDiagnostics` does not exist.

- [ ] **Step 3: Implement diagnostics**

Create `src/domain/diagnostics.ts`:

```ts
import type { AppliedLog, DiagnosticFinding, VehicleProfile } from "./types";

function valuesFor(log: AppliedLog, channelId: string): Array<{ timestampSec: number; value: number }> {
  return log.rows
    .map((row) => ({ timestampSec: row.timestampSec, value: row.values[channelId] }))
    .filter((point): point is { timestampSec: number; value: number } => typeof point.value === "number");
}

function hasAnyValue(log: AppliedLog, channelId: string): boolean {
  return valuesFor(log, channelId).length > 0;
}

function minValue(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId).map((point) => point.value);
  return values.length > 0 ? Math.min(...values) : null;
}

function maxAbs(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId).map((point) => Math.abs(point.value));
  return values.length > 0 ? Math.max(...values) : null;
}

export function runDiagnostics(log: AppliedLog, profile: VehicleProfile): DiagnosticFinding[] {
  const findings: DiagnosticFinding[] = [];

  for (const [channelId, channel] of Object.entries(profile.channels)) {
    const available = channel.sourceColumns.some((source) => log.rawHeaders.includes(source));
    if (!available) {
      findings.push({
        id: `missing-${channelId}`,
        severity: channel.defaultVisible ? "warning" : "info",
        title: `Missing channel: ${channel.displayName}`,
        detail: `None of the expected columns were found: ${channel.sourceColumns.join(", ")}.`,
        affectedChannelIds: [channelId]
      });
    } else if (!hasAnyValue(log, channelId)) {
      findings.push({
        id: `empty-${channelId}`,
        severity: "warning",
        title: `No numeric values: ${channel.displayName}`,
        detail: `${channel.displayName} is present but has no numeric data.`,
        affectedChannelIds: [channelId]
      });
    }
  }

  for (let index = 1; index < log.rows.length; index += 1) {
    if (log.rows[index].timestampSec <= log.rows[index - 1].timestampSec) {
      findings.push({
        id: "timestamp-not-increasing",
        severity: "critical",
        title: "Timestamp is not increasing",
        detail: `Row ${index} is not later than row ${index - 1}.`,
        affectedChannelIds: ["Timestamp"],
        startSec: log.rows[index - 1].timestampSec,
        endSec: log.rows[index].timestampSec
      });
      break;
    }
  }

  const minBattery = minValue(log, "Batt_V");
  if (minBattery !== null && minBattery < 11.8) {
    findings.push({
      id: "low-battery-voltage",
      severity: "warning",
      title: "Low battery voltage",
      detail: `Minimum battery voltage is ${minBattery.toFixed(2)} V.`,
      affectedChannelIds: ["Batt_V"]
    });
  }

  const maxRawAy = maxAbs(log, "ay_g");
  const maxCorrectedAy = maxAbs(log, "ay_corrected_g");
  if (maxRawAy !== null && maxCorrectedAy !== null && maxRawAy > 6 && maxCorrectedAy <= 2) {
    findings.push({
      id: "suspicious-raw-adxl-scale",
      severity: "info",
      title: "ADXL345 raw scale looks inflated",
      detail: "Raw acceleration exceeds expected vehicle values, while corrected values look plausible. Analysis uses corrected channels.",
      affectedChannelIds: ["ax_g", "ay_g", "az_g", "ax_corrected_g", "ay_corrected_g", "az_corrected_g"]
    });
  }

  return findings;
}
```

- [ ] **Step 4: Run diagnostics tests**

Run:

```bash
npm test -- tests/domain/diagnostics.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit diagnostics**

Run:

```bash
git add src/domain/diagnostics.ts tests/domain/diagnostics.test.ts
git commit -m "feat: diagnose log quality and sensor confidence"
```

## Task 5: Implement Event Detection And Segment Extraction

**Files:**

- Create: `src/domain/events.ts`
- Create: `src/domain/segments.ts`
- Create: `tests/domain/events.test.ts`

- [ ] **Step 1: Write event detection tests**

Create `tests/domain/events.test.ts`:

```ts
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { parseCsv } from "../../src/domain/csvImport";
import { applyProfile } from "../../src/domain/profileApply";
import { detectEvents } from "../../src/domain/events";
import { segmentsFromEvents } from "../../src/domain/segments";

function loadAppliedLog() {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), defaultProfiles[0]);
}

describe("detectEvents", () => {
  it("detects configured composite events", () => {
    const events = detectEvents(loadAppliedLog(), defaultProfiles[0]);

    expect(events.some((event) => event.ruleId === "high-rpm-low-oil-pressure")).toBe(true);
    expect(events.some((event) => event.ruleId === "low-battery-voltage")).toBe(true);
  });

  it("creates event-backed segments", () => {
    const events = detectEvents(loadAppliedLog(), defaultProfiles[0]);
    const segments = segmentsFromEvents(events);

    expect(segments.length).toBeGreaterThan(0);
    expect(segments[0].source).toBe("event");
  });
});
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
npm test -- tests/domain/events.test.ts
```

Expected: FAIL because `detectEvents` and `segmentsFromEvents` do not exist.

- [ ] **Step 3: Implement event detection**

Create `src/domain/events.ts`:

```ts
import type { AppliedLog, DetectedEvent, RuleCondition, ThresholdRule, VehicleProfile } from "./types";

function compare(value: number | null, condition: RuleCondition): boolean {
  if (value === null) return false;
  if (condition.op === ">") return value > condition.value;
  if (condition.op === ">=") return value >= condition.value;
  if (condition.op === "<") return value < condition.value;
  if (condition.op === "<=") return value <= condition.value;
  if (condition.op === "==") return value === condition.value;
  return value !== condition.value;
}

function matchesRule(rowValues: Record<string, number | null>, rule: ThresholdRule): boolean {
  const all = rule.all ?? [];
  const any = rule.any ?? [];
  const allMatch = all.length === 0 || all.every((condition) => compare(rowValues[condition.channelId] ?? null, condition));
  const anyMatch = any.length === 0 || any.some((condition) => compare(rowValues[condition.channelId] ?? null, condition));
  return allMatch && anyMatch;
}

export function detectEvents(log: AppliedLog, profile: VehicleProfile): DetectedEvent[] {
  const events: DetectedEvent[] = [];

  for (const rule of profile.rules) {
    let startSec: number | null = null;
    let endSec: number | null = null;

    for (const row of log.rows) {
      if (matchesRule(row.values, rule)) {
        startSec ??= row.timestampSec;
        endSec = row.timestampSec;
      } else if (startSec !== null && endSec !== null) {
        if (endSec - startSec >= rule.minDurationSec) {
          events.push({
            id: `${rule.id}-${startSec.toFixed(2)}`,
            ruleId: rule.id,
            name: rule.name,
            severity: rule.severity,
            startSec,
            endSec,
            description: rule.description
          });
        }
        startSec = null;
        endSec = null;
      }
    }

    if (startSec !== null && endSec !== null && endSec - startSec >= rule.minDurationSec) {
      events.push({
        id: `${rule.id}-${startSec.toFixed(2)}`,
        ruleId: rule.id,
        name: rule.name,
        severity: rule.severity,
        startSec,
        endSec,
        description: rule.description
      });
    }
  }

  return events.sort((a, b) => a.startSec - b.startSec);
}
```

- [ ] **Step 4: Implement segment extraction**

Create `src/domain/segments.ts`:

```ts
import type { DetectedEvent, Segment } from "./types";

export function segmentsFromEvents(events: DetectedEvent[]): Segment[] {
  return events.map((event) => ({
    id: `segment-${event.id}`,
    name: event.name,
    startSec: event.startSec,
    endSec: event.endSec,
    source: "event"
  }));
}

export function createManualSegment(name: string, startSec: number, endSec: number): Segment {
  return {
    id: `manual-${startSec.toFixed(2)}-${endSec.toFixed(2)}`,
    name,
    startSec: Math.min(startSec, endSec),
    endSec: Math.max(startSec, endSec),
    source: "manual"
  };
}
```

- [ ] **Step 5: Run event tests**

Run:

```bash
npm test -- tests/domain/events.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit event engine**

Run:

```bash
git add src/domain/events.ts src/domain/segments.ts tests/domain/events.test.ts
git commit -m "feat: detect configured log events"
```

## Task 6: Implement Summary And Report HTML Domain Logic

**Files:**

- Create: `src/domain/summary.ts`
- Create: `src/domain/reportHtml.ts`
- Create: `tests/domain/summary.test.ts`

- [ ] **Step 1: Write summary and report tests**

Create `tests/domain/summary.test.ts`:

```ts
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { parseCsv } from "../../src/domain/csvImport";
import { applyProfile } from "../../src/domain/profileApply";
import { detectEvents } from "../../src/domain/events";
import { summarizeLog } from "../../src/domain/summary";
import { buildReportHtml } from "../../src/domain/reportHtml";

function loadAppliedLog() {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), defaultProfiles[0]);
}

describe("summary and report", () => {
  it("summarizes key run metrics", () => {
    const log = loadAppliedLog();
    const events = detectEvents(log, defaultProfiles[0]);
    const summary = summarizeLog(log, events);

    expect(summary.maxSpeedKph).toBe(40);
    expect(summary.maxRpm).toBe(7000);
    expect(summary.criticalEventCount).toBeGreaterThan(0);
  });

  it("builds an HTML report with correction note", () => {
    const log = loadAppliedLog();
    const events = detectEvents(log, defaultProfiles[0]);
    const summary = summarizeLog(log, events);
    const html = buildReportHtml({ log, profile: defaultProfiles[0], events, summary, diagnostics: [] });

    expect(html).toContain("MF Log Analyzer Report");
    expect(html).toContain("ADXL345 correction applied");
  });
});
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
npm test -- tests/domain/summary.test.ts
```

Expected: FAIL because `summarizeLog` and `buildReportHtml` do not exist.

- [ ] **Step 3: Implement summary**

Create `src/domain/summary.ts`:

```ts
import type { AppliedLog, DetectedEvent } from "./types";

export type RunSummary = {
  durationSec: number;
  maxSpeedKph: number | null;
  maxRpm: number | null;
  maxCorrectedG: number | null;
  maxEotInC: number | null;
  minOilPressureBar: number | null;
  warningEventCount: number;
  criticalEventCount: number;
};

function numericValues(log: AppliedLog, channelId: string): number[] {
  return log.rows
    .map((row) => row.values[channelId])
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
}

function max(log: AppliedLog, channelId: string): number | null {
  const values = numericValues(log, channelId);
  return values.length > 0 ? Math.max(...values) : null;
}

function min(log: AppliedLog, channelId: string): number | null {
  const values = numericValues(log, channelId);
  return values.length > 0 ? Math.min(...values) : null;
}

export function summarizeLog(log: AppliedLog, events: DetectedEvent[]): RunSummary {
  const first = log.rows[0]?.timestampSec ?? 0;
  const last = log.rows[log.rows.length - 1]?.timestampSec ?? first;
  const maxAx = Math.abs(max(log, "ax_corrected_g") ?? 0);
  const maxAy = Math.abs(max(log, "ay_corrected_g") ?? 0);

  return {
    durationSec: Math.max(0, last - first),
    maxSpeedKph: max(log, "GPS_Speed_KPH") ?? max(log, "VSS_kmh"),
    maxRpm: max(log, "RPM"),
    maxCorrectedG: Math.max(maxAx, maxAy),
    maxEotInC: max(log, "EOT_IN"),
    minOilPressureBar: min(log, "OilPressure_bar"),
    warningEventCount: events.filter((event) => event.severity === "warning").length,
    criticalEventCount: events.filter((event) => event.severity === "critical").length
  };
}
```

- [ ] **Step 4: Implement HTML report builder**

Create `src/domain/reportHtml.ts`:

```ts
import type { AppliedLog, DetectedEvent, DiagnosticFinding, VehicleProfile } from "./types";
import type { RunSummary } from "./summary";

function escapeHtml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

export function buildReportHtml(input: {
  log: AppliedLog;
  profile: VehicleProfile;
  events: DetectedEvent[];
  diagnostics: DiagnosticFinding[];
  summary: RunSummary;
}) {
  const { log, profile, events, diagnostics, summary } = input;
  const eventRows = events
    .map((event) => `<tr><td>${escapeHtml(event.severity)}</td><td>${escapeHtml(event.name)}</td><td>${event.startSec.toFixed(2)}-${event.endSec.toFixed(2)} s</td><td>${escapeHtml(event.description)}</td></tr>`)
    .join("");
  const diagnosticRows = diagnostics
    .map((finding) => `<tr><td>${escapeHtml(finding.severity)}</td><td>${escapeHtml(finding.title)}</td><td>${escapeHtml(finding.detail)}</td></tr>`)
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>MF Log Analyzer Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; color: #172026; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th, td { border: 1px solid #cfd8df; padding: 8px; text-align: left; }
    th { background: #eef3f6; }
    .note { padding: 12px; background: #fff7ed; border: 1px solid #fdba74; }
  </style>
</head>
<body>
  <h1>MF Log Analyzer Report</h1>
  <p><strong>File:</strong> ${escapeHtml(log.fileName)}</p>
  <p><strong>Profile:</strong> ${escapeHtml(profile.name)} (${escapeHtml(profile.revision)})</p>
  <h2>Run Summary</h2>
  <ul>
    <li>Duration: ${summary.durationSec.toFixed(2)} s</li>
    <li>Max speed: ${summary.maxSpeedKph ?? "n/a"} km/h</li>
    <li>Max RPM: ${summary.maxRpm ?? "n/a"}</li>
    <li>Max corrected G: ${summary.maxCorrectedG?.toFixed(2) ?? "n/a"} g</li>
    <li>Max EOT_IN: ${summary.maxEotInC ?? "n/a"} C</li>
    <li>Min oil pressure: ${summary.minOilPressureBar ?? "n/a"} bar</li>
    <li>Warning events: ${summary.warningEventCount}</li>
    <li>Critical events: ${summary.criticalEventCount}</li>
  </ul>
  <p class="note">ADXL345 correction applied: ax_corrected_g = ax_g / 8, ay_corrected_g = ay_g / 8, az_corrected_g = az_g / 8.</p>
  <h2>Diagnostics</h2>
  <table><thead><tr><th>Severity</th><th>Title</th><th>Detail</th></tr></thead><tbody>${diagnosticRows}</tbody></table>
  <h2>Events</h2>
  <table><thead><tr><th>Severity</th><th>Name</th><th>Time</th><th>Description</th></tr></thead><tbody>${eventRows}</tbody></table>
</body>
</html>`;
}
```

- [ ] **Step 5: Run summary tests**

Run:

```bash
npm test -- tests/domain/summary.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit summary and report domain**

Run:

```bash
git add src/domain/summary.ts src/domain/reportHtml.ts tests/domain/summary.test.ts
git commit -m "feat: summarize logs and generate reports"
```

## Task 7: Add Shared Session State And File Loading

**Files:**

- Create: `src/state/sessionStore.ts`
- Modify: `src/App.tsx`
- Modify: `src/domain/types.ts`

- [ ] **Step 1: Add desktop API types**

Append to `src/domain/types.ts`:

```ts
export type AnalysisSession = {
  filePath: string;
  profileId: string;
  log: AppliedLog;
  diagnostics: DiagnosticFinding[];
  events: DetectedEvent[];
  segments: Segment[];
};
```

- [ ] **Step 2: Create session store**

Create `src/state/sessionStore.ts`:

```ts
import { create } from "zustand";
import { defaultProfiles } from "../domain/defaultProfiles";
import { parseCsv } from "../domain/csvImport";
import { applyProfile } from "../domain/profileApply";
import { runDiagnostics } from "../domain/diagnostics";
import { detectEvents } from "../domain/events";
import { createManualSegment, segmentsFromEvents } from "../domain/segments";
import type { AnalysisSession, OverlayPreset, VehicleProfile } from "../domain/types";

declare global {
  interface Window {
    mfLogAnalyzer?: {
      openCsv: () => Promise<{ filePath: string; text: string } | null>;
      saveHtmlReport: (html: string) => Promise<string | null>;
      popout: (route: string) => Promise<boolean>;
      setSessionSnapshot: (snapshot: SessionSnapshot) => Promise<boolean>;
      getSessionSnapshot: () => Promise<SessionSnapshot | null>;
    };
  }
}

export type SessionSnapshot = {
  selectedProfileId: string;
  session: AnalysisSession | null;
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlayId: string | null;
};

type SessionStore = {
  profiles: VehicleProfile[];
  selectedProfileId: string;
  session: AnalysisSession | null;
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlay: OverlayPreset | null;
  setSelectedProfileId: (profileId: string) => void;
  openCsv: () => Promise<void>;
  addManualSegment: (name: string, startSec: number, endSec: number) => void;
  setCurrentTimeSec: (timeSec: number | null) => void;
  setSelectedEventId: (eventId: string | null) => void;
  setSelectedOverlay: (overlay: OverlayPreset | null) => void;
  updateProfile: (profile: VehicleProfile) => void;
};

function fileNameFromPath(filePath: string) {
  return filePath.split(/[\\/]/).pop() ?? filePath;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  profiles: defaultProfiles,
  selectedProfileId: "2025-vehicle",
  session: null,
  currentTimeSec: null,
  selectedEventId: null,
  selectedOverlay: defaultProfiles[0].overlays[0],
  setSelectedProfileId: (profileId) => {
    const profile = get().profiles.find((item) => item.id === profileId);
    set({ selectedProfileId: profileId, selectedOverlay: profile?.overlays[0] ?? null });
  },
  openCsv: async () => {
    const result = await window.mfLogAnalyzer?.openCsv();
    if (!result) return;
    const profile = get().profiles.find((item) => item.id === get().selectedProfileId) ?? get().profiles[0];
    const parsed = parseCsv(result.text);
    const log = applyProfile(fileNameFromPath(result.filePath), parsed, profile);
    const diagnostics = runDiagnostics(log, profile);
    const events = detectEvents(log, profile);
    const segments = segmentsFromEvents(events);
    set({
      session: { filePath: result.filePath, profileId: profile.id, log, diagnostics, events, segments },
      currentTimeSec: log.rows[0]?.timestampSec ?? null,
      selectedEventId: null
    });
  },
  addManualSegment: (name, startSec, endSec) => {
    const segment = createManualSegment(name, startSec, endSec);
    set((state) => {
      if (!state.session) return state;
      return { session: { ...state.session, segments: [...state.session.segments, segment] } };
    });
  },
  setCurrentTimeSec: (currentTimeSec) => set({ currentTimeSec }),
  setSelectedEventId: (selectedEventId) => set({ selectedEventId }),
  setSelectedOverlay: (selectedOverlay) => set({ selectedOverlay }),
  updateProfile: (profile) => {
    set((state) => ({
      profiles: state.profiles.map((item) => (item.id === profile.id ? profile : item))
    }));
  }
}));

export function createSessionSnapshot(): SessionSnapshot {
  const state = useSessionStore.getState();
  return {
    selectedProfileId: state.selectedProfileId,
    session: state.session,
    currentTimeSec: state.currentTimeSec,
    selectedEventId: state.selectedEventId,
    selectedOverlayId: state.selectedOverlay?.id ?? null
  };
}

export async function publishSessionSnapshot() {
  await window.mfLogAnalyzer?.setSessionSnapshot(createSessionSnapshot());
}

export async function hydrateSessionSnapshot() {
  const snapshot = await window.mfLogAnalyzer?.getSessionSnapshot();
  if (!snapshot) return;
  const state = useSessionStore.getState();
  const profile = state.profiles.find((item) => item.id === snapshot.selectedProfileId);
  const overlay = profile?.overlays.find((item) => item.id === snapshot.selectedOverlayId) ?? profile?.overlays[0] ?? null;
  useSessionStore.setState({
    selectedProfileId: snapshot.selectedProfileId,
    session: snapshot.session,
    currentTimeSec: snapshot.currentTimeSec,
    selectedEventId: snapshot.selectedEventId,
    selectedOverlay: overlay
  });
}
```

- [ ] **Step 3: Wire app header to session store**

Replace `src/App.tsx` with:

```tsx
import { useEffect } from "react";
import { hydrateSessionSnapshot, useSessionStore } from "./state/sessionStore";

export default function App() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const setSelectedProfileId = useSessionStore((state) => state.setSelectedProfileId);
  const openCsv = useSessionStore((state) => state.openCsv);
  const session = useSessionStore((state) => state.session);

  useEffect(() => {
    void hydrateSessionSnapshot();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MF Log Analyzer</h1>
          <p>{session ? session.log.fileName : "Open a CSV log to inspect vehicle health, behavior, and report outputs."}</p>
        </div>
        <div className="topbar-actions">
          <select value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)} aria-label="Vehicle profile">
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => void openCsv()}>
            Open CSV
          </button>
        </div>
      </header>
      <section className="empty-state">{session ? "Analysis session loaded." : "No log loaded."}</section>
    </main>
  );
}
```

Append to `src/styles.css`:

```css
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

select {
  border: 1px solid #a9b4bc;
  border-radius: 6px;
  padding: 8px 10px;
  background: #ffffff;
  color: #172026;
  font: inherit;
}
```

- [ ] **Step 4: Run tests and build**

Run:

```bash
npm test
npm run build
```

Expected: both commands exit with code 0.

- [ ] **Step 5: Commit session loading**

Run:

```bash
git add src/domain/types.ts src/state/sessionStore.ts src/App.tsx src/styles.css
git commit -m "feat: load CSV logs into shared sessions"
```

## Task 8: Build App Layout, Tabs, Summary, And Diagnostics Views

**Files:**

- Create: `src/ui/Layout.tsx`
- Create: `src/ui/Tabs.tsx`
- Create: `src/ui/SummaryView.tsx`
- Create: `src/ui/DiagnosticsView.tsx`
- Create: `src/ui/SeverityBadge.tsx`
- Modify: `src/App.tsx`
- Modify: `src/styles.css`

- [ ] **Step 1: Create severity badge**

Create `src/ui/SeverityBadge.tsx`:

```tsx
import type { Severity } from "../domain/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`severity severity-${severity}`}>{severity}</span>;
}
```

- [ ] **Step 2: Create tabs**

Create `src/ui/Tabs.tsx`:

```tsx
export type TabId = "summary" | "diagnostics" | "time-series" | "behavior" | "map-lap" | "report" | "settings";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "summary", label: "Summary" },
  { id: "diagnostics", label: "Log Diagnostics" },
  { id: "time-series", label: "Time-Series Graph" },
  { id: "behavior", label: "Vehicle Behavior" },
  { id: "map-lap", label: "Map / Lap" },
  { id: "report", label: "Report" },
  { id: "settings", label: "Settings" }
];

export function Tabs({ activeTab, onChange }: { activeTab: TabId; onChange: (tab: TabId) => void }) {
  return (
    <nav className="tabs" aria-label="Analysis views">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" className={activeTab === tab.id ? "tab tab-active" : "tab"} onClick={() => onChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 3: Create summary view**

Create `src/ui/SummaryView.tsx`:

```tsx
import { summarizeLog } from "../domain/summary";
import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

export function SummaryView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to see the run summary.</section>;

  const summary = summarizeLog(session.log, session.events);
  const criticalEvents = session.events.filter((event) => event.severity === "critical");

  return (
    <section className="view-grid">
      <div className="panel metric-grid">
        <Metric label="Duration" value={`${summary.durationSec.toFixed(2)} s`} />
        <Metric label="Max Speed" value={`${summary.maxSpeedKph ?? "n/a"} km/h`} />
        <Metric label="Max RPM" value={`${summary.maxRpm ?? "n/a"}`} />
        <Metric label="Max Corrected G" value={`${summary.maxCorrectedG?.toFixed(2) ?? "n/a"} g`} />
        <Metric label="Max EOT_IN" value={`${summary.maxEotInC ?? "n/a"} C`} />
        <Metric label="Min Oil Pressure" value={`${summary.minOilPressureBar ?? "n/a"} bar`} />
      </div>
      <div className="panel">
        <h2>Critical Events</h2>
        {criticalEvents.length === 0 ? (
          <p>No critical events detected.</p>
        ) : (
          <ul className="event-list">
            {criticalEvents.map((event) => (
              <li key={event.id}>
                <SeverityBadge severity={event.severity} />
                <span>{event.name}</span>
                <span>{event.startSec.toFixed(2)} s</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
```

- [ ] **Step 4: Create diagnostics view**

Create `src/ui/DiagnosticsView.tsx`:

```tsx
import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

export function DiagnosticsView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to inspect log diagnostics.</section>;

  return (
    <section className="panel">
      <h2>Log Diagnostics</h2>
      <p>{session.diagnostics.length} findings</p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Finding</th>
            <th>Detail</th>
            <th>Channels</th>
          </tr>
        </thead>
        <tbody>
          {session.diagnostics.map((finding) => (
            <tr key={finding.id}>
              <td><SeverityBadge severity={finding.severity} /></td>
              <td>{finding.title}</td>
              <td>{finding.detail}</td>
              <td>{finding.affectedChannelIds.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 5: Create layout and wire tabs**

Create `src/ui/Layout.tsx`:

```tsx
import { useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";
import { Tabs, type TabId } from "./Tabs";

export function Layout() {
  const [activeTab, setActiveTab] = useState<TabId>("summary");

  return (
    <>
      <Tabs activeTab={activeTab} onChange={setActiveTab} />
      <section className="content-area">
        {activeTab === "summary" && <SummaryView />}
        {activeTab === "diagnostics" && <DiagnosticsView />}
        {activeTab === "time-series" && <section className="empty-state">Time-series view is next.</section>}
        {activeTab === "behavior" && <section className="empty-state">Vehicle behavior view is next.</section>}
        {activeTab === "map-lap" && <section className="empty-state">Map / Lap view is next.</section>}
        {activeTab === "report" && <section className="empty-state">Report view is next.</section>}
        {activeTab === "settings" && <section className="empty-state">Settings view is next.</section>}
      </section>
    </>
  );
}
```

Modify `src/App.tsx` to import and render `Layout`:

```tsx
import { useSessionStore } from "./state/sessionStore";
import { Layout } from "./ui/Layout";

export default function App() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const setSelectedProfileId = useSessionStore((state) => state.setSelectedProfileId);
  const openCsv = useSessionStore((state) => state.openCsv);
  const session = useSessionStore((state) => state.session);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MF Log Analyzer</h1>
          <p>{session ? session.log.fileName : "Open a CSV log to inspect vehicle health, behavior, and report outputs."}</p>
        </div>
        <div className="topbar-actions">
          <select value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)} aria-label="Vehicle profile">
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => void openCsv()}>
            Open CSV
          </button>
        </div>
      </header>
      <Layout />
    </main>
  );
}
```

Append CSS:

```css
.tabs {
  display: flex;
  gap: 4px;
  padding: 10px 16px 0;
  background: #ffffff;
  border-bottom: 1px solid #d8e0e5;
}

.tab {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  border-bottom-color: transparent;
}

.tab-active {
  background: #e7f0f5;
  border-color: #8fb3c7;
}

.content-area {
  padding: 18px;
}

.view-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}

.panel {
  background: #ffffff;
  border: 1px solid #d8e0e5;
  border-radius: 8px;
  padding: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric {
  border: 1px solid #d8e0e5;
  border-radius: 8px;
  padding: 12px;
}

.metric span {
  display: block;
  color: #60707a;
  font-size: 13px;
}

.metric strong {
  display: block;
  margin-top: 6px;
  font-size: 22px;
}

.severity {
  display: inline-block;
  min-width: 68px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  text-align: center;
}

.severity-info { background: #e0f2fe; color: #075985; }
.severity-warning { background: #fef3c7; color: #92400e; }
.severity-critical { background: #fee2e2; color: #991b1b; }

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #d8e0e5;
  padding: 8px;
  text-align: left;
}

.event-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.event-list li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #edf1f4;
}
```

- [ ] **Step 6: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit layout and initial tabs**

Run:

```bash
git add src/App.tsx src/styles.css src/ui
git commit -m "feat: add dashboard and diagnostics views"
```

## Task 9: Build Time-Series Overlay View

**Files:**

- Create: `src/ui/ChannelPicker.tsx`
- Create: `src/ui/TimeSeriesView.tsx`
- Modify: `src/ui/Layout.tsx`

- [ ] **Step 1: Create channel picker**

Create `src/ui/ChannelPicker.tsx`:

```tsx
import type { OverlayPreset, VehicleProfile } from "../domain/types";

export function ChannelPicker({
  profile,
  selectedOverlay,
  onOverlayChange
}: {
  profile: VehicleProfile;
  selectedOverlay: OverlayPreset | null;
  onOverlayChange: (overlay: OverlayPreset) => void;
}) {
  return (
    <label className="field-row">
      Overlay
      <select
        value={selectedOverlay?.id ?? ""}
        onChange={(event) => {
          const overlay = profile.overlays.find((item) => item.id === event.target.value);
          if (overlay) onOverlayChange(overlay);
        }}
      >
        {profile.overlays.map((overlay) => (
          <option key={overlay.id} value={overlay.id}>
            {overlay.name}
          </option>
        ))}
      </select>
    </label>
  );
}
```

- [ ] **Step 2: Create time-series view**

Create `src/ui/TimeSeriesView.tsx`:

```tsx
import Plot from "react-plotly.js";
import { useSessionStore } from "../state/sessionStore";
import { ChannelPicker } from "./ChannelPicker";

function normalize(values: Array<number | null>) {
  const numeric = values.filter((value): value is number => typeof value === "number");
  if (numeric.length === 0) return values.map(() => null);
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  if (max === min) return values.map((value) => (value === null ? null : 50));
  return values.map((value) => (value === null ? null : ((value - min) / (max - min)) * 100));
}

export function TimeSeriesView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);
  const selectedOverlay = useSessionStore((state) => state.selectedOverlay);
  const setSelectedOverlay = useSessionStore((state) => state.setSelectedOverlay);

  if (!session) return <section className="empty-state">Open a CSV to plot channels.</section>;
  const profile = profiles.find((item) => item.id === session.profileId) ?? profiles[0];
  const overlay = selectedOverlay ?? profile.overlays[0];
  const x = session.log.rows.map((row) => row.timestampSec);

  const traces = overlay.channelIds.map((channelId, index) => {
    const channel = profile.channels[channelId];
    const rawY = session.log.rows.map((row) => row.values[channelId]);
    const y = overlay.mode === "normalized" ? normalize(rawY) : rawY;
    return {
      x,
      y,
      name: channel?.displayName ?? channelId,
      type: "scatter" as const,
      mode: "lines" as const,
      line: { color: channel?.color },
      yaxis: overlay.mode === "normalized" ? "y" : index === 0 ? "y" : `y${index + 1}`
    };
  });

  return (
    <section className="panel">
      <div className="view-toolbar">
        <h2>Time-Series Graph</h2>
        <ChannelPicker profile={profile} selectedOverlay={overlay} onOverlayChange={setSelectedOverlay} />
      </div>
      <Plot
        data={traces}
        layout={{
          autosize: true,
          height: 620,
          margin: { l: 50, r: 50, t: 20, b: 50 },
          xaxis: { title: "Time (s)" },
          yaxis: { title: overlay.mode === "normalized" ? "Normalized (%)" : undefined },
          showlegend: true
        }}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </section>
  );
}
```

- [ ] **Step 3: Wire view into layout**

Modify `src/ui/Layout.tsx`:

```tsx
import { TimeSeriesView } from "./TimeSeriesView";
```

Replace the temporary time-series empty state:

```tsx
{activeTab === "time-series" && <TimeSeriesView />}
```

Append CSS:

```css
.view-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.view-toolbar h2 {
  margin: 0;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
```

- [ ] **Step 4: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit time-series view**

Run:

```bash
git add src/ui/ChannelPicker.tsx src/ui/TimeSeriesView.tsx src/ui/Layout.tsx src/styles.css
git commit -m "feat: graph configurable channel overlays"
```

## Task 10: Build Vehicle Behavior View

**Files:**

- Create: `src/ui/BehaviorView.tsx`
- Modify: `src/ui/Layout.tsx`

- [ ] **Step 1: Create G-G and car attitude view**

Create `src/ui/BehaviorView.tsx`:

```tsx
import Plot from "react-plotly.js";
import { Canvas } from "@react-three/fiber";
import { useSessionStore } from "../state/sessionStore";

function latestValue(values: Array<number | null>) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    const value = values[index];
    if (typeof value === "number") return value;
  }
  return 0;
}

function CarModel({ rollDeg, pitchDeg, yawDeg }: { rollDeg: number; pitchDeg: number; yawDeg: number }) {
  return (
    <mesh rotation={[pitchDeg * Math.PI / 180, yawDeg * Math.PI / 180, rollDeg * Math.PI / 180]}>
      <boxGeometry args={[2.6, 0.35, 1.2]} />
      <meshStandardMaterial color="#2f6f8f" />
    </mesh>
  );
}

export function BehaviorView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to inspect vehicle behavior.</section>;

  const x = session.log.rows.map((row) => row.values.ax_corrected_g);
  const y = session.log.rows.map((row) => row.values.ay_corrected_g);
  const rollRate = latestValue(session.log.rows.map((row) => row.values.gx_dps));
  const pitchRate = latestValue(session.log.rows.map((row) => row.values.gy_dps));
  const yawRate = latestValue(session.log.rows.map((row) => row.values.gz_dps));

  return (
    <section className="view-grid">
      <div className="panel">
        <h2>G-G Diagram</h2>
        <Plot
          data={[{ x, y, type: "scatter", mode: "markers", name: "Corrected G", marker: { size: 7, color: "#2563eb" } }]}
          layout={{
            height: 560,
            margin: { l: 50, r: 20, t: 20, b: 50 },
            xaxis: { title: "Longitudinal G", zeroline: true },
            yaxis: { title: "Lateral G", zeroline: true, scaleanchor: "x" }
          }}
          useResizeHandler
          style={{ width: "100%" }}
        />
      </div>
      <div className="panel">
        <h2>Vehicle Attitude Tendency</h2>
        <p className="confidence-note">IMU-only attitude is shown as tendency visualization, not precision attitude estimation.</p>
        <div className="car-canvas">
          <Canvas camera={{ position: [0, 3, 5], fov: 45 }}>
            <ambientLight intensity={0.8} />
            <directionalLight position={[3, 5, 2]} intensity={1.2} />
            <CarModel rollDeg={rollRate * 0.08} pitchDeg={pitchRate * 0.08} yawDeg={yawRate * 0.04} />
          </Canvas>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Wire view into layout**

Modify `src/ui/Layout.tsx`:

```tsx
import { BehaviorView } from "./BehaviorView";
```

Replace the temporary behavior empty state:

```tsx
{activeTab === "behavior" && <BehaviorView />}
```

Append CSS:

```css
.confidence-note {
  color: #7c2d12;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  padding: 10px;
  border-radius: 6px;
}

.car-canvas {
  height: 360px;
  border: 1px solid #d8e0e5;
  border-radius: 8px;
  background: #eef3f6;
}
```

- [ ] **Step 3: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit behavior view**

Run:

```bash
git add src/ui/BehaviorView.tsx src/ui/Layout.tsx src/styles.css
git commit -m "feat: visualize vehicle behavior"
```

## Task 11: Build Map / Lap Coordinate Fallback View

**Files:**

- Create: `src/ui/MapLapView.tsx`
- Modify: `src/state/sessionStore.ts`
- Modify: `src/ui/Layout.tsx`

- [ ] **Step 1: Confirm manual segment support**

Confirm `src/state/sessionStore.ts` includes this action in `SessionStore`:

```ts
addManualSegment: (name: string, startSec: number, endSec: number) => void;
```

Confirm the implementation appends `createManualSegment(name, startSec, endSec)` to `session.segments`.

- [ ] **Step 2: Create coordinate-path map/lap view**

Create `src/ui/MapLapView.tsx`:

```tsx
import { useState } from "react";
import Plot from "react-plotly.js";
import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

export function MapLapView() {
  const session = useSessionStore((state) => state.session);
  const addManualSegment = useSessionStore((state) => state.addManualSegment);
  const [name, setName] = useState("Manual Segment");
  const [startSec, setStartSec] = useState("0");
  const [endSec, setEndSec] = useState("1");

  if (!session) return <section className="empty-state">Open a CSV to inspect GPS path and segments.</section>;

  const lat = session.log.rows.map((row) => row.values.Latitude);
  const lon = session.log.rows.map((row) => row.values.Longitude);
  const speed = session.log.rows.map((row) => row.values.GPS_Speed_KPH ?? row.values.VSS_kmh);

  return (
    <section className="view-grid">
      <div className="panel">
        <h2>GPS Path</h2>
        <p className="confidence-note">Offline coordinate plot. Online map tiles can be added over this path in a follow-up task.</p>
        <Plot
          data={[{ x: lon, y: lat, mode: "markers+lines", type: "scatter", marker: { color: speed, colorscale: "Viridis", showscale: true } }]}
          layout={{
            height: 560,
            margin: { l: 50, r: 20, t: 20, b: 50 },
            xaxis: { title: "Longitude" },
            yaxis: { title: "Latitude", scaleanchor: "x" }
          }}
          useResizeHandler
          style={{ width: "100%" }}
        />
      </div>
      <div className="panel">
        <h2>Segments</h2>
        <form
          className="segment-form"
          onSubmit={(event) => {
            event.preventDefault();
            addManualSegment(name, Number(startSec), Number(endSec));
          }}
        >
          <input value={name} onChange={(event) => setName(event.target.value)} aria-label="Segment name" />
          <input value={startSec} onChange={(event) => setStartSec(event.target.value)} aria-label="Segment start seconds" />
          <input value={endSec} onChange={(event) => setEndSec(event.target.value)} aria-label="Segment end seconds" />
          <button type="submit">Add Segment</button>
        </form>
        <ul className="event-list">
          {session.segments.map((segment) => {
            const event = session.events.find((item) => `segment-${item.id}` === segment.id);
            return (
              <li key={segment.id}>
                {event ? <SeverityBadge severity={event.severity} /> : <span className="severity severity-info">manual</span>}
                <span>{segment.name}</span>
                <span>{segment.startSec.toFixed(2)}-{segment.endSec.toFixed(2)} s</span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Wire view into layout**

Modify `src/ui/Layout.tsx`:

```tsx
import { MapLapView } from "./MapLapView";
```

Replace the temporary map empty state:

```tsx
{activeTab === "map-lap" && <MapLapView />}
```

- [ ] **Step 4: Add segment form styles**

Append CSS:

```css
.segment-form {
  display: grid;
  grid-template-columns: 1fr 90px 90px auto;
  gap: 8px;
  margin-bottom: 12px;
}

input {
  border: 1px solid #a9b4bc;
  border-radius: 6px;
  padding: 8px 10px;
  font: inherit;
}
```

- [ ] **Step 5: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit map/lap fallback**

Run:

```bash
git add src/state/sessionStore.ts src/ui/MapLapView.tsx src/ui/Layout.tsx src/styles.css
git commit -m "feat: show offline GPS path and event segments"
```

## Task 12: Build Report And Settings Views

**Files:**

- Create: `src/ui/ReportView.tsx`
- Create: `src/ui/SettingsView.tsx`
- Modify: `src/ui/Layout.tsx`
- Modify: `src/state/sessionStore.ts`

- [ ] **Step 1: Confirm profile update action**

Confirm `SessionStore` in `src/state/sessionStore.ts` includes:

```ts
updateProfile: (profile: VehicleProfile) => void;
```

Confirm the implementation inside `create` updates the matching profile by id:

```ts
updateProfile: (profile) => {
  set((state) => ({
    profiles: state.profiles.map((item) => (item.id === profile.id ? profile : item))
  }));
},
```

- [ ] **Step 2: Create report view**

Create `src/ui/ReportView.tsx`:

```tsx
import { buildReportHtml } from "../domain/reportHtml";
import { summarizeLog } from "../domain/summary";
import { useSessionStore } from "../state/sessionStore";

export function ReportView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);

  if (!session) return <section className="empty-state">Open a CSV to generate a report.</section>;
  const profile = profiles.find((item) => item.id === session.profileId) ?? profiles[0];
  const summary = summarizeLog(session.log, session.events);
  const html = buildReportHtml({ log: session.log, profile, events: session.events, diagnostics: session.diagnostics, summary });

  return (
    <section className="panel">
      <div className="view-toolbar">
        <h2>Report</h2>
        <button type="button" onClick={() => void window.mfLogAnalyzer?.saveHtmlReport(html)}>
          Save HTML
        </button>
      </div>
      <iframe title="Report preview" className="report-preview" srcDoc={html} />
    </section>
  );
}
```

- [ ] **Step 3: Create settings view**

Create `src/ui/SettingsView.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import type { VehicleProfile } from "../domain/types";
import { useSessionStore } from "../state/sessionStore";

export function SettingsView() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const updateProfile = useSessionStore((state) => state.updateProfile);
  const profile = profiles.find((item) => item.id === selectedProfileId) ?? profiles[0];
  const profileJson = useMemo(() => JSON.stringify(profile, null, 2), [profile]);
  const [draft, setDraft] = useState(profileJson);
  const [message, setMessage] = useState("Edit JSON, then apply to update this profile.");

  useEffect(() => {
    setDraft(profileJson);
    setMessage("Edit JSON, then apply to update this profile.");
  }, [profileJson]);

  function applyProfileJson() {
    try {
      const parsed = JSON.parse(draft) as VehicleProfile;
      if (parsed.id !== profile.id) {
        setMessage(`Profile id must remain ${profile.id}.`);
        return;
      }
      updateProfile({ ...parsed, revision: new Date().toISOString() });
      setMessage("Profile JSON applied. Re-open the CSV to run analysis with changed mappings or rules.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Invalid JSON.");
    }
  }

  return (
    <section className="view-grid">
      <div className="panel">
        <h2>Profile</h2>
        <dl className="settings-list">
          <dt>Name</dt><dd>{profile.name}</dd>
          <dt>Revision</dt><dd>{profile.revision}</dd>
          <dt>Channels</dt><dd>{Object.keys(profile.channels).length}</dd>
          <dt>Rules</dt><dd>{profile.rules.length}</dd>
          <dt>Overlay Presets</dt><dd>{profile.overlays.length}</dd>
        </dl>
      </div>
      <div className="panel">
        <h2>Channel Mapping</h2>
        <table className="data-table">
          <thead>
            <tr><th>Channel</th><th>Sources</th><th>Unit</th><th>Calibration</th></tr>
          </thead>
          <tbody>
            {Object.values(profile.channels).map((channel) => (
              <tr key={channel.id}>
                <td>{channel.displayName}</td>
                <td>{channel.sourceColumns.join(", ")}</td>
                <td>{channel.unit}</td>
                <td>{channel.calibration.type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel panel-wide">
        <div className="view-toolbar">
          <h2>Profile JSON Editor</h2>
          <button type="button" onClick={applyProfileJson}>Apply JSON</button>
        </div>
        <p>{message}</p>
        <textarea className="json-editor" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} />
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire views into layout**

Modify `src/ui/Layout.tsx`:

```tsx
import { ReportView } from "./ReportView";
import { SettingsView } from "./SettingsView";
```

Replace the temporary report and settings empty states:

```tsx
{activeTab === "report" && <ReportView />}
{activeTab === "settings" && <SettingsView />}
```

Append CSS:

```css
.report-preview {
  width: 100%;
  min-height: 680px;
  border: 1px solid #d8e0e5;
  border-radius: 8px;
  background: #ffffff;
}

.settings-list {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px 12px;
}

.settings-list dt {
  color: #60707a;
}

.settings-list dd {
  margin: 0;
  font-weight: 600;
}

.panel-wide {
  grid-column: 1 / -1;
}

.json-editor {
  width: 100%;
  min-height: 420px;
  border: 1px solid #a9b4bc;
  border-radius: 8px;
  padding: 12px;
  font: 13px ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  resize: vertical;
}
```

- [ ] **Step 5: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit report and settings**

Run:

```bash
git add src/state/sessionStore.ts src/ui/ReportView.tsx src/ui/SettingsView.tsx src/ui/Layout.tsx src/styles.css
git commit -m "feat: preview reports and edit profile settings"
```

## Task 13: Add Pop-Out View Support

**Files:**

- Modify: `electron/main.ts`
- Modify: `electron/preload.ts`
- Modify: `src/state/sessionStore.ts`
- Modify: `src/App.tsx`
- Create: `src/ui/PopoutButton.tsx`
- Modify: `src/ui/Layout.tsx`

- [ ] **Step 1: Add session snapshot IPC to Electron main**

Modify `electron/main.ts` by adding this near the top-level variables:

```ts
let latestSessionSnapshot: unknown = null;
```

Add these IPC handlers after the existing `view:popout` handler:

```ts
ipcMain.handle("session:setSnapshot", async (_event, snapshot: unknown) => {
  latestSessionSnapshot = snapshot;
  return true;
});

ipcMain.handle("session:getSnapshot", async () => latestSessionSnapshot);
```

- [ ] **Step 2: Extend preload desktop API**

Modify `electron/preload.ts`:

```ts
export type DesktopApi = {
  openCsv: () => Promise<{ filePath: string; text: string } | null>;
  saveHtmlReport: (html: string) => Promise<string | null>;
  popout: (route: string) => Promise<boolean>;
  setSessionSnapshot: (snapshot: unknown) => Promise<boolean>;
  getSessionSnapshot: () => Promise<unknown | null>;
};
```

Update the `api` object:

```ts
const api: DesktopApi = {
  openCsv: () => ipcRenderer.invoke("file:openCsv"),
  saveHtmlReport: (html) => ipcRenderer.invoke("file:saveHtmlReport", html),
  popout: (route) => ipcRenderer.invoke("view:popout", route),
  setSessionSnapshot: (snapshot) => ipcRenderer.invoke("session:setSnapshot", snapshot),
  getSessionSnapshot: () => ipcRenderer.invoke("session:getSnapshot")
};
```

- [ ] **Step 3: Add cross-window selection sync**

Append to `src/state/sessionStore.ts`:

```ts
type SelectionSyncMessage = {
  type: "selection";
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlayId: string | null;
};

const syncChannel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("mf-log-analyzer-selection") : null;

function postSelectionSync() {
  const state = useSessionStore.getState();
  syncChannel?.postMessage({
    type: "selection",
    currentTimeSec: state.currentTimeSec,
    selectedEventId: state.selectedEventId,
    selectedOverlayId: state.selectedOverlay?.id ?? null
  } satisfies SelectionSyncMessage);
}

export function startCrossWindowSelectionSync() {
  if (!syncChannel) return () => undefined;
  syncChannel.onmessage = (event: MessageEvent<SelectionSyncMessage>) => {
    if (event.data.type !== "selection") return;
    const state = useSessionStore.getState();
    const profile = state.profiles.find((item) => item.id === state.selectedProfileId);
    const selectedOverlay = profile?.overlays.find((item) => item.id === event.data.selectedOverlayId) ?? state.selectedOverlay;
    useSessionStore.setState({
      currentTimeSec: event.data.currentTimeSec,
      selectedEventId: event.data.selectedEventId,
      selectedOverlay
    });
  };
  return () => {
    syncChannel.onmessage = null;
  };
}
```

Replace the simple setters in `src/state/sessionStore.ts`:

```ts
setCurrentTimeSec: (currentTimeSec) => {
  set({ currentTimeSec });
  postSelectionSync();
},
setSelectedEventId: (selectedEventId) => {
  set({ selectedEventId });
  postSelectionSync();
},
setSelectedOverlay: (selectedOverlay) => {
  set({ selectedOverlay });
  postSelectionSync();
},
```

- [ ] **Step 4: Start snapshot hydration and selection sync in App**

Modify the `src/App.tsx` import:

```tsx
import { hydrateSessionSnapshot, startCrossWindowSelectionSync, useSessionStore } from "./state/sessionStore";
```

Replace the existing hydration effect:

```tsx
useEffect(() => {
  void hydrateSessionSnapshot();
  return startCrossWindowSelectionSync();
}, []);
```

- [ ] **Step 5: Create pop-out button**

Create `src/ui/PopoutButton.tsx`:

```tsx
import { publishSessionSnapshot } from "../state/sessionStore";
import type { TabId } from "./Tabs";

const routes: Record<TabId, string> = {
  summary: "/summary",
  diagnostics: "/diagnostics",
  "time-series": "/time-series",
  behavior: "/behavior",
  "map-lap": "/map-lap",
  report: "/report",
  settings: "/settings"
};

export function PopoutButton({ tab }: { tab: TabId }) {
  return (
    <button
      type="button"
      onClick={async () => {
        await publishSessionSnapshot();
        await window.mfLogAnalyzer?.popout(routes[tab]);
      }}
    >
      Open in New Window
    </button>
  );
}
```

- [ ] **Step 6: Add pop-out control to layout**

Modify `src/ui/Layout.tsx` to import `PopoutButton`:

```tsx
import { PopoutButton } from "./PopoutButton";
```

Wrap the content area header:

```tsx
<div className="content-toolbar">
  <PopoutButton tab={activeTab} />
</div>
```

Place it immediately before tab-specific content inside `content-area`.

Append CSS:

```css
.content-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
```

- [ ] **Step 7: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit pop-out support**

Run:

```bash
git add electron/main.ts electron/preload.ts src/state/sessionStore.ts src/App.tsx src/ui/PopoutButton.tsx src/ui/Layout.tsx src/styles.css
git commit -m "feat: add pop-out analysis views"
```

## Task 14: Add Smoke Test And Final Verification

**Files:**

- Create: `tests/e2e/app-smoke.spec.ts`
- Modify: `package.json`

- [ ] **Step 1: Write browser smoke test**

Create `tests/e2e/app-smoke.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test("renders MF Log Analyzer shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "MF Log Analyzer" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open CSV" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Summary" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Vehicle Behavior" })).toBeVisible();
});
```

- [ ] **Step 2: Run all unit tests**

Run:

```bash
npm test
```

Expected: all domain tests PASS.

- [ ] **Step 3: Run build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 4: Run smoke test**

Run:

```bash
npm run test:e2e
```

Expected: Playwright test PASS.

- [ ] **Step 5: Manually launch development app**

Run:

```bash
npm run electron:dev
```

Expected:

- Desktop app window opens.
- `MF Log Analyzer` heading is visible.
- Vehicle profile dropdown includes `2025 Vehicle` and `2026 Vehicle`.
- Tabs are visible.
- Opening `tests/fixtures/2025-sample.csv` loads an analysis session.
- Summary tab shows max speed, max RPM, corrected G, and critical event count.
- Diagnostics tab shows low battery and ADXL scale findings.
- Time-Series tab shows overlay graph.
- Vehicle Behavior tab shows G-G diagram and simple car model.
- Map / Lap tab shows coordinate path.
- Report tab previews HTML.
- Settings tab lists profile channels.

- [ ] **Step 6: Commit smoke test**

Run:

```bash
git add tests/e2e/app-smoke.spec.ts package.json
git commit -m "test: verify app shell smoke flow"
```

## Self-Review Checklist

- Spec coverage:
  - Vehicle profiles: Task 2
  - CSV import and `EOT_IN` alias: Tasks 2-3
  - ADXL345 `/8` correction: Tasks 2-3
  - Log diagnostics: Task 4
  - Event rules: Task 5
  - Summary: Task 8
  - Time-series overlays: Task 9
  - G-G diagram and car attitude visualization: Task 10
  - Map / Lap coordinate fallback: Task 11
  - Report HTML export: Tasks 6 and 12
  - Settings JSON editor and profile foundation: Task 12
  - Pop-out views with session snapshot and selection sync: Task 13
- Known scoped follow-ups are listed in Scope Check.
- No temporary empty-state sections remain for implemented views in the vertical slice.
- Type names used across tasks are consistent: `VehicleProfile`, `SensorChannel`, `AppliedLog`, `DiagnosticFinding`, `DetectedEvent`, `Segment`, `AnalysisSession`.
- Every task has a verification command and a commit step.
