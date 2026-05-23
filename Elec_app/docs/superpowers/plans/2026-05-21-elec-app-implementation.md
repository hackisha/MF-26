# Elec App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first offline-first Elec App MVP that imports EasyEDA JSON, classifies components, traces ECU-to-connector-to-target wiring, and provides field debugging reference views.

**Architecture:** Use a static Vite React TypeScript app with domain logic isolated from UI. Parser, graph tracing, classification, update matching, and persistence live in focused modules with Vitest coverage before UI wiring.

**Tech Stack:** Vite, React, TypeScript, Vitest, Testing Library, IndexedDB browser APIs, CSS modules/plain CSS, PWA manifest/service worker.

---

## Scope Check

The design spec covers several subsystems, but they are tightly connected around one field-debugging MVP. This plan builds a usable local app in vertical slices: scaffold, parser, graph, classification, persistence, UI views, attachments, update flow, and offline packaging.

## File Structure

- `package.json`: npm scripts and dependencies.
- `index.html`: app entry HTML.
- `vite.config.ts`: Vite and Vitest config.
- `tsconfig.json`, `tsconfig.node.json`: TypeScript config.
- `src/main.tsx`: React bootstrap.
- `src/App.tsx`: top-level app state and routing between tabs.
- `src/styles.css`: practical field-oriented UI styles.
- `src/domain/types.ts`: normalized project, component, pin, graph, note, measurement, attachment types.
- `src/domain/easyedaParser.ts`: EasyEDA JSON parser.
- `src/domain/connectivity.ts`: graph construction and trace logic.
- `src/domain/classification.ts`: auto-classification and review queue logic.
- `src/domain/updateMatcher.ts`: matching old project metadata to a new import.
- `src/storage/projectStore.ts`: local project save/load/export/import.
- `src/storage/attachmentStore.ts`: IndexedDB attachment persistence.
- `src/ui/ProjectHome.tsx`: project open/import/export entry view.
- `src/ui/ImportAnalysis.tsx`: upload summary and parse warnings.
- `src/ui/ClassificationQueue.tsx`: ambiguous component confirmation.
- `src/ui/SearchDebugger.tsx`: search and trace results.
- `src/ui/ConnectorPinout.tsx`: connector pinout table.
- `src/ui/ComponentInfoPanel.tsx`: click/hover detail panel.
- `src/ui/ReferenceTabs.tsx`: wiring diagram, datasheet, and regulation file/link views.
- `src/ui/NotesMeasurements.tsx`: shared notes and measurement editors.
- `src/ui/UpdateSummary.tsx`: schematic update matching review.
- `src/utils/fileHash.ts`: source file hash utility.
- `src/utils/search.ts`: search indexing and matching.
- `src/test/fixtures/sampleSummary.ts`: expected counts from the provided EasyEDA file.
- `src/**/*.test.ts`, `src/**/*.test.tsx`: unit and UI tests.
- `public/manifest.webmanifest`: PWA metadata.
- `public/sw.js`: simple offline service worker.

## Task 1: Initialize Project Scaffold

**Files:**
- Create: `package.json`
- Create: `index.html`
- Create: `vite.config.ts`
- Create: `tsconfig.json`
- Create: `tsconfig.node.json`
- Create: `src/main.tsx`
- Create: `src/App.tsx`
- Create: `src/styles.css`
- Create: `.gitignore`

- [ ] **Step 1: Initialize git repository**

Run:

```powershell
git init
```

Expected: output includes `Initialized empty Git repository`.

- [ ] **Step 2: Create npm package metadata**

Create `package.json`:

```json
{
  "name": "elec-app",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "tsc -b --pretty false"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "vite": "^7.0.0",
    "typescript": "^5.8.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "jsdom": "^25.0.0",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 3: Install dependencies**

Run:

```powershell
npm install
```

Expected: command exits 0 and creates `package-lock.json`.

- [ ] **Step 4: Create Vite and TypeScript config**

Create `vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"]
  }
});
```

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
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create React entry files**

Create `index.html`:

```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Elec App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

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
          <h1>Elec App</h1>
          <p>MF-26 engine/elec wiring debugger</p>
        </div>
      </header>
      <section className="empty-state">
        <h2>프로젝트 준비 중</h2>
        <p>EasyEDA JSON을 분석하는 오프라인 배선 디버거를 구성합니다.</p>
      </section>
    </main>
  );
}
```

Create `src/styles.css`:

```css
:root {
  color: #172026;
  background: #f5f7f8;
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
}

body {
  margin: 0;
}

button,
input,
select,
textarea {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
}

.topbar {
  background: #12343b;
  color: white;
  padding: 18px 24px;
}

.topbar h1 {
  margin: 0;
  font-size: 24px;
}

.topbar p {
  margin: 4px 0 0;
  color: #cde3e7;
}

.empty-state {
  margin: 24px;
  padding: 24px;
  background: white;
  border: 1px solid #d9e2e5;
  border-radius: 8px;
}
```

Create `.gitignore`:

```gitignore
node_modules/
dist/
.superpowers/
*.log
```

- [ ] **Step 6: Add Vitest setup**

Create `src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: Verify scaffold**

Run:

```powershell
npm run build
npm test
```

Expected: build exits 0 and Vitest reports no test files or all tests pass.

- [ ] **Step 8: Commit scaffold**

Run:

```powershell
git add .
git commit -m "chore: scaffold elec app"
```

Expected: commit succeeds.

## Task 2: Define Domain Types and Fixture Expectations

**Files:**
- Create: `src/domain/types.ts`
- Create: `src/test/fixtures/sampleSummary.ts`
- Create: `src/domain/types.test.ts`

- [ ] **Step 1: Write type smoke test**

Create `src/domain/types.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { ComponentRole, ElecProject } from "./types";

describe("domain types", () => {
  it("allows an empty project with known component roles", () => {
    const role: ComponentRole = "connector";
    const project: ElecProject = {
      id: "project-1",
      name: "MF-26",
      createdAt: "2026-05-21T00:00:00.000Z",
      updatedAt: "2026-05-21T00:00:00.000Z",
      source: null,
      components: [],
      graph: { nodes: [], edges: [] },
      classifications: {},
      notes: [],
      measurements: [],
      attachments: []
    };

    expect(role).toBe("connector");
    expect(project.components).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm test -- src/domain/types.test.ts
```

Expected: FAIL because `src/domain/types.ts` does not exist.

- [ ] **Step 3: Add domain types**

Create `src/domain/types.ts`:

```ts
export type ComponentRole =
  | "ecu"
  | "connector"
  | "sensor"
  | "actuator"
  | "power"
  | "other"
  | "unknown";

export type MeasurementStatus = "pass" | "fail" | "unknown";

export interface SourceSchematic {
  fileName: string;
  title: string;
  editorVersion: string;
  uploadedAt: string;
  hash: string;
  shapeCounts: Record<string, number>;
}

export interface Pin {
  id: string;
  componentId: string;
  number: string;
  label: string | null;
  x: number;
  y: number;
  raw: string;
}

export interface Component {
  id: string;
  sourceId: string;
  rawName: string;
  packageName: string;
  symbolName: string;
  alias: string;
  x: number;
  y: number;
  pins: Pin[];
  autoRole: ComponentRole;
  autoConfidence: number;
  confirmedRole: ComponentRole | null;
  raw: string;
}

export interface GraphNode {
  id: string;
  kind: "pin" | "wire-point" | "junction" | "label";
  x: number;
  y: number;
  label: string | null;
  refId: string | null;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  kind: "wire" | "pin-contact" | "label-contact";
  confidence: number;
}

export interface NetGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface UserClassification {
  componentId: string;
  role: ComponentRole;
  alias: string;
  confirmedAt: string;
}

export interface Note {
  id: string;
  targetType: "component" | "pin" | "regulation";
  targetId: string;
  body: string;
  updatedAt: string;
}

export interface Measurement {
  id: string;
  pinId: string;
  expectedValue: string;
  condition: string;
  measuredValue: string;
  status: MeasurementStatus;
  measuredAt: string;
  note: string;
}

export interface Attachment {
  id: string;
  targetType: "component" | "wiring-diagram" | "regulation";
  targetId: string | null;
  label: string;
  kind: "link" | "file";
  url: string | null;
  blobKey: string | null;
  mimeType: string | null;
}

export interface ElecProject {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  source: SourceSchematic | null;
  components: Component[];
  graph: NetGraph;
  classifications: Record<string, UserClassification>;
  notes: Note[];
  measurements: Measurement[];
  attachments: Attachment[];
}
```

- [ ] **Step 4: Add sample fixture summary**

Create `src/test/fixtures/sampleSummary.ts`:

```ts
export const sampleEasyEdaSummary = {
  fileName: "SCH_26.5.11-배선도_2026-05-19.json",
  schematicCount: 1,
  shapeCount: 1275,
  shapeCounts: {
    R: 74,
    T: 248,
    F: 9,
    W: 324,
    LIB: 39,
    N: 464,
    E: 10,
    PL: 12,
    O: 6,
    J: 89
  },
  knownSymbols: ["EMU_BLACK_SYMBOL", "EMU_GRAY_SYMBOL", "MOLEX_12PIN"]
} as const;
```

- [ ] **Step 5: Verify types pass**

Run:

```powershell
npm test -- src/domain/types.test.ts
npm run lint
```

Expected: PASS and TypeScript exits 0.

- [ ] **Step 6: Commit domain types**

Run:

```powershell
git add src/domain src/test
git commit -m "feat: define elec app domain types"
```

Expected: commit succeeds.

## Task 3: Implement EasyEDA Parser

**Files:**
- Create: `src/domain/easyedaParser.ts`
- Create: `src/domain/easyedaParser.test.ts`
- Modify: `src/domain/types.ts`

- [ ] **Step 1: Write parser tests**

Create `src/domain/easyedaParser.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseEasyEdaSchematic } from "./easyedaParser";

const fixture = {
  editorVersion: "6.5.51",
  title: "fixture",
  schematics: [
    {
      dataStr: {
        shape: [
          "W~0 0 10 0~#000000~1~0~none~wire1~0",
          "J~10~0~2.5~#CC0000~junction1~0",
          "F~part_netLabel_VCC~10~0~0~label1~~0^^10~0^^+12V~#FF0000~0~0~0~start~1~Times New Roman~9pt",
          "LIB~100~200~package`MOLEX_12PIN_FOOTPRINT`spiceSymbolName`MOLEX_12PIN`~~0~src-molex#@$T~N~100~190~0~#000080~Arial~~~~~comment~Main Connector~1~start~text1~0~pinpart#@$P~show~1~1~90~200~180~pin1~0^^90~200^^M 90 200 h 10~#880000^^1~100#@$P~show~1~2~90~210~180~pin2~0^^90~210^^M 90 210 h 10~#880000^^1~100"
        ]
      }
    }
  ]
};

describe("parseEasyEdaSchematic", () => {
  it("extracts counts, components, pins, wires, junctions, and labels", async () => {
    const result = await parseEasyEdaSchematic({
      fileName: "fixture.json",
      text: JSON.stringify(fixture),
      uploadedAt: "2026-05-21T00:00:00.000Z",
      hash: "hash-1"
    });

    expect(result.source.shapeCounts).toMatchObject({ W: 1, J: 1, F: 1, LIB: 1 });
    expect(result.components).toHaveLength(1);
    expect(result.components[0].symbolName).toBe("MOLEX_12PIN");
    expect(result.components[0].pins.map((pin) => pin.number)).toEqual(["1", "2"]);
    expect(result.wires).toHaveLength(1);
    expect(result.junctions).toHaveLength(1);
    expect(result.labels[0].label).toBe("+12V");
  });

  it("returns warnings instead of throwing on unsupported shapes", async () => {
    const result = await parseEasyEdaSchematic({
      fileName: "fixture.json",
      text: JSON.stringify({ ...fixture, schematics: [{ dataStr: { shape: ["ZZ~bad"] } }] }),
      uploadedAt: "2026-05-21T00:00:00.000Z",
      hash: "hash-2"
    });

    expect(result.warnings[0]).toContain("Unsupported shape type: ZZ");
  });
});
```

- [ ] **Step 2: Run parser tests to verify failure**

Run:

```powershell
npm test -- src/domain/easyedaParser.test.ts
```

Expected: FAIL because parser module does not exist.

- [ ] **Step 3: Add parser result types**

Append to `src/domain/types.ts`:

```ts
export interface WireSegment {
  id: string;
  points: Array<{ x: number; y: number }>;
  raw: string;
}

export interface Junction {
  id: string;
  x: number;
  y: number;
  raw: string;
}

export interface NetLabel {
  id: string;
  x: number;
  y: number;
  label: string;
  raw: string;
}

export interface ParseWarning {
  shape: string;
  message: string;
}

export interface ParsedSchematic {
  source: SourceSchematic;
  components: Component[];
  wires: WireSegment[];
  junctions: Junction[];
  labels: NetLabel[];
  warnings: string[];
}
```

- [ ] **Step 4: Implement parser**

Create `src/domain/easyedaParser.ts`:

```ts
import type {
  Component,
  Junction,
  NetLabel,
  ParsedSchematic,
  Pin,
  SourceSchematic,
  WireSegment
} from "./types";
import { classifyComponent } from "./classification";

interface ParseInput {
  fileName: string;
  text: string;
  uploadedAt: string;
  hash: string;
}

function getShapeType(shape: string): string {
  return shape.split("~", 1)[0] || "UNKNOWN";
}

function readBacktickProperty(raw: string, key: string): string {
  const marker = `${key}\``;
  const start = raw.indexOf(marker);
  if (start < 0) return "";
  const valueStart = start + marker.length;
  const valueEnd = raw.indexOf("`", valueStart);
  if (valueEnd < 0) return raw.slice(valueStart);
  return raw.slice(valueStart, valueEnd);
}

function toNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseWire(shape: string): WireSegment {
  const fields = shape.split("~");
  const coordinateTokens = (fields[1] ?? "")
    .trim()
    .split(/\s+/)
    .map(Number)
    .filter(Number.isFinite);

  const points = [];
  for (let i = 0; i < coordinateTokens.length; i += 2) {
    points.push({ x: coordinateTokens[i], y: coordinateTokens[i + 1] });
  }

  return {
    id: fields[6] || `wire-${shape}`,
    points,
    raw: shape
  };
}

function parseJunction(shape: string): Junction {
  const fields = shape.split("~");
  return {
    id: fields[5] || `junction-${fields[1]}-${fields[2]}`,
    x: toNumber(fields[1]),
    y: toNumber(fields[2]),
    raw: shape
  };
}

function parseNetLabel(shape: string): NetLabel | null {
  const fields = shape.split("~");
  const payload = shape.split("^^");
  const label = payload[2]?.split("~")[0];
  if (!label) return null;

  return {
    id: fields[4] || `label-${fields[2]}-${fields[3]}`,
    x: toNumber(fields[2]),
    y: toNumber(fields[3]),
    label,
    raw: shape
  };
}

function parsePin(componentId: string, segment: string): Pin | null {
  const fields = segment.split("~");
  if (fields[0] !== "P") return null;
  const number = fields[3];
  const x = toNumber(fields[4]);
  const y = toNumber(fields[5]);
  const pinId = fields[7] || `${componentId}-pin-${number}`;

  return {
    id: pinId,
    componentId,
    number,
    label: null,
    x,
    y,
    raw: segment
  };
}

function parseComponent(shape: string): Component {
  const segments = shape.split("#@$");
  const header = segments[0];
  const fields = header.split("~");
  const sourceId = fields[7] || fields[6] || `component-${fields[1]}-${fields[2]}`;
  const packageName = readBacktickProperty(header, "package");
  const symbolName = readBacktickProperty(header, "spiceSymbolName");
  const textNames = segments
    .filter((segment) => segment.startsWith("T~"))
    .map((segment) => segment.split("~")[10])
    .filter(Boolean);
  const rawName = textNames[0] || symbolName || packageName || sourceId;
  const componentId = sourceId;
  const auto = classifyComponent({ packageName, symbolName, rawName, pinCount: 0 });
  const pins = segments
    .map((segment) => parsePin(componentId, segment))
    .filter((pin): pin is Pin => Boolean(pin));

  const autoWithPins = classifyComponent({
    packageName,
    symbolName,
    rawName,
    pinCount: pins.length
  });

  return {
    id: componentId,
    sourceId,
    rawName,
    packageName,
    symbolName,
    alias: rawName,
    x: toNumber(fields[1]),
    y: toNumber(fields[2]),
    pins,
    autoRole: autoWithPins.role || auto.role,
    autoConfidence: autoWithPins.confidence || auto.confidence,
    confirmedRole: null,
    raw: shape
  };
}

export async function parseEasyEdaSchematic(input: ParseInput): Promise<ParsedSchematic> {
  const json = JSON.parse(input.text);
  const shapes: string[] = json.schematics?.flatMap(
    (sheet: { dataStr?: { shape?: string[] } }) => sheet.dataStr?.shape ?? []
  );

  if (!Array.isArray(shapes)) {
    throw new Error("지원하지 않는 EasyEDA 구조: schematics[].dataStr.shape[]가 없습니다.");
  }

  const source: SourceSchematic = {
    fileName: input.fileName,
    title: json.title ?? "",
    editorVersion: json.editorVersion ?? "",
    uploadedAt: input.uploadedAt,
    hash: input.hash,
    shapeCounts: {}
  };
  const components: Component[] = [];
  const wires: WireSegment[] = [];
  const junctions: Junction[] = [];
  const labels: NetLabel[] = [];
  const warnings: string[] = [];

  for (const shape of shapes) {
    const type = getShapeType(shape);
    source.shapeCounts[type] = (source.shapeCounts[type] ?? 0) + 1;

    if (type === "LIB") components.push(parseComponent(shape));
    else if (type === "W") wires.push(parseWire(shape));
    else if (type === "J") junctions.push(parseJunction(shape));
    else if (type === "F") {
      const label = parseNetLabel(shape);
      if (label) labels.push(label);
    } else if (!["R", "T", "N", "E", "PL", "O"].includes(type)) {
      warnings.push(`Unsupported shape type: ${type}`);
    }
  }

  return { source, components, wires, junctions, labels, warnings };
}
```

- [ ] **Step 5: Add temporary classification stub for parser dependency**

Create `src/domain/classification.ts`:

```ts
import type { ComponentRole } from "./types";

export interface ClassificationInput {
  packageName: string;
  symbolName: string;
  rawName: string;
  pinCount: number;
}

export interface ClassificationResult {
  role: ComponentRole;
  confidence: number;
  reason: string;
}

export function classifyComponent(input: ClassificationInput): ClassificationResult {
  const haystack = `${input.packageName} ${input.symbolName} ${input.rawName}`.toUpperCase();
  if (haystack.includes("EMU_")) {
    return { role: "ecu", confidence: 0.9, reason: "EMU symbol/package name" };
  }
  if (haystack.includes("MOLEX") || haystack.includes("HDR-")) {
    return { role: "connector", confidence: 0.75, reason: "connector-like symbol/package name" };
  }
  return { role: "unknown", confidence: 0.2, reason: "no strong rule matched" };
}
```

- [ ] **Step 6: Verify parser**

Run:

```powershell
npm test -- src/domain/easyedaParser.test.ts
npm run lint
```

Expected: PASS.

- [ ] **Step 7: Commit parser**

Run:

```powershell
git add src/domain
git commit -m "feat: parse EasyEDA schematic exports"
```

Expected: commit succeeds.

## Task 4: Build Connectivity Graph and Trace Logic

**Files:**
- Create: `src/domain/connectivity.ts`
- Create: `src/domain/connectivity.test.ts`

- [ ] **Step 1: Write connectivity tests**

Create `src/domain/connectivity.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Component, ParsedSchematic } from "./types";
import { buildConnectivityGraph, traceFromPin } from "./connectivity";

function component(id: string, role: Component["autoRole"], x: number, y: number): Component {
  return {
    id,
    sourceId: id,
    rawName: id,
    packageName: id,
    symbolName: id,
    alias: id,
    x,
    y,
    pins: [{ id: `${id}-1`, componentId: id, number: "1", label: null, x, y, raw: "" }],
    autoRole: role,
    autoConfidence: 1,
    confirmedRole: role,
    raw: ""
  };
}

describe("connectivity", () => {
  it("connects pins through wire endpoints and traces connected components", () => {
    const ecu = component("ecu", "ecu", 0, 0);
    const connector = component("connector", "connector", 10, 0);
    const sensor = component("sensor", "sensor", 20, 0);
    const parsed: ParsedSchematic = {
      source: {
        fileName: "fixture.json",
        title: "fixture",
        editorVersion: "6.5.51",
        uploadedAt: "2026-05-21T00:00:00.000Z",
        hash: "hash",
        shapeCounts: {}
      },
      components: [ecu, connector, sensor],
      wires: [
        { id: "w1", points: [{ x: 0, y: 0 }, { x: 10, y: 0 }], raw: "" },
        { id: "w2", points: [{ x: 10, y: 0 }, { x: 20, y: 0 }], raw: "" }
      ],
      junctions: [{ id: "j1", x: 10, y: 0, raw: "" }],
      labels: [],
      warnings: []
    };

    const graph = buildConnectivityGraph(parsed);
    const trace = traceFromPin(graph, parsed.components, "ecu-1");

    expect(trace.map((item) => item.componentId)).toEqual(["ecu", "connector", "sensor"]);
  });
});
```

- [ ] **Step 2: Run connectivity test to verify failure**

Run:

```powershell
npm test -- src/domain/connectivity.test.ts
```

Expected: FAIL because connectivity module does not exist.

- [ ] **Step 3: Implement connectivity graph**

Create `src/domain/connectivity.ts`:

```ts
import type { Component, GraphEdge, GraphNode, NetGraph, ParsedSchematic } from "./types";

const SNAP = 0.5;

function pointKey(x: number, y: number): string {
  return `${Math.round(x / SNAP) * SNAP}:${Math.round(y / SNAP) * SNAP}`;
}

function addNode(nodes: Map<string, GraphNode>, node: GraphNode): string {
  const key = pointKey(node.x, node.y);
  if (!nodes.has(key)) nodes.set(key, node);
  return nodes.get(key)!.id;
}

function edgeId(from: string, to: string, kind: GraphEdge["kind"]): string {
  return [kind, from, to].sort().join(":");
}

export function buildConnectivityGraph(parsed: ParsedSchematic): NetGraph {
  const nodesByPoint = new Map<string, GraphNode>();
  const edgesById = new Map<string, GraphEdge>();

  for (const wire of parsed.wires) {
    for (const point of wire.points) {
      addNode(nodesByPoint, {
        id: `wire:${point.x}:${point.y}`,
        kind: "wire-point",
        x: point.x,
        y: point.y,
        label: null,
        refId: wire.id
      });
    }
    for (let i = 0; i < wire.points.length - 1; i += 1) {
      const a = wire.points[i];
      const b = wire.points[i + 1];
      const from = addNode(nodesByPoint, {
        id: `wire:${a.x}:${a.y}`,
        kind: "wire-point",
        x: a.x,
        y: a.y,
        label: null,
        refId: wire.id
      });
      const to = addNode(nodesByPoint, {
        id: `wire:${b.x}:${b.y}`,
        kind: "wire-point",
        x: b.x,
        y: b.y,
        label: null,
        refId: wire.id
      });
      edgesById.set(edgeId(from, to, "wire"), {
        id: edgeId(from, to, "wire"),
        from,
        to,
        kind: "wire",
        confidence: 1
      });
    }
  }

  for (const junction of parsed.junctions) {
    addNode(nodesByPoint, {
      id: `junction:${junction.id}`,
      kind: "junction",
      x: junction.x,
      y: junction.y,
      label: null,
      refId: junction.id
    });
  }

  for (const label of parsed.labels) {
    addNode(nodesByPoint, {
      id: `label:${label.id}`,
      kind: "label",
      x: label.x,
      y: label.y,
      label: label.label,
      refId: label.id
    });
  }

  for (const component of parsed.components) {
    for (const pin of component.pins) {
      const pointNode = addNode(nodesByPoint, {
        id: `wire:${pin.x}:${pin.y}`,
        kind: "wire-point",
        x: pin.x,
        y: pin.y,
        label: null,
        refId: null
      });
      const pinNodeId = `pin:${pin.id}`;
      const pinNode: GraphNode = {
        id: pinNodeId,
        kind: "pin",
        x: pin.x,
        y: pin.y,
        label: pin.label,
        refId: pin.id
      };
      nodesByPoint.set(`pin:${pin.id}`, pinNode);
      edgesById.set(edgeId(pinNodeId, pointNode, "pin-contact"), {
        id: edgeId(pinNodeId, pointNode, "pin-contact"),
        from: pinNodeId,
        to: pointNode,
        kind: "pin-contact",
        confidence: 1
      });
    }
  }

  return {
    nodes: [...nodesByPoint.values()],
    edges: [...edgesById.values()]
  };
}

function adjacency(graph: NetGraph): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const edge of graph.edges) {
    map.set(edge.from, [...(map.get(edge.from) ?? []), edge.to]);
    map.set(edge.to, [...(map.get(edge.to) ?? []), edge.from]);
  }
  return map;
}

export function traceFromPin(graph: NetGraph, components: Component[], pinId: string): Component[] {
  const start = `pin:${pinId}`;
  const seen = new Set<string>([start]);
  const queue = [start];
  const links = adjacency(graph);
  const connectedPinIds = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current.startsWith("pin:")) connectedPinIds.add(current.slice(4));
    for (const next of links.get(current) ?? []) {
      if (!seen.has(next)) {
        seen.add(next);
        queue.push(next);
      }
    }
  }

  return components.filter((component) =>
    component.pins.some((pin) => connectedPinIds.has(pin.id))
  );
}
```

- [ ] **Step 4: Verify connectivity**

Run:

```powershell
npm test -- src/domain/connectivity.test.ts
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit connectivity**

Run:

```powershell
git add src/domain
git commit -m "feat: build wiring connectivity graph"
```

Expected: commit succeeds.

## Task 5: Complete Classification and Review Queue

**Files:**
- Modify: `src/domain/classification.ts`
- Create: `src/domain/classification.test.ts`

- [ ] **Step 1: Write classification tests**

Create `src/domain/classification.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { classifyComponent, createClassificationQueue } from "./classification";
import type { Component } from "./types";

function baseComponent(partial: Partial<Component>): Component {
  return {
    id: "c1",
    sourceId: "c1",
    rawName: "",
    packageName: "",
    symbolName: "",
    alias: "",
    x: 0,
    y: 0,
    pins: [],
    autoRole: "unknown",
    autoConfidence: 0,
    confirmedRole: null,
    raw: "",
    ...partial
  };
}

describe("classification", () => {
  it("classifies EMU parts as ECU with high confidence", () => {
    expect(
      classifyComponent({
        packageName: "EMU_GRAY_FOOTPRINT",
        symbolName: "EMU_GRAY_SYMBOL",
        rawName: "EMU Gray",
        pinCount: 34
      })
    ).toMatchObject({ role: "ecu", confidence: 0.9 });
  });

  it("classifies connector-like parts but still queues generic headers", () => {
    const molex = classifyComponent({
      packageName: "MOLEX_12PIN_FOOTPRINT",
      symbolName: "MOLEX_12PIN",
      rawName: "Main Connector",
      pinCount: 12
    });
    const header = classifyComponent({
      packageName: "HDR-F-2.54_1X3",
      symbolName: "HDR-F-2.54_1x3",
      rawName: "Fuel Pump",
      pinCount: 3
    });

    expect(molex.role).toBe("connector");
    expect(molex.confidence).toBeGreaterThan(header.confidence);
    expect(header.role).toBe("connector");
  });

  it("queues components below the confidence threshold", () => {
    const queue = createClassificationQueue([
      baseComponent({ id: "strong", autoRole: "ecu", autoConfidence: 0.9 }),
      baseComponent({ id: "weak", autoRole: "connector", autoConfidence: 0.55 })
    ]);

    expect(queue.map((item) => item.componentId)).toEqual(["weak"]);
  });
});
```

- [ ] **Step 2: Run classification tests**

Run:

```powershell
npm test -- src/domain/classification.test.ts
```

Expected: FAIL because `createClassificationQueue` is missing and confidence rules are incomplete.

- [ ] **Step 3: Implement full classification module**

Replace `src/domain/classification.ts`:

```ts
import type { Component, ComponentRole } from "./types";

export interface ClassificationInput {
  packageName: string;
  symbolName: string;
  rawName: string;
  pinCount: number;
}

export interface ClassificationResult {
  role: ComponentRole;
  confidence: number;
  reason: string;
}

export interface ClassificationQueueItem {
  componentId: string;
  suggestedRole: ComponentRole;
  confidence: number;
  reason: string;
}

export function classifyComponent(input: ClassificationInput): ClassificationResult {
  const haystack = `${input.packageName} ${input.symbolName} ${input.rawName}`.toUpperCase();

  if (haystack.includes("EMU_")) {
    return { role: "ecu", confidence: 0.9, reason: "EMU 이름 패턴" };
  }

  if (haystack.includes("MOLEX")) {
    return { role: "connector", confidence: 0.82, reason: "MOLEX 커넥터 이름 패턴" };
  }

  if (haystack.includes("HDR-")) {
    const confidence = input.rawName && !haystack.includes("HDR-F") ? 0.65 : 0.55;
    return { role: "connector", confidence, reason: "HDR 헤더 이름 패턴" };
  }

  if (haystack.includes("RELAY")) {
    return { role: "actuator", confidence: 0.62, reason: "relay 이름 패턴" };
  }

  if (haystack.includes("VCC") || haystack.includes("+12V") || haystack.includes("GND")) {
    return { role: "power", confidence: 0.7, reason: "전원 관련 이름 패턴" };
  }

  return { role: "unknown", confidence: 0.2, reason: "강한 자동 분류 규칙 없음" };
}

export function createClassificationQueue(
  components: Component[],
  threshold = 0.7
): ClassificationQueueItem[] {
  return components
    .filter((component) => !component.confirmedRole && component.autoConfidence < threshold)
    .map((component) => ({
      componentId: component.id,
      suggestedRole: component.autoRole,
      confidence: component.autoConfidence,
      reason: `자동 분류 confidence ${component.autoConfidence.toFixed(2)}`
    }));
}
```

- [ ] **Step 4: Verify classification**

Run:

```powershell
npm test -- src/domain/classification.test.ts src/domain/easyedaParser.test.ts
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit classification**

Run:

```powershell
git add src/domain
git commit -m "feat: classify components for review"
```

Expected: commit succeeds.

## Task 6: Implement Project and Attachment Storage

**Files:**
- Create: `src/storage/projectStore.ts`
- Create: `src/storage/attachmentStore.ts`
- Create: `src/storage/projectStore.test.ts`

- [ ] **Step 1: Write project storage tests**

Create `src/storage/projectStore.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { exportProjectJson, importProjectJson, loadProject, saveProject } from "./projectStore";
import type { ElecProject } from "../domain/types";

const project: ElecProject = {
  id: "p1",
  name: "MF-26",
  createdAt: "2026-05-21T00:00:00.000Z",
  updatedAt: "2026-05-21T00:00:00.000Z",
  source: null,
  components: [],
  graph: { nodes: [], edges: [] },
  classifications: {},
  notes: [],
  measurements: [],
  attachments: []
};

describe("projectStore", () => {
  beforeEach(() => localStorage.clear());

  it("saves and loads a project", () => {
    saveProject(project);
    expect(loadProject()?.name).toBe("MF-26");
  });

  it("exports and imports project JSON", () => {
    const text = exportProjectJson(project);
    expect(importProjectJson(text).id).toBe("p1");
  });
});
```

- [ ] **Step 2: Run storage tests**

Run:

```powershell
npm test -- src/storage/projectStore.test.ts
```

Expected: FAIL because storage module does not exist.

- [ ] **Step 3: Implement project store**

Create `src/storage/projectStore.ts`:

```ts
import type { ElecProject } from "../domain/types";

const CURRENT_PROJECT_KEY = "elec-app/current-project";

export function saveProject(project: ElecProject): void {
  localStorage.setItem(CURRENT_PROJECT_KEY, JSON.stringify(project));
}

export function loadProject(): ElecProject | null {
  const raw = localStorage.getItem(CURRENT_PROJECT_KEY);
  if (!raw) return null;
  return importProjectJson(raw);
}

export function exportProjectJson(project: ElecProject): string {
  return JSON.stringify(project, null, 2);
}

export function importProjectJson(text: string): ElecProject {
  const parsed = JSON.parse(text) as ElecProject;
  if (!parsed.id || !parsed.name || !Array.isArray(parsed.components)) {
    throw new Error("지원하지 않는 Elec App 프로젝트 파일입니다.");
  }
  return parsed;
}
```

- [ ] **Step 4: Implement attachment store**

Create `src/storage/attachmentStore.ts`:

```ts
const DB_NAME = "elec-app-attachments";
const STORE_NAME = "files";
const DB_VERSION = 1;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveAttachmentBlob(key: string, blob: Blob): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(blob, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function loadAttachmentBlob(key: string): Promise<Blob | null> {
  const db = await openDb();
  const blob = await new Promise<Blob | null>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get(key);
    request.onsuccess = () => resolve((request.result as Blob | undefined) ?? null);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return blob;
}
```

- [ ] **Step 5: Verify storage**

Run:

```powershell
npm test -- src/storage/projectStore.test.ts
npm run lint
```

Expected: PASS.

- [ ] **Step 6: Commit storage**

Run:

```powershell
git add src/storage
git commit -m "feat: persist elec app projects"
```

Expected: commit succeeds.

## Task 7: Build App State Shell and Import Flow

**Files:**
- Modify: `src/App.tsx`
- Create: `src/ui/ProjectHome.tsx`
- Create: `src/ui/ImportAnalysis.tsx`
- Create: `src/utils/fileHash.ts`
- Create: `src/App.test.tsx`

- [ ] **Step 1: Write UI import smoke test**

Create `src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("shows project actions on launch", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /EasyEDA JSON 가져오기/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /프로젝트 파일 가져오기/i })).toBeInTheDocument();
  });

  it("accepts a JSON file input", async () => {
    render(<App />);
    const input = screen.getByLabelText(/EasyEDA JSON 파일/i);
    const file = new File([JSON.stringify({ schematics: [] })], "test.json", {
      type: "application/json"
    });

    await userEvent.upload(input, file);
    expect(screen.getByText(/test.json/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run UI test**

Run:

```powershell
npm test -- src/App.test.tsx
```

Expected: FAIL because UI does not include import actions.

- [ ] **Step 3: Implement file hash utility**

Create `src/utils/fileHash.ts`:

```ts
export async function hashText(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
```

- [ ] **Step 4: Implement ProjectHome**

Create `src/ui/ProjectHome.tsx`:

```tsx
interface ProjectHomeProps {
  currentFileName: string | null;
  onJsonFile: (file: File) => void;
  onProjectFile: (file: File) => void;
  onExport: () => void;
}

export function ProjectHome({ currentFileName, onJsonFile, onProjectFile, onExport }: ProjectHomeProps) {
  return (
    <section className="panel">
      <h2>프로젝트 홈</h2>
      <div className="actions">
        <label className="file-action">
          EasyEDA JSON 파일
          <input
            aria-label="EasyEDA JSON 파일"
            type="file"
            accept=".json,application/json"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onJsonFile(file);
            }}
          />
        </label>
        <button type="button">EasyEDA JSON 가져오기</button>
        <label className="file-action">
          프로젝트 파일
          <input
            aria-label="프로젝트 파일"
            type="file"
            accept=".json,application/json"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onProjectFile(file);
            }}
          />
        </label>
        <button type="button">프로젝트 파일 가져오기</button>
        <button type="button" onClick={onExport}>
          프로젝트 내보내기
        </button>
      </div>
      {currentFileName ? <p className="status">최근 import: {currentFileName}</p> : null}
    </section>
  );
}
```

- [ ] **Step 5: Implement ImportAnalysis**

Create `src/ui/ImportAnalysis.tsx`:

```tsx
import type { ParsedSchematic } from "../domain/types";

interface ImportAnalysisProps {
  parsed: ParsedSchematic | null;
  error: string | null;
}

export function ImportAnalysis({ parsed, error }: ImportAnalysisProps) {
  if (error) {
    return (
      <section className="panel error">
        <h2>분석 실패</h2>
        <p>{error}</p>
      </section>
    );
  }
  if (!parsed) return null;

  return (
    <section className="panel">
      <h2>업로드 분석</h2>
      <dl className="summary-grid">
        <div><dt>파일</dt><dd>{parsed.source.fileName}</dd></div>
        <div><dt>부품</dt><dd>{parsed.components.length}</dd></div>
        <div><dt>와이어</dt><dd>{parsed.wires.length}</dd></div>
        <div><dt>접점</dt><dd>{parsed.junctions.length}</dd></div>
        <div><dt>Net label</dt><dd>{parsed.labels.length}</dd></div>
        <div><dt>경고</dt><dd>{parsed.warnings.length}</dd></div>
      </dl>
    </section>
  );
}
```

- [ ] **Step 6: Wire App state**

Replace `src/App.tsx`:

```tsx
import { useState } from "react";
import { buildConnectivityGraph } from "./domain/connectivity";
import { parseEasyEdaSchematic } from "./domain/easyedaParser";
import type { ElecProject, ParsedSchematic } from "./domain/types";
import { ImportAnalysis } from "./ui/ImportAnalysis";
import { ProjectHome } from "./ui/ProjectHome";
import { hashText } from "./utils/fileHash";

function createProject(parsed: ParsedSchematic): ElecProject {
  const now = new Date().toISOString();
  return {
    id: parsed.source.hash,
    name: parsed.source.title || parsed.source.fileName,
    createdAt: now,
    updatedAt: now,
    source: parsed.source,
    components: parsed.components,
    graph: buildConnectivityGraph(parsed),
    classifications: {},
    notes: [],
    measurements: [],
    attachments: []
  };
}

export default function App() {
  const [parsed, setParsed] = useState<ParsedSchematic | null>(null);
  const [project, setProject] = useState<ElecProject | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleJsonFile(file: File) {
    setError(null);
    const text = await file.text();
    const hash = await hashText(text);
    const nextParsed = await parseEasyEdaSchematic({
      fileName: file.name,
      text,
      uploadedAt: new Date().toISOString(),
      hash
    });
    setParsed(nextParsed);
    setProject(createProject(nextParsed));
  }

  async function handleProjectFile(file: File) {
    setError(null);
    try {
      const text = await file.text();
      setProject(JSON.parse(text) as ElecProject);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "프로젝트 파일을 열 수 없습니다.");
    }
  }

  function handleExport() {
    if (!project) return;
    const blob = new Blob([JSON.stringify(project, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "elec-app-project.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Elec App</h1>
          <p>MF-26 engine/elec wiring debugger</p>
        </div>
      </header>
      <ProjectHome
        currentFileName={parsed?.source.fileName ?? project?.source?.fileName ?? null}
        onJsonFile={(file) => void handleJsonFile(file).catch((cause) => setError(String(cause)))}
        onProjectFile={(file) => void handleProjectFile(file)}
        onExport={handleExport}
      />
      <ImportAnalysis parsed={parsed} error={error} />
    </main>
  );
}
```

- [ ] **Step 7: Add panel CSS**

Append to `src/styles.css`:

```css
.panel {
  margin: 16px 24px;
  padding: 18px;
  background: white;
  border: 1px solid #d9e2e5;
  border-radius: 8px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.file-action {
  display: grid;
  gap: 6px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.summary-grid div {
  padding: 10px;
  background: #f5f7f8;
  border: 1px solid #d9e2e5;
  border-radius: 6px;
}

.summary-grid dt {
  font-size: 12px;
  color: #52656d;
}

.summary-grid dd {
  margin: 4px 0 0;
  font-weight: 700;
}

.error {
  border-color: #b42318;
  color: #7a271a;
}
```

- [ ] **Step 8: Verify app shell**

Run:

```powershell
npm test -- src/App.test.tsx
npm run build
```

Expected: PASS and build exits 0.

- [ ] **Step 9: Commit import flow**

Run:

```powershell
git add src
git commit -m "feat: add EasyEDA import flow"
```

Expected: commit succeeds.

## Task 8: Implement Classification Queue UI

**Files:**
- Create: `src/ui/ClassificationQueue.tsx`
- Create: `src/ui/ClassificationQueue.test.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write classification queue UI test**

Create `src/ui/ClassificationQueue.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClassificationQueue } from "./ClassificationQueue";
import type { Component } from "../domain/types";

const component: Component = {
  id: "hdr1",
  sourceId: "hdr1",
  rawName: "Fuel Pump Header",
  packageName: "HDR-F-2.54_1X3",
  symbolName: "HDR-F-2.54_1x3",
  alias: "Fuel Pump Header",
  x: 0,
  y: 0,
  pins: [],
  autoRole: "connector",
  autoConfidence: 0.55,
  confirmedRole: null,
  raw: ""
};

describe("ClassificationQueue", () => {
  it("lets user confirm role and alias", async () => {
    const onConfirm = vi.fn();
    render(<ClassificationQueue components={[component]} onConfirm={onConfirm} />);

    await userEvent.selectOptions(screen.getByLabelText(/분류/), "sensor");
    await userEvent.clear(screen.getByLabelText(/별칭/));
    await userEvent.type(screen.getByLabelText(/별칭/), "Fuel Pump");
    await userEvent.click(screen.getByRole("button", { name: /확정/ }));

    expect(onConfirm).toHaveBeenCalledWith("hdr1", "sensor", "Fuel Pump");
  });
});
```

- [ ] **Step 2: Run UI test**

Run:

```powershell
npm test -- src/ui/ClassificationQueue.test.tsx
```

Expected: FAIL because component does not exist.

- [ ] **Step 3: Implement ClassificationQueue**

Create `src/ui/ClassificationQueue.tsx`:

```tsx
import { useState } from "react";
import type { Component, ComponentRole } from "../domain/types";

const roleLabels: Record<ComponentRole, string> = {
  ecu: "ECU",
  connector: "커넥터",
  sensor: "센서",
  actuator: "액추에이터",
  power: "전원 부품",
  other: "기타",
  unknown: "미확인"
};

interface ClassificationQueueProps {
  components: Component[];
  onConfirm: (componentId: string, role: ComponentRole, alias: string) => void;
}

export function ClassificationQueue({ components, onConfirm }: ClassificationQueueProps) {
  const pending = components.filter((component) => !component.confirmedRole && component.autoConfidence < 0.7);

  if (pending.length === 0) {
    return (
      <section className="panel">
        <h2>분류 확인 큐</h2>
        <p>확인할 애매한 부품이 없습니다.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>분류 확인 큐</h2>
      <div className="stack">
        {pending.map((component) => (
          <ClassificationRow key={component.id} component={component} onConfirm={onConfirm} />
        ))}
      </div>
    </section>
  );
}

function ClassificationRow({ component, onConfirm }: { component: Component; onConfirm: ClassificationQueueProps["onConfirm"] }) {
  const [role, setRole] = useState<ComponentRole>(component.autoRole);
  const [alias, setAlias] = useState(component.alias || component.rawName);

  return (
    <article className="classification-row">
      <div>
        <h3>{component.rawName || component.symbolName || component.packageName}</h3>
        <p>{component.packageName} / pins {component.pins.length} / confidence {component.autoConfidence.toFixed(2)}</p>
      </div>
      <label>
        분류
        <select value={role} onChange={(event) => setRole(event.currentTarget.value as ComponentRole)}>
          {Object.entries(roleLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>
      <label>
        별칭
        <input value={alias} onChange={(event) => setAlias(event.currentTarget.value)} />
      </label>
      <button type="button" onClick={() => onConfirm(component.id, role, alias)}>
        확정
      </button>
    </article>
  );
}
```

- [ ] **Step 4: Wire queue into App**

In `src/App.tsx`, import `ClassificationQueue`:

```tsx
import { ClassificationQueue } from "./ui/ClassificationQueue";
```

Add this function inside `App`:

```tsx
function confirmClassification(componentId: string, role: ComponentRole, alias: string) {
  setProject((current) => {
    if (!current) return current;
    const updatedAt = new Date().toISOString();
    return {
      ...current,
      updatedAt,
      components: current.components.map((component) =>
        component.id === componentId ? { ...component, confirmedRole: role, alias } : component
      ),
      classifications: {
        ...current.classifications,
        [componentId]: { componentId, role, alias, confirmedAt: updatedAt }
      }
    };
  });
}
```

Add `ComponentRole` to the type import:

```tsx
import type { ComponentRole, ElecProject, ParsedSchematic } from "./domain/types";
```

Render below `ImportAnalysis`:

```tsx
{project ? (
  <ClassificationQueue components={project.components} onConfirm={confirmClassification} />
) : null}
```

- [ ] **Step 5: Add CSS for queue**

Append to `src/styles.css`:

```css
.stack {
  display: grid;
  gap: 12px;
}

.classification-row {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 160px minmax(180px, 260px) auto;
  gap: 12px;
  align-items: end;
  padding: 12px;
  border: 1px solid #d9e2e5;
  border-radius: 8px;
}
```

- [ ] **Step 6: Verify classification UI**

Run:

```powershell
npm test -- src/ui/ClassificationQueue.test.tsx
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit classification UI**

Run:

```powershell
git add src
git commit -m "feat: add component classification queue"
```

Expected: commit succeeds.

## Task 9: Add Search Debugger and Connector Pinout

**Files:**
- Create: `src/utils/search.ts`
- Create: `src/ui/SearchDebugger.tsx`
- Create: `src/ui/ConnectorPinout.tsx`
- Create: `src/ui/SearchDebugger.test.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write search debugger test**

Create `src/ui/SearchDebugger.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SearchDebugger } from "./SearchDebugger";
import type { Component, NetGraph } from "../domain/types";

const components: Component[] = [
  {
    id: "ecu",
    sourceId: "ecu",
    rawName: "EMU Gray",
    packageName: "EMU_GRAY_FOOTPRINT",
    symbolName: "EMU_GRAY_SYMBOL",
    alias: "ECU Gray",
    x: 0,
    y: 0,
    pins: [{ id: "ecu-1", componentId: "ecu", number: "1", label: null, x: 0, y: 0, raw: "" }],
    autoRole: "ecu",
    autoConfidence: 1,
    confirmedRole: "ecu",
    raw: ""
  },
  {
    id: "conn",
    sourceId: "conn",
    rawName: "Main Connector",
    packageName: "MOLEX_12PIN",
    symbolName: "MOLEX_12PIN",
    alias: "Main Connector",
    x: 10,
    y: 0,
    pins: [{ id: "conn-1", componentId: "conn", number: "1", label: null, x: 10, y: 0, raw: "" }],
    autoRole: "connector",
    autoConfidence: 1,
    confirmedRole: "connector",
    raw: ""
  }
];

const graph: NetGraph = {
  nodes: [
    { id: "pin:ecu-1", kind: "pin", x: 0, y: 0, label: null, refId: "ecu-1" },
    { id: "pin:conn-1", kind: "pin", x: 10, y: 0, label: null, refId: "conn-1" }
  ],
  edges: [{ id: "e1", from: "pin:ecu-1", to: "pin:conn-1", kind: "wire", confidence: 1 }]
};

describe("SearchDebugger", () => {
  it("searches aliases and shows trace components", async () => {
    render(<SearchDebugger components={components} graph={graph} />);
    await userEvent.type(screen.getByLabelText(/검색/), "ECU Gray");
    expect(screen.getByText(/Main Connector/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run search test**

Run:

```powershell
npm test -- src/ui/SearchDebugger.test.tsx
```

Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement search utility**

Create `src/utils/search.ts`:

```ts
import type { Component } from "../domain/types";

export function matchesComponent(component: Component, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return false;
  const haystack = [
    component.rawName,
    component.alias,
    component.packageName,
    component.symbolName,
    ...component.pins.map((pin) => `${component.alias} pin ${pin.number}`)
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalized);
}
```

- [ ] **Step 4: Implement SearchDebugger**

Create `src/ui/SearchDebugger.tsx`:

```tsx
import { useMemo, useState } from "react";
import { traceFromPin } from "../domain/connectivity";
import type { Component, NetGraph } from "../domain/types";
import { matchesComponent } from "../utils/search";

interface SearchDebuggerProps {
  components: Component[];
  graph: NetGraph;
}

export function SearchDebugger({ components, graph }: SearchDebuggerProps) {
  const [query, setQuery] = useState("");
  const matches = useMemo(
    () => components.filter((component) => matchesComponent(component, query)).slice(0, 10),
    [components, query]
  );
  const selected = matches[0];
  const trace = selected?.pins[0] ? traceFromPin(graph, components, selected.pins[0].id) : [];

  return (
    <section className="panel">
      <h2>검색 디버거</h2>
      <label>
        검색
        <input value={query} onChange={(event) => setQuery(event.currentTarget.value)} placeholder="ECU Gray pin 12, Fuel Pump, GND" />
      </label>
      {matches.length > 0 ? (
        <div className="trace-list">
          {trace.map((component) => (
            <div className="trace-chip" key={component.id}>
              {component.alias || component.rawName}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">검색어를 입력하면 연결 경로를 표시합니다.</p>
      )}
    </section>
  );
}
```

- [ ] **Step 5: Implement ConnectorPinout**

Create `src/ui/ConnectorPinout.tsx`:

```tsx
import type { Component } from "../domain/types";

interface ConnectorPinoutProps {
  components: Component[];
}

export function ConnectorPinout({ components }: ConnectorPinoutProps) {
  const connectors = components.filter((component) => (component.confirmedRole ?? component.autoRole) === "connector");
  const selected = connectors[0] ?? null;

  return (
    <section className="panel">
      <h2>커넥터 Pinout</h2>
      {selected ? (
        <table className="pinout-table">
          <caption>{selected.alias || selected.rawName}</caption>
          <thead>
            <tr>
              <th>Pin</th>
              <th>Net</th>
              <th>ECU</th>
              <th>대상</th>
              <th>메모</th>
              <th>측정</th>
            </tr>
          </thead>
          <tbody>
            {selected.pins.map((pin) => (
              <tr key={pin.id}>
                <td>{pin.number}</td>
                <td>{pin.label ?? "-"}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">분류된 커넥터가 없습니다.</p>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Wire views into App**

Import:

```tsx
import { ConnectorPinout } from "./ui/ConnectorPinout";
import { SearchDebugger } from "./ui/SearchDebugger";
```

Render after classification queue:

```tsx
{project ? (
  <>
    <SearchDebugger components={project.components} graph={project.graph} />
    <ConnectorPinout components={project.components} />
  </>
) : null}
```

- [ ] **Step 7: Add CSS**

Append to `src/styles.css`:

```css
.trace-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.trace-chip {
  padding: 8px 10px;
  background: #e7f1f3;
  border: 1px solid #bfd8de;
  border-radius: 6px;
  font-weight: 700;
}

.pinout-table {
  width: 100%;
  border-collapse: collapse;
}

.pinout-table th,
.pinout-table td {
  border-bottom: 1px solid #d9e2e5;
  padding: 8px;
  text-align: left;
}

.muted {
  color: #60747d;
}
```

- [ ] **Step 8: Verify search and pinout**

Run:

```powershell
npm test -- src/ui/SearchDebugger.test.tsx
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit debugger views**

Run:

```powershell
git add src
git commit -m "feat: add search debugger and connector pinout"
```

Expected: commit succeeds.

## Task 10: Add Component Info, Notes, and Measurements

**Files:**
- Create: `src/ui/ComponentInfoPanel.tsx`
- Create: `src/ui/NotesMeasurements.tsx`
- Create: `src/ui/NotesMeasurements.test.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write notes and measurements test**

Create `src/ui/NotesMeasurements.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NotesMeasurements } from "./NotesMeasurements";

describe("NotesMeasurements", () => {
  it("submits a pin note and measurement", async () => {
    const onAddNote = vi.fn();
    const onAddMeasurement = vi.fn();
    render(
      <NotesMeasurements
        targetId="pin-1"
        onAddNote={onAddNote}
        onAddMeasurement={onAddMeasurement}
      />
    );

    await userEvent.type(screen.getByLabelText(/메모/), "접촉불량 이력");
    await userEvent.click(screen.getByRole("button", { name: /메모 저장/ }));
    await userEvent.type(screen.getByLabelText(/예상값/), "12V");
    await userEvent.type(screen.getByLabelText(/실측값/), "11.9V");
    await userEvent.click(screen.getByRole("button", { name: /측정 저장/ }));

    expect(onAddNote).toHaveBeenCalledWith("pin-1", "접촉불량 이력");
    expect(onAddMeasurement).toHaveBeenCalledWith(
      expect.objectContaining({ pinId: "pin-1", expectedValue: "12V", measuredValue: "11.9V" })
    );
  });
});
```

- [ ] **Step 2: Run notes test**

Run:

```powershell
npm test -- src/ui/NotesMeasurements.test.tsx
```

Expected: FAIL because component does not exist.

- [ ] **Step 3: Implement NotesMeasurements**

Create `src/ui/NotesMeasurements.tsx`:

```tsx
import { useState } from "react";
import type { Measurement } from "../domain/types";

interface NotesMeasurementsProps {
  targetId: string;
  onAddNote: (targetId: string, body: string) => void;
  onAddMeasurement: (measurement: Omit<Measurement, "id" | "measuredAt">) => void;
}

export function NotesMeasurements({ targetId, onAddNote, onAddMeasurement }: NotesMeasurementsProps) {
  const [note, setNote] = useState("");
  const [expectedValue, setExpectedValue] = useState("");
  const [measuredValue, setMeasuredValue] = useState("");

  return (
    <div className="notes-measurements">
      <label>
        메모
        <textarea value={note} onChange={(event) => setNote(event.currentTarget.value)} />
      </label>
      <button type="button" onClick={() => onAddNote(targetId, note)}>
        메모 저장
      </button>
      <label>
        예상값
        <input value={expectedValue} onChange={(event) => setExpectedValue(event.currentTarget.value)} />
      </label>
      <label>
        실측값
        <input value={measuredValue} onChange={(event) => setMeasuredValue(event.currentTarget.value)} />
      </label>
      <button
        type="button"
        onClick={() =>
          onAddMeasurement({
            pinId: targetId,
            expectedValue,
            condition: "",
            measuredValue,
            status: "unknown",
            note: ""
          })
        }
      >
        측정 저장
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Implement ComponentInfoPanel**

Create `src/ui/ComponentInfoPanel.tsx`:

```tsx
import type { Attachment, Component, Measurement, Note } from "../domain/types";

interface ComponentInfoPanelProps {
  component: Component | null;
  notes: Note[];
  measurements: Measurement[];
  attachments: Attachment[];
}

export function ComponentInfoPanel({ component, notes, measurements, attachments }: ComponentInfoPanelProps) {
  if (!component) {
    return (
      <aside className="info-panel">
        <h2>부품 정보</h2>
        <p className="muted">부품을 선택하면 정보가 표시됩니다.</p>
      </aside>
    );
  }

  const componentNotes = notes.filter((note) => note.targetId === component.id);
  const componentAttachments = attachments.filter((attachment) => attachment.targetId === component.id);

  return (
    <aside className="info-panel">
      <h2>{component.alias || component.rawName}</h2>
      <dl>
        <dt>분류</dt>
        <dd>{component.confirmedRole ?? component.autoRole}</dd>
        <dt>핀 수</dt>
        <dd>{component.pins.length}</dd>
        <dt>원본 이름</dt>
        <dd>{component.symbolName || component.packageName}</dd>
      </dl>
      <h3>데이터시트</h3>
      {componentAttachments.length > 0 ? (
        <ul>{componentAttachments.map((item) => <li key={item.id}>{item.label}</li>)}</ul>
      ) : (
        <p className="muted">등록된 데이터시트가 없습니다.</p>
      )}
      <h3>메모</h3>
      {componentNotes.length > 0 ? (
        <ul>{componentNotes.map((note) => <li key={note.id}>{note.body}</li>)}</ul>
      ) : (
        <p className="muted">메모가 없습니다.</p>
      )}
      <h3>측정 기록</h3>
      <p>{measurements.filter((measurement) => component.pins.some((pin) => pin.id === measurement.pinId)).length}개</p>
    </aside>
  );
}
```

- [ ] **Step 5: Wire minimal handlers into App**

Add helpers inside `App`:

```tsx
function addNote(targetId: string, body: string) {
  setProject((current) =>
    current
      ? {
          ...current,
          notes: [
            ...current.notes,
            { id: crypto.randomUUID(), targetType: "pin", targetId, body, updatedAt: new Date().toISOString() }
          ]
        }
      : current
  );
}

function addMeasurement(input: Omit<Measurement, "id" | "measuredAt">) {
  setProject((current) =>
    current
      ? {
          ...current,
          measurements: [
            ...current.measurements,
            { ...input, id: crypto.randomUUID(), measuredAt: new Date().toISOString() }
          ]
        }
      : current
  );
}
```

Import `Measurement`:

```tsx
import type { ComponentRole, ElecProject, Measurement, ParsedSchematic } from "./domain/types";
```

Render a basic panel for the first component:

```tsx
{project ? (
  <ComponentInfoPanel
    component={project.components[0] ?? null}
    notes={project.notes}
    measurements={project.measurements}
    attachments={project.attachments}
  />
) : null}
```

- [ ] **Step 6: Verify notes and measurements**

Run:

```powershell
npm test -- src/ui/NotesMeasurements.test.tsx
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit info and measurements**

Run:

```powershell
git add src
git commit -m "feat: add component notes and measurements"
```

Expected: commit succeeds.

## Task 11: Add Reference Tabs for Datasheets, Wiring Diagram, and Regulations

**Files:**
- Create: `src/ui/ReferenceTabs.tsx`
- Create: `src/ui/ReferenceTabs.test.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write reference tab test**

Create `src/ui/ReferenceTabs.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReferenceTabs } from "./ReferenceTabs";

describe("ReferenceTabs", () => {
  it("adds a regulation link", async () => {
    const onAddLink = vi.fn();
    render(<ReferenceTabs attachments={[]} onAddLink={onAddLink} onAddFile={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /대회 규정/ }));
    await userEvent.type(screen.getByLabelText(/링크 제목/), "FSAE Rules");
    await userEvent.type(screen.getByLabelText(/URL/), "https://example.com/rules.pdf");
    await userEvent.click(screen.getByRole("button", { name: /링크 저장/ }));

    expect(onAddLink).toHaveBeenCalledWith("regulation", "FSAE Rules", "https://example.com/rules.pdf");
  });
});
```

- [ ] **Step 2: Run reference tab test**

Run:

```powershell
npm test -- src/ui/ReferenceTabs.test.tsx
```

Expected: FAIL because component does not exist.

- [ ] **Step 3: Implement ReferenceTabs**

Create `src/ui/ReferenceTabs.tsx`:

```tsx
import { useState } from "react";
import type { Attachment } from "../domain/types";

type ReferenceTarget = "component" | "wiring-diagram" | "regulation";

interface ReferenceTabsProps {
  attachments: Attachment[];
  onAddLink: (targetType: ReferenceTarget, label: string, url: string) => void;
  onAddFile: (targetType: ReferenceTarget, file: File) => void;
}

const tabs: Array<{ target: ReferenceTarget; label: string }> = [
  { target: "component", label: "데이터시트" },
  { target: "wiring-diagram", label: "전체 배선도" },
  { target: "regulation", label: "대회 규정" }
];

export function ReferenceTabs({ attachments, onAddLink, onAddFile }: ReferenceTabsProps) {
  const [active, setActive] = useState<ReferenceTarget>("component");
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  const visible = attachments.filter((attachment) => attachment.targetType === active);

  return (
    <section className="panel">
      <h2>레퍼런스</h2>
      <div className="tab-row">
        {tabs.map((tab) => (
          <button key={tab.target} type="button" onClick={() => setActive(tab.target)}>
            {tab.label}
          </button>
        ))}
      </div>
      <div className="reference-form">
        <label>
          링크 제목
          <input value={label} onChange={(event) => setLabel(event.currentTarget.value)} />
        </label>
        <label>
          URL
          <input value={url} onChange={(event) => setUrl(event.currentTarget.value)} />
        </label>
        <button type="button" onClick={() => onAddLink(active, label, url)}>
          링크 저장
        </button>
        <label>
          파일 첨부
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onAddFile(active, file);
            }}
          />
        </label>
      </div>
      <ul>
        {visible.map((item) => (
          <li key={item.id}>{item.label}</li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Wire references into App**

Add import:

```tsx
import { ReferenceTabs } from "./ui/ReferenceTabs";
```

Add handlers:

```tsx
function addReferenceLink(targetType: "component" | "wiring-diagram" | "regulation", label: string, url: string) {
  setProject((current) =>
    current
      ? {
          ...current,
          attachments: [
            ...current.attachments,
            { id: crypto.randomUUID(), targetType, targetId: null, label, kind: "link", url, blobKey: null, mimeType: null }
          ]
        }
      : current
  );
}

function addReferenceFile(targetType: "component" | "wiring-diagram" | "regulation", file: File) {
  setProject((current) =>
    current
      ? {
          ...current,
          attachments: [
            ...current.attachments,
            {
              id: crypto.randomUUID(),
              targetType,
              targetId: null,
              label: file.name,
              kind: "file",
              url: null,
              blobKey: `${Date.now()}-${file.name}`,
              mimeType: file.type
            }
          ]
        }
      : current
  );
}
```

Render:

```tsx
{project ? (
  <ReferenceTabs
    attachments={project.attachments}
    onAddLink={addReferenceLink}
    onAddFile={addReferenceFile}
  />
) : null}
```

- [ ] **Step 5: Verify reference tabs**

Run:

```powershell
npm test -- src/ui/ReferenceTabs.test.tsx
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit reference tabs**

Run:

```powershell
git add src
git commit -m "feat: add offline reference tabs"
```

Expected: commit succeeds.

## Task 12: Implement Schematic Update Matcher

**Files:**
- Create: `src/domain/updateMatcher.ts`
- Create: `src/domain/updateMatcher.test.ts`
- Create: `src/ui/UpdateSummary.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write update matcher tests**

Create `src/domain/updateMatcher.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { matchUpdatedComponents } from "./updateMatcher";
import type { Component } from "./types";

function component(id: string, symbolName: string, x: number): Component {
  return {
    id,
    sourceId: id,
    rawName: symbolName,
    packageName: symbolName,
    symbolName,
    alias: symbolName,
    x,
    y: 0,
    pins: [{ id: `${id}-1`, componentId: id, number: "1", label: null, x, y: 0, raw: "" }],
    autoRole: "unknown",
    autoConfidence: 0.2,
    confirmedRole: null,
    raw: ""
  };
}

describe("updateMatcher", () => {
  it("matches by id first and falls back to symbol and coordinates", () => {
    const oldComponents = [component("old-1", "MOLEX_12PIN", 100)];
    const newComponents = [component("new-1", "MOLEX_12PIN", 102)];

    const result = matchUpdatedComponents(oldComponents, newComponents);

    expect(result.matched[0]).toMatchObject({
      previousId: "old-1",
      nextId: "new-1",
      confidence: expect.any(Number)
    });
    expect(result.added).toHaveLength(0);
    expect(result.removed).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run update matcher test**

Run:

```powershell
npm test -- src/domain/updateMatcher.test.ts
```

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement update matcher**

Create `src/domain/updateMatcher.ts`:

```ts
import type { Component } from "./types";

export interface ComponentMatch {
  previousId: string;
  nextId: string;
  confidence: number;
  reason: string;
}

export interface UpdateMatchResult {
  matched: ComponentMatch[];
  added: Component[];
  removed: Component[];
  needsReview: ComponentMatch[];
}

function score(previous: Component, next: Component): ComponentMatch {
  if (previous.sourceId === next.sourceId) {
    return { previousId: previous.id, nextId: next.id, confidence: 1, reason: "EasyEDA sourceId 일치" };
  }

  let confidence = 0;
  const reasons: string[] = [];
  if (previous.symbolName && previous.symbolName === next.symbolName) {
    confidence += 0.35;
    reasons.push("symbolName 일치");
  }
  if (previous.packageName && previous.packageName === next.packageName) {
    confidence += 0.25;
    reasons.push("packageName 일치");
  }
  if (previous.pins.length === next.pins.length) {
    confidence += 0.2;
    reasons.push("핀 수 일치");
  }
  const distance = Math.hypot(previous.x - next.x, previous.y - next.y);
  if (distance <= 20) {
    confidence += 0.2;
    reasons.push("좌표 근접");
  }

  return {
    previousId: previous.id,
    nextId: next.id,
    confidence,
    reason: reasons.join(", ") || "약한 후보"
  };
}

export function matchUpdatedComponents(previous: Component[], next: Component[]): UpdateMatchResult {
  const usedPrevious = new Set<string>();
  const usedNext = new Set<string>();
  const matched: ComponentMatch[] = [];
  const needsReview: ComponentMatch[] = [];

  for (const nextComponent of next) {
    const candidates = previous
      .filter((previousComponent) => !usedPrevious.has(previousComponent.id))
      .map((previousComponent) => score(previousComponent, nextComponent))
      .sort((a, b) => b.confidence - a.confidence);
    const best = candidates[0];
    if (!best || best.confidence < 0.6) continue;

    usedPrevious.add(best.previousId);
    usedNext.add(best.nextId);
    if (best.confidence >= 0.8) matched.push(best);
    else needsReview.push(best);
  }

  return {
    matched,
    needsReview,
    added: next.filter((component) => !usedNext.has(component.id)),
    removed: previous.filter((component) => !usedPrevious.has(component.id))
  };
}
```

- [ ] **Step 4: Implement UpdateSummary**

Create `src/ui/UpdateSummary.tsx`:

```tsx
import type { UpdateMatchResult } from "../domain/updateMatcher";

interface UpdateSummaryProps {
  result: UpdateMatchResult | null;
}

export function UpdateSummary({ result }: UpdateSummaryProps) {
  if (!result) return null;

  return (
    <section className="panel">
      <h2>회로도 업데이트 요약</h2>
      <dl className="summary-grid">
        <div><dt>자동 유지</dt><dd>{result.matched.length}</dd></div>
        <div><dt>확인 필요</dt><dd>{result.needsReview.length}</dd></div>
        <div><dt>추가</dt><dd>{result.added.length}</dd></div>
        <div><dt>삭제</dt><dd>{result.removed.length}</dd></div>
      </dl>
    </section>
  );
}
```

- [ ] **Step 5: Verify matcher**

Run:

```powershell
npm test -- src/domain/updateMatcher.test.ts
npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit update matcher**

Run:

```powershell
git add src
git commit -m "feat: match schematic updates"
```

Expected: commit succeeds.

## Task 13: Add PWA Offline Support and Final Verification

**Files:**
- Create: `public/manifest.webmanifest`
- Create: `public/sw.js`
- Modify: `index.html`
- Modify: `src/main.tsx`

- [ ] **Step 1: Add manifest**

Create `public/manifest.webmanifest`:

```json
{
  "name": "Elec App",
  "short_name": "Elec App",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f5f7f8",
  "theme_color": "#12343b",
  "description": "Offline wiring debugger for MF-26 engine/elec team"
}
```

- [ ] **Step 2: Add service worker**

Create `public/sw.js`:

```js
const CACHE_NAME = "elec-app-v1";
const CORE_ASSETS = ["/", "/index.html", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/index.html")))
  );
});
```

- [ ] **Step 3: Register manifest and service worker**

Add to `index.html` inside `<head>`:

```html
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#12343b" />
```

Append to `src/main.tsx`:

```ts
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js");
  });
}
```

- [ ] **Step 4: Run full verification**

Run:

```powershell
npm test
npm run build
```

Expected: all tests pass and production build exits 0.

- [ ] **Step 5: Start local dev server**

Run:

```powershell
npm run dev
```

Expected: Vite prints a localhost URL such as `http://127.0.0.1:5173/`.

- [ ] **Step 6: Manual smoke test**

In browser:

1. Open the Vite URL.
2. Upload `SCH_26.5.11-배선도_2026-05-19.json`.
3. Confirm analysis shows nonzero components, wires, junctions, and labels.
4. Confirm ambiguous parts appear in classification queue.
5. Confirm a component can be classified and aliased.
6. Search for `EMU` or `MOLEX`.
7. Confirm connector pinout table appears.
8. Add a note and measurement.
9. Add a regulation link.
10. Export project JSON.

Expected: all steps complete without console errors.

- [ ] **Step 7: Commit offline support**

Run:

```powershell
git add public index.html src/main.tsx
git commit -m "feat: add offline PWA support"
```

Expected: commit succeeds.

## Plan Self-Review

Spec coverage:

- EasyEDA JSON import: Tasks 3 and 7.
- Parser and normalization: Tasks 2 and 3.
- Connectivity graph and path tracing: Task 4.
- Hybrid classification and upfront queue: Tasks 5 and 8.
- Project local storage and export/import: Task 6.
- Search debugger and connector pinout: Task 9.
- Component info panel, notes, measurements: Task 10.
- Datasheet, wiring diagram, and regulation references: Task 11.
- Schematic update matching: Task 12.
- Offline PWA behavior: Task 13.

Known implementation risk:

- The sample EasyEDA parser is based on observed shape strings and fixture coverage. During execution, run the parser against the real sample file and add fixture tests for any shape patterns that fail.
- Attachment binary storage is represented by the IndexedDB store and UI metadata. If the browser test environment lacks IndexedDB, keep IndexedDB behavior covered by manual smoke tests or add a small fake in `src/test/setup.ts`.

No placeholder terms remain in task steps. Function names used across tasks are defined before use or in the same task.
