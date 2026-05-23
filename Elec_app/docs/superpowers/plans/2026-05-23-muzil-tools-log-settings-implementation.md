# Muzil Tools Log Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first extensible log interpretation system for Muzil Tools: persistent CSV sessions, settings-backed sensor definitions, safe derived formulas, clearer replay tabs, overlay tooltips, GPS projection, and ADXL/ADU separation.

**Architecture:** Add a settings/domain layer under `src/domain/logSettings*`, persistence under `src/storage/logReplayStore.ts`, and UI tabs under `src/ui/logReplay`. Existing parsing stays in `logReplayParser.ts`; settings transform parsed sessions into display/analysis sessions. The first implementation remains fully client-side and stores recent CSV/settings in IndexedDB.

**Tech Stack:** React 19, TypeScript, Vitest, Testing Library, Vite, IndexedDB browser APIs, SVG charts.

---

## File Structure

- Create `Elec_app/src/domain/logSettingsTypes.ts`: settings interfaces and enums.
- Create `Elec_app/src/domain/logSettingsDefaults.ts`: default settings and inferred sensor config generation.
- Create `Elec_app/src/domain/formulaEngine.ts`: safe tokenizer/parser/evaluator for derived sensors and event rules.
- Create `Elec_app/src/domain/logSessionTransform.ts`: apply settings, alias mapping, scale/offset, derived sensors, and event rule evaluation to parsed sessions.
- Create `Elec_app/src/domain/gpsProjection.ts`: convert lat/lon samples to local meter coordinates and screen points.
- Create `Elec_app/src/storage/logReplayStore.ts`: IndexedDB persistence for latest CSV, settings, and UI state.
- Create `Elec_app/src/ui/logReplay/LogReplayInnerTabs.tsx`: Dashboard/Overlay/GPS/G-G/Events/Sensors/Settings tabs.
- Create `Elec_app/src/ui/logReplay/LogDashboard.tsx`: data-logger-inspired black/yellow dashboard.
- Create `Elec_app/src/ui/logReplay/LogSensorsTable.tsx`: searchable all-sensors table.
- Create `Elec_app/src/ui/logReplay/LogSettingsPanel.tsx`: settings editor for sensors, derived formulas, presets, ADXL/ADU, GPS.
- Modify `Elec_app/src/ui/logReplay/LogReplayTab.tsx`: own persistent session/settings state and render inner tabs.
- Modify `Elec_app/src/ui/logReplay/SensorOverlayChart.tsx`: add hover tooltip.
- Modify `Elec_app/src/ui/logReplay/GpsTrackPanel.tsx`: use projected coordinates.
- Modify `Elec_app/src/ui/logReplay/GGDiagram.tsx`: use linear acceleration settings and separate ADU from G-G.
- Modify `Elec_app/src/domain/logReplayAnalysis.ts`: route events through settings rules and fix Korean messages.
- Modify `Elec_app/src/styles.css`: dark/yellow log replay theme and readable tab layout.

---

### Task 1: Settings Types And Defaults

**Files:**
- Create: `Elec_app/src/domain/logSettingsTypes.ts`
- Create: `Elec_app/src/domain/logSettingsDefaults.ts`
- Test: `Elec_app/src/domain/logSettingsDefaults.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `Elec_app/src/domain/logSettingsDefaults.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings, inferSensorConfigs } from "./logSettingsDefaults";
import type { SensorDefinition } from "./logReplayTypes";

describe("log replay settings defaults", () => {
  test("creates default settings with GPS, ADXL, ADU, presets, and safe event rules", () => {
    const settings = createDefaultLogReplaySettings();

    expect(settings.version).toBe(1);
    expect(settings.gps.latitudeKey).toBe("Latitude");
    expect(settings.gps.longitudeKey).toBe("Longitude");
    expect(settings.accel.linear.unit).toBe("g");
    expect(settings.accel.angular.unit).toBe("degps");
    expect(settings.eventRules.map((rule) => rule.id)).toContain("low-oil-pressure");
    expect(settings.graphPresets.map((preset) => preset.id)).toContain("engine");
  });

  test("infers display settings from parsed sensor definitions", () => {
    const sensors: SensorDefinition[] = [
      { key: "RPM", label: "RPM", type: "number", unit: "rpm" },
      { key: "ADXL_ax_g", label: "ADXL X", type: "number", unit: "g" },
      { key: "adu_z", label: "ADU Z", type: "number", unit: "deg/s" },
    ];

    const configs = inferSensorConfigs(sensors);

    expect(configs.find((sensor) => sensor.sourceKey === "RPM")?.group).toBe("engine");
    expect(configs.find((sensor) => sensor.sourceKey === "ADXL_ax_g")?.group).toBe("linear-accel");
    expect(configs.find((sensor) => sensor.sourceKey === "adu_z")?.group).toBe("angular");
  });
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/domain/logSettingsDefaults.test.ts
```

Expected: FAIL because `logSettingsDefaults` does not exist.

- [ ] **Step 3: Add settings types**

Create `Elec_app/src/domain/logSettingsTypes.ts`:

```ts
export type SensorGroup = "engine" | "electric" | "gps" | "linear-accel" | "angular" | "custom";

export interface SensorConfig {
  id: string;
  sourceKey: string;
  aliases: string[];
  label: string;
  unit: string;
  group: SensorGroup;
  scale: number;
  offset: number;
  precision: number;
  color: string;
  showInDashboard: boolean;
  showInOverlay: boolean;
  showInSensorTable: boolean;
}

export interface DerivedSensorConfig {
  id: string;
  label: string;
  expression: string;
  unit: string;
  group: SensorGroup;
  precision: number;
  color: string;
  fallback: "empty" | "zero" | "previous";
  enabled: boolean;
}

export interface EventRuleConfig {
  id: string;
  label: string;
  expression: string;
  severity: "info" | "warning" | "danger";
  enabled: boolean;
}

export interface GraphPresetConfig {
  id: string;
  label: string;
  sensorIds: string[];
}

export interface GpsConfig {
  latitudeKey: string;
  longitudeKey: string;
  speedKey: string;
  jumpThresholdMeters: number;
  smoothing: "off" | "light";
}

export interface AccelConfig {
  linear: {
    xKey: string;
    yKey: string;
    zKey: string;
    unit: "g" | "mps2" | "raw";
    swapXY: boolean;
    invertX: boolean;
    invertY: boolean;
    invertZ: boolean;
    lowPassAlpha: number;
  };
  angular: {
    xKey: string;
    yKey: string;
    zKey: string;
    unit: "degps" | "radps" | "raw";
    scale: number;
    offset: number;
  };
}

export interface MatlabExportConfig {
  variablePrefix: string;
  sanitizeVariableNames: boolean;
}

export interface LogReplaySettings {
  version: 1;
  sensors: SensorConfig[];
  derivedSensors: DerivedSensorConfig[];
  eventRules: EventRuleConfig[];
  graphPresets: GraphPresetConfig[];
  gps: GpsConfig;
  accel: AccelConfig;
  matlab: MatlabExportConfig;
}
```

- [ ] **Step 4: Add default generation**

Create `Elec_app/src/domain/logSettingsDefaults.ts`:

```ts
import type { SensorDefinition } from "./logReplayTypes";
import type { LogReplaySettings, SensorConfig, SensorGroup } from "./logSettingsTypes";

const COLORS = ["#ffc300", "#4cc9f0", "#f72585", "#22c55e", "#a78bfa", "#fb7185"];

function groupForKey(key: string): SensorGroup {
  const lower = key.toLowerCase();
  if (lower.includes("latitude") || lower.includes("longitude") || lower.includes("gps")) return "gps";
  if (lower.includes("adxl") || lower === "ax_g" || lower === "ay_g" || lower === "az_g") return "linear-accel";
  if (lower.startsWith("adu_") || lower.startsWith("adu")) return "angular";
  if (lower.includes("batt") || lower.includes("volt") || lower.includes("cel")) return "electric";
  if (lower.includes("rpm") || lower.includes("oil") || lower.includes("clt") || lower.includes("tps")) return "engine";
  return "custom";
}

export function inferSensorConfigs(sensors: SensorDefinition[]): SensorConfig[] {
  return sensors
    .filter((sensor) => sensor.key !== "Timestamp")
    .map((sensor, index) => ({
      id: sensor.key,
      sourceKey: sensor.key,
      aliases: [],
      label: sensor.label || sensor.key,
      unit: sensor.unit ?? "",
      group: groupForKey(sensor.key),
      scale: 1,
      offset: 0,
      precision: 2,
      color: COLORS[index % COLORS.length],
      showInDashboard: Boolean(sensor.recommendedCard),
      showInOverlay: Boolean(sensor.recommendedOverlay),
      showInSensorTable: true,
    }));
}

export function createDefaultLogReplaySettings(): LogReplaySettings {
  return {
    version: 1,
    sensors: [],
    derivedSensors: [
      {
        id: "ADXL_ax_mps2",
        label: "ADXL X m/s2",
        expression: "ADXL_ax_g * 9.80665",
        unit: "m/s2",
        group: "linear-accel",
        precision: 2,
        color: "#4cc9f0",
        fallback: "empty",
        enabled: false,
      },
    ],
    eventRules: [
      { id: "low-battery", label: "Batt low", expression: "Batt_V < 12", severity: "warning", enabled: true },
      {
        id: "low-oil-pressure",
        label: "Oil P low",
        expression: "OilPressure_bar < 1 && RPM > 3000",
        severity: "danger",
        enabled: true,
      },
      { id: "high-coolant", label: "CLT high", expression: "CLT_C > 110", severity: "warning", enabled: true },
    ],
    graphPresets: [
      { id: "engine", label: "Engine", sensorIds: ["RPM", "TPS_percent", "CLT_C", "OilPressure_bar"] },
      { id: "electric", label: "Electric", sensorIds: ["Batt_V", "CEL_Error"] },
      { id: "accel", label: "Accel", sensorIds: ["ADXL_ax_g", "ADXL_ay_g", "ADXL_az_g"] },
    ],
    gps: { latitudeKey: "Latitude", longitudeKey: "Longitude", speedKey: "GPS_Speed_KPH", jumpThresholdMeters: 80, smoothing: "off" },
    accel: {
      linear: {
        xKey: "ADXL_ax_g",
        yKey: "ADXL_ay_g",
        zKey: "ADXL_az_g",
        unit: "g",
        swapXY: false,
        invertX: false,
        invertY: false,
        invertZ: false,
        lowPassAlpha: 0.2,
      },
      angular: { xKey: "adu_x", yKey: "adu_y", zKey: "adu_z", unit: "degps", scale: 1, offset: 0 },
    },
    matlab: { variablePrefix: "muzil_", sanitizeVariableNames: true },
  };
}
```

- [ ] **Step 5: Run the tests and verify GREEN**

Run:

```powershell
cd Elec_app
npm test -- src/domain/logSettingsDefaults.test.ts
```

Expected: PASS.

---

### Task 2: Safe Formula Engine

**Files:**
- Create: `Elec_app/src/domain/formulaEngine.ts`
- Test: `Elec_app/src/domain/formulaEngine.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `Elec_app/src/domain/formulaEngine.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { evaluateFormula, validateFormula } from "./formulaEngine";

const values = { RPM: 6500, OilPressure_bar: 3.2, FrontPressure: 40, RearPressure: 60, Batt_V: 13.1 };

describe("formulaEngine", () => {
  test("evaluates arithmetic formulas with sensor names and functions", () => {
    expect(evaluateFormula("OilPressure_bar * 100", values)).toBe(320);
    expect(evaluateFormula("abs(RPM - 7000)", values)).toBe(500);
    expect(evaluateFormula("FrontPressure / (FrontPressure + RearPressure)", values)).toBe(0.4);
  });

  test("evaluates comparison and boolean formulas for event rules", () => {
    expect(evaluateFormula("OilPressure_bar < 1 && RPM > 3000", values)).toBe(false);
    expect(evaluateFormula("Batt_V >= 12 && RPM > 1000", values)).toBe(true);
  });

  test("rejects unsafe JavaScript syntax", () => {
    expect(validateFormula("globalThis.alert(1)").ok).toBe(false);
    expect(validateFormula("constructor.constructor('return 1')()").ok).toBe(false);
    expect(validateFormula("RPM; alert(1)").ok).toBe(false);
  });
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/domain/formulaEngine.test.ts
```

Expected: FAIL because `formulaEngine` does not exist.

- [ ] **Step 3: Implement a limited parser/evaluator**

Create `Elec_app/src/domain/formulaEngine.ts` with a tokenizer and recursive descent parser. Do not use `eval` or `Function`.

```ts
type FormulaValue = number | boolean;

interface Token {
  type: "number" | "identifier" | "operator" | "paren" | "comma";
  value: string;
}

const FUNCTIONS: Record<string, (...args: number[]) => number> = {
  min: Math.min,
  max: Math.max,
  abs: Math.abs,
  sqrt: Math.sqrt,
  round: Math.round,
  floor: Math.floor,
  ceil: Math.ceil,
};

function tokenize(input: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < input.length) {
    const char = input[i];
    if (/\s/.test(char)) {
      i += 1;
      continue;
    }
    const two = input.slice(i, i + 2);
    if ([">=", "<=", "==", "!=", "&&", "||"].includes(two)) {
      tokens.push({ type: "operator", value: two });
      i += 2;
      continue;
    }
    if ("+-*/><".includes(char)) {
      tokens.push({ type: "operator", value: char });
      i += 1;
      continue;
    }
    if ("()".includes(char)) {
      tokens.push({ type: "paren", value: char });
      i += 1;
      continue;
    }
    if (char === ",") {
      tokens.push({ type: "comma", value: char });
      i += 1;
      continue;
    }
    if (/[0-9.]/.test(char)) {
      const start = i;
      while (i < input.length && /[0-9.]/.test(input[i])) i += 1;
      tokens.push({ type: "number", value: input.slice(start, i) });
      continue;
    }
    if (/[A-Za-z_]/.test(char)) {
      const start = i;
      while (i < input.length && /[A-Za-z0-9_]/.test(input[i])) i += 1;
      tokens.push({ type: "identifier", value: input.slice(start, i) });
      continue;
    }
    throw new Error(`Unsupported token '${char}'`);
  }
  return tokens;
}

class Parser {
  private index = 0;

  constructor(
    private readonly tokens: Token[],
    private readonly values: Record<string, number>,
  ) {}

  parse(): FormulaValue {
    const value = this.parseOr();
    if (this.peek()) throw new Error(`Unexpected token '${this.peek()?.value}'`);
    return value;
  }

  private parseOr(): FormulaValue {
    let left = this.parseAnd();
    while (this.match("||")) left = Boolean(left) || Boolean(this.parseAnd());
    return left;
  }

  private parseAnd(): FormulaValue {
    let left = this.parseCompare();
    while (this.match("&&")) left = Boolean(left) && Boolean(this.parseCompare());
    return left;
  }

  private parseCompare(): FormulaValue {
    let left = this.parseAdd();
    const operator = this.peek()?.value;
    if ([">", ">=", "<", "<=", "==", "!="].includes(operator ?? "")) {
      this.index += 1;
      const right = this.parseAdd();
      if (operator === ">") return Number(left) > Number(right);
      if (operator === ">=") return Number(left) >= Number(right);
      if (operator === "<") return Number(left) < Number(right);
      if (operator === "<=") return Number(left) <= Number(right);
      if (operator === "==") return Number(left) === Number(right);
      return Number(left) !== Number(right);
    }
    return left;
  }

  private parseAdd(): number {
    let value = this.parseMul();
    while (true) {
      if (this.match("+")) value += this.parseMul();
      else if (this.match("-")) value -= this.parseMul();
      else return value;
    }
  }

  private parseMul(): number {
    let value = this.parseUnary();
    while (true) {
      if (this.match("*")) value *= this.parseUnary();
      else if (this.match("/")) value /= this.parseUnary();
      else return value;
    }
  }

  private parseUnary(): number {
    if (this.match("-")) return -this.parseUnary();
    return this.parsePrimary();
  }

  private parsePrimary(): number {
    const token = this.peek();
    if (!token) throw new Error("Unexpected end of formula");
    if (token.type === "number") {
      this.index += 1;
      const number = Number(token.value);
      if (!Number.isFinite(number)) throw new Error(`Invalid number '${token.value}'`);
      return number;
    }
    if (token.type === "identifier") {
      this.index += 1;
      const next = this.peek();
      if (next?.value === "(") {
        const fn = FUNCTIONS[token.value];
        if (!fn) throw new Error(`Unsupported function '${token.value}'`);
        this.index += 1;
        const args: number[] = [];
        if (this.peek()?.value !== ")") {
          do {
            args.push(Number(this.parseOr()));
          } while (this.match(","));
        }
        this.expect(")");
        return fn(...args);
      }
      const value = this.values[token.value];
      if (value === undefined || !Number.isFinite(value)) throw new Error(`Missing sensor '${token.value}'`);
      return value;
    }
    if (this.match("(")) {
      const value = Number(this.parseOr());
      this.expect(")");
      return value;
    }
    throw new Error(`Unexpected token '${token.value}'`);
  }

  private peek(): Token | undefined {
    return this.tokens[this.index];
  }

  private match(value: string): boolean {
    if (this.peek()?.value !== value) return false;
    this.index += 1;
    return true;
  }

  private expect(value: string): void {
    if (!this.match(value)) throw new Error(`Expected '${value}'`);
  }
}

export function evaluateFormula(expression: string, values: Record<string, number>): FormulaValue {
  return new Parser(tokenize(expression), values).parse();
}

export function validateFormula(expression: string): { ok: true } | { ok: false; error: string } {
  try {
    tokenize(expression);
    evaluateFormula(expression, {});
    return { ok: true };
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : String(cause);
    if (message.startsWith("Missing sensor")) return { ok: true };
    return { ok: false, error: message };
  }
}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
cd Elec_app
npm test -- src/domain/formulaEngine.test.ts
```

Expected: PASS.

---

### Task 3: Apply Settings To Parsed Sessions

**Files:**
- Create: `Elec_app/src/domain/logSessionTransform.ts`
- Test: `Elec_app/src/domain/logSessionTransform.test.ts`

- [ ] **Step 1: Write failing tests**

Create `Elec_app/src/domain/logSessionTransform.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { applyLogReplaySettings } from "./logSessionTransform";
import { createDefaultLogReplaySettings } from "./logSettingsDefaults";
import type { LogSession } from "./logReplayTypes";

const session: LogSession = {
  id: "demo",
  fileName: "demo.csv",
  columns: ["Timestamp", "rpm", "OilPressure_bar", "ADXL_ax_g"],
  sensors: [
    { key: "Timestamp", label: "Timestamp", type: "number" },
    { key: "rpm", label: "rpm", type: "number" },
    { key: "OilPressure_bar", label: "OilPressure_bar", type: "number", unit: "bar" },
    { key: "ADXL_ax_g", label: "ADXL_ax_g", type: "number", unit: "g" },
  ],
  samples: [
    { rowIndex: 1, timeMs: 0, values: { rpm: 6000, OilPressure_bar: 3.2, ADXL_ax_g: 1.1 } },
    { rowIndex: 2, timeMs: 100, values: { rpm: 7000, OilPressure_bar: 0.5, ADXL_ax_g: 1.2 } },
  ],
  summary: { rowCount: 2, durationMs: 100, startLabel: "0", endLabel: "0.1", invalidCounts: {} },
};

describe("applyLogReplaySettings", () => {
  test("maps aliases, applies scale and offset, and adds derived sensors", () => {
    const settings = createDefaultLogReplaySettings();
    settings.sensors = [
      {
        id: "RPM",
        sourceKey: "RPM",
        aliases: ["rpm"],
        label: "RPM",
        unit: "rpm",
        group: "engine",
        scale: 1,
        offset: 0,
        precision: 0,
        color: "#ffc300",
        showInDashboard: true,
        showInOverlay: true,
        showInSensorTable: true,
      },
      {
        id: "OilPressure_kPa_source",
        sourceKey: "OilPressure_bar",
        aliases: [],
        label: "Oil Pressure",
        unit: "kPa",
        group: "engine",
        scale: 100,
        offset: 0,
        precision: 1,
        color: "#4cc9f0",
        showInDashboard: true,
        showInOverlay: true,
        showInSensorTable: true,
      },
    ];
    settings.derivedSensors = [
      {
        id: "ADXL_ax_mps2",
        label: "ADXL X",
        expression: "ADXL_ax_g * 9.80665",
        unit: "m/s2",
        group: "linear-accel",
        precision: 2,
        color: "#f72585",
        fallback: "empty",
        enabled: true,
      },
    ];

    const transformed = applyLogReplaySettings(session, settings);

    expect(transformed.columns).toContain("RPM");
    expect(transformed.samples[0].values.RPM).toBe(6000);
    expect(transformed.samples[0].values.OilPressure_kPa_source).toBe(320);
    expect(transformed.samples[0].values.ADXL_ax_mps2).toBeCloseTo(10.787315);
  });
});
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/domain/logSessionTransform.test.ts
```

Expected: FAIL because `logSessionTransform` does not exist.

- [ ] **Step 3: Implement transform**

Create `Elec_app/src/domain/logSessionTransform.ts`:

```ts
import { evaluateFormula } from "./formulaEngine";
import type { LogSample, LogSession, SensorValue } from "./logReplayTypes";
import type { LogReplaySettings, SensorConfig } from "./logSettingsTypes";

function numberValue(value: SensorValue): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function resolveSource(sample: LogSample, config: SensorConfig): number | undefined {
  const keys = [config.sourceKey, ...config.aliases];
  for (const key of keys) {
    const value = numberValue(sample.values[key]);
    if (value !== undefined) return value;
  }
  return undefined;
}

export function applyLogReplaySettings(session: LogSession, settings: LogReplaySettings): LogSession {
  const configuredSensors = settings.sensors.filter((sensor) => sensor.showInSensorTable);
  const transformedSamples = session.samples.map((sample) => {
    const values: Record<string, SensorValue> = { ...sample.values };

    configuredSensors.forEach((config) => {
      const source = resolveSource(sample, config);
      if (source !== undefined) values[config.id] = source * config.scale + config.offset;
    });

    const numericValues = Object.fromEntries(
      Object.entries(values).filter(([, value]) => typeof value === "number" && Number.isFinite(value)),
    ) as Record<string, number>;

    settings.derivedSensors
      .filter((sensor) => sensor.enabled)
      .forEach((sensor) => {
        try {
          const value = evaluateFormula(sensor.expression, numericValues);
          values[sensor.id] = typeof value === "number" && Number.isFinite(value) ? value : null;
        } catch {
          values[sensor.id] = sensor.fallback === "zero" ? 0 : null;
        }
      });

    return { ...sample, values };
  });

  const configuredDefinitions = configuredSensors.map((sensor) => ({
    key: sensor.id,
    label: sensor.label,
    unit: sensor.unit,
    type: "number" as const,
    recommendedCard: sensor.showInDashboard,
    recommendedOverlay: sensor.showInOverlay,
  }));
  const derivedDefinitions = settings.derivedSensors
    .filter((sensor) => sensor.enabled)
    .map((sensor) => ({
      key: sensor.id,
      label: sensor.label,
      unit: sensor.unit,
      type: "number" as const,
      recommendedCard: false,
      recommendedOverlay: true,
    }));

  return {
    ...session,
    columns: Array.from(new Set([...session.columns, ...configuredDefinitions.map((sensor) => sensor.key), ...derivedDefinitions.map((sensor) => sensor.key)])),
    sensors: [...session.sensors, ...configuredDefinitions, ...derivedDefinitions],
    samples: transformedSamples,
  };
}
```

- [ ] **Step 4: Run transform tests and full domain tests**

Run:

```powershell
cd Elec_app
npm test -- src/domain/logSessionTransform.test.ts src/domain/formulaEngine.test.ts src/domain/logSettingsDefaults.test.ts
```

Expected: PASS.

---

### Task 4: Persist CSV And Settings In IndexedDB

**Files:**
- Create: `Elec_app/src/storage/logReplayStore.ts`
- Test: `Elec_app/src/storage/logReplayStore.test.ts`
- Modify: `Elec_app/src/test/setup.ts`

- [ ] **Step 1: Write failing persistence tests**

Create `Elec_app/src/storage/logReplayStore.test.ts`:

```ts
import { beforeEach, describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings } from "../domain/logSettingsDefaults";
import { loadLatestCsv, loadLogReplaySettings, saveLatestCsv, saveLogReplaySettings } from "./logReplayStore";

describe("logReplayStore", () => {
  beforeEach(async () => {
    indexedDB.deleteDatabase("muzil-tools-log-replay");
  });

  test("persists and loads the latest CSV text", async () => {
    await saveLatestCsv({ fileName: "run.csv", text: "Timestamp,RPM\n0,1000" });

    await expect(loadLatestCsv()).resolves.toEqual({ fileName: "run.csv", text: "Timestamp,RPM\n0,1000" });
  });

  test("persists and loads log replay settings", async () => {
    const settings = createDefaultLogReplaySettings();
    settings.gps.jumpThresholdMeters = 123;

    await saveLogReplaySettings(settings);

    await expect(loadLogReplaySettings()).resolves.toMatchObject({ gps: { jumpThresholdMeters: 123 } });
  });
});
```

- [ ] **Step 2: Add IndexedDB fake if tests need it**

If Vitest reports `indexedDB is not defined`, install a dev dependency:

```powershell
cd Elec_app
npm install -D fake-indexeddb
```

Then modify `Elec_app/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/storage/logReplayStore.test.ts
```

Expected: FAIL because `logReplayStore` does not exist.

- [ ] **Step 4: Implement IndexedDB store**

Create `Elec_app/src/storage/logReplayStore.ts`:

```ts
import type { LogReplaySettings } from "../domain/logSettingsTypes";

const DB_NAME = "muzil-tools-log-replay";
const STORE_NAME = "items";
const DB_VERSION = 1;

export interface StoredCsv {
  fileName: string;
  text: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function put<T>(key: string, value: T): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function get<T>(key: string): Promise<T | null> {
  const db = await openDb();
  const value = await new Promise<T | null>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get(key);
    request.onsuccess = () => resolve((request.result as T | undefined) ?? null);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return value;
}

export function saveLatestCsv(csv: StoredCsv): Promise<void> {
  return put("latest-csv", csv);
}

export function loadLatestCsv(): Promise<StoredCsv | null> {
  return get<StoredCsv>("latest-csv");
}

export function saveLogReplaySettings(settings: LogReplaySettings): Promise<void> {
  return put("settings", settings);
}

export function loadLogReplaySettings(): Promise<LogReplaySettings | null> {
  return get<LogReplaySettings>("settings");
}
```

- [ ] **Step 5: Run persistence tests**

Run:

```powershell
cd Elec_app
npm test -- src/storage/logReplayStore.test.ts
```

Expected: PASS.

---

### Task 5: Log Replay State, Inner Tabs, And Session Restore

**Files:**
- Create: `Elec_app/src/ui/logReplay/LogReplayInnerTabs.tsx`
- Modify: `Elec_app/src/ui/logReplay/LogReplayTab.tsx`
- Test: `Elec_app/src/ui/logReplay/LogReplayTab.test.tsx`

- [ ] **Step 1: Extend UI tests**

Add this test to `Elec_app/src/ui/logReplay/LogReplayTab.test.tsx`:

```ts
import userEvent from "@testing-library/user-event";

test("shows log analysis inner tabs for the replay workspace", () => {
  render(<LogReplayTab />);

  expect(screen.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Overlay" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "GPS" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "G-G / Accel" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/LogReplayTab.test.tsx
```

Expected: FAIL because inner tabs do not exist.

- [ ] **Step 3: Create inner tabs component**

Create `Elec_app/src/ui/logReplay/LogReplayInnerTabs.tsx`:

```tsx
export type LogReplayView = "dashboard" | "overlay" | "gps" | "accel" | "events" | "sensors" | "settings";

const TABS: Array<{ id: LogReplayView; label: string }> = [
  { id: "dashboard", label: "Dashboard" },
  { id: "overlay", label: "Overlay" },
  { id: "gps", label: "GPS" },
  { id: "accel", label: "G-G / Accel" },
  { id: "events", label: "Events" },
  { id: "sensors", label: "Sensors" },
  { id: "settings", label: "Settings" },
];

interface LogReplayInnerTabsProps {
  active: LogReplayView;
  onChange: (view: LogReplayView) => void;
}

export function LogReplayInnerTabs({ active, onChange }: LogReplayInnerTabsProps) {
  return (
    <nav className="log-inner-tabs" aria-label="로그 분석 화면">
      {TABS.map((tab) => (
        <button key={tab.id} type="button" className={active === tab.id ? "active" : ""} onClick={() => onChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 4: Wire tabs and persistence into `LogReplayTab`**

Modify `LogReplayTab.tsx`:

- Add `view` state with default `"dashboard"`.
- Load settings via `loadLogReplaySettings` or `createDefaultLogReplaySettings`.
- Load latest CSV with `loadLatestCsv`, parse it, and set `session`.
- On CSV upload, call `saveLatestCsv`.
- Render `LogReplayInnerTabs` above session content.
- Keep `PlaybackControls` visible when session exists.

The render logic should follow this shape:

```tsx
<CsvLogUploader session={session} error={error} onFileText={handleFileText} />
<LogReplayInnerTabs active={view} onChange={setView} />
{session && currentSample ? (
  <>
    <PlaybackControls ... />
    {view === "overlay" ? <SensorOverlayChart ... /> : null}
    {view === "gps" ? <GpsTrackPanel ... /> : null}
    {view === "accel" ? <GGDiagram ... /> : null}
    {view === "events" ? <EventStrip ... /> : null}
    {view === "settings" ? <LogSettingsPanel ... /> : null}
  </>
) : null}
```

- [ ] **Step 5: Run UI test**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/LogReplayTab.test.tsx
```

Expected: PASS.

---

### Task 6: Overlay Hover Tooltip

**Files:**
- Modify: `Elec_app/src/ui/logReplay/SensorOverlayChart.tsx`
- Test: `Elec_app/src/ui/logReplay/SensorOverlayChart.test.tsx`

- [ ] **Step 1: Write failing hover test**

Create `Elec_app/src/ui/logReplay/SensorOverlayChart.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { SensorOverlayChart } from "./SensorOverlayChart";
import type { LogSession } from "../../domain/logReplayTypes";

const session: LogSession = {
  id: "s",
  fileName: "s.csv",
  columns: ["Timestamp", "RPM", "TPS_percent"],
  sensors: [
    { key: "RPM", label: "RPM", unit: "rpm", type: "number" },
    { key: "TPS_percent", label: "TPS", unit: "%", type: "number" },
  ],
  samples: [
    { rowIndex: 1, timeMs: 0, values: { RPM: 1000, TPS_percent: 10 } },
    { rowIndex: 2, timeMs: 1000, values: { RPM: 2000, TPS_percent: 20 } },
  ],
  summary: { rowCount: 2, durationMs: 1000, startLabel: "0", endLabel: "1", invalidCounts: {} },
};

describe("SensorOverlayChart", () => {
  test("shows sensor values in a tooltip on hover", async () => {
    render(
      <SensorOverlayChart
        session={session}
        selectedKeys={["RPM", "TPS_percent"]}
        currentTimeMs={0}
        onSelectedKeysChange={vi.fn()}
        onSeek={vi.fn()}
      />,
    );

    const chart = screen.getByLabelText("선택 센서 오버랩 그래프").parentElement!;
    Object.defineProperty(chart, "getBoundingClientRect", {
      value: () => ({ left: 0, width: 100, top: 0, height: 100, right: 100, bottom: 100 }),
    });
    await userEvent.hover(chart);
    await userEvent.pointer({ target: chart, coords: { clientX: 100, clientY: 50 } });

    expect(screen.getByText("RPM")).toBeInTheDocument();
    expect(screen.getByText("2000 rpm")).toBeInTheDocument();
    expect(screen.getByText("TPS")).toBeInTheDocument();
    expect(screen.getByText("20 %")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/SensorOverlayChart.test.tsx
```

Expected: FAIL because tooltip does not exist.

- [ ] **Step 3: Implement hover state**

Modify `SensorOverlayChart.tsx`:

- Add `hoverTimeMs` state.
- On `onMouseMove`, compute time from pointer X.
- Use `findNearestSample(session.samples, hoverTimeMs)`.
- Render `.overlay-tooltip` with selected sensor label/value/unit.
- Hide tooltip on `onMouseLeave`.

- [ ] **Step 4: Run test**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/SensorOverlayChart.test.tsx
```

Expected: PASS.

---

### Task 7: GPS Projection And ADXL/ADU Separation

**Files:**
- Create: `Elec_app/src/domain/gpsProjection.ts`
- Test: `Elec_app/src/domain/gpsProjection.test.ts`
- Modify: `Elec_app/src/ui/logReplay/GpsTrackPanel.tsx`
- Modify: `Elec_app/src/ui/logReplay/GGDiagram.tsx`

- [ ] **Step 1: Write GPS projection tests**

Create `Elec_app/src/domain/gpsProjection.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { projectGpsPoints } from "./gpsProjection";

describe("projectGpsPoints", () => {
  test("projects latitude and longitude into local meter coordinates around the track center", () => {
    const points = projectGpsPoints([
      { lat: 37.0, lon: 127.0 },
      { lat: 37.001, lon: 127.001 },
    ]);

    expect(points).toHaveLength(2);
    expect(points[0].x).toBeLessThan(points[1].x);
    expect(points[0].y).toBeLessThan(points[1].y);
    expect(Math.abs(points[1].x - points[0].x)).toBeGreaterThan(80);
    expect(Math.abs(points[1].y - points[0].y)).toBeGreaterThan(100);
  });
});
```

- [ ] **Step 2: Implement GPS projection**

Create `Elec_app/src/domain/gpsProjection.ts`:

```ts
interface GpsPoint {
  lat: number;
  lon: number;
}

export interface ProjectedGpsPoint extends GpsPoint {
  x: number;
  y: number;
}

export function projectGpsPoints(points: GpsPoint[]): ProjectedGpsPoint[] {
  if (points.length === 0) return [];
  const centerLat = points.reduce((sum, point) => sum + point.lat, 0) / points.length;
  const centerLon = points.reduce((sum, point) => sum + point.lon, 0) / points.length;
  const metersPerDegreeLat = 111_320;
  const metersPerDegreeLon = 111_320 * Math.cos((centerLat * Math.PI) / 180);
  return points.map((point) => ({
    ...point,
    x: (point.lon - centerLon) * metersPerDegreeLon,
    y: (point.lat - centerLat) * metersPerDegreeLat,
  }));
}
```

- [ ] **Step 3: Run projection test**

Run:

```powershell
cd Elec_app
npm test -- src/domain/gpsProjection.test.ts
```

Expected: PASS.

- [ ] **Step 4: Update GPS panel**

Modify `GpsTrackPanel.tsx` to call `projectGpsPoints` before scaling to SVG. Keep current marker logic, but use projected `x/y` instead of raw longitude/latitude.

- [ ] **Step 5: Update G-G diagram input rules**

Modify `GGDiagram.tsx`:

- Prefer `ADXL_ax_g`/`ADXL_ay_g`.
- Fallback to `ax_g`/`ay_g`.
- Do not use `adu_x`/`adu_y` for G-G.
- Show a small note if only ADU angular values exist: "ADU 값은 각가속도/각속도 계열이라 G-G 입력으로 사용하지 않습니다."

Run:

```powershell
cd Elec_app
npm test -- src/domain/gpsProjection.test.ts
```

Expected: PASS.

---

### Task 8: Settings UI First Version

**Files:**
- Create: `Elec_app/src/ui/logReplay/LogSettingsPanel.tsx`
- Test: `Elec_app/src/ui/logReplay/LogSettingsPanel.test.tsx`
- Modify: `Elec_app/src/ui/logReplay/LogReplayTab.tsx`

- [ ] **Step 1: Write failing settings UI test**

Create `Elec_app/src/ui/logReplay/LogSettingsPanel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import { LogSettingsPanel } from "./LogSettingsPanel";

describe("LogSettingsPanel", () => {
  test("edits a sensor scale value", async () => {
    const settings = createDefaultLogReplaySettings();
    settings.sensors = [
      {
        id: "RPM",
        sourceKey: "RPM",
        aliases: [],
        label: "RPM",
        unit: "rpm",
        group: "engine",
        scale: 1,
        offset: 0,
        precision: 0,
        color: "#ffc300",
        showInDashboard: true,
        showInOverlay: true,
        showInSensorTable: true,
      },
    ];
    const onChange = vi.fn();

    render(<LogSettingsPanel settings={settings} onChange={onChange} />);

    await userEvent.clear(screen.getByLabelText("RPM scale"));
    await userEvent.type(screen.getByLabelText("RPM scale"), "2");

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ sensors: [expect.objectContaining({ scale: 2 })] }));
  });
});
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/LogSettingsPanel.test.tsx
```

Expected: FAIL because `LogSettingsPanel` does not exist.

- [ ] **Step 3: Implement settings panel**

Create `Elec_app/src/ui/logReplay/LogSettingsPanel.tsx`:

```tsx
import type { LogReplaySettings } from "../../domain/logSettingsTypes";

interface LogSettingsPanelProps {
  settings: LogReplaySettings;
  onChange: (settings: LogReplaySettings) => void;
}

export function LogSettingsPanel({ settings, onChange }: LogSettingsPanelProps) {
  function updateSensor(id: string, patch: Partial<LogReplaySettings["sensors"][number]>) {
    onChange({
      ...settings,
      sensors: settings.sensors.map((sensor) => (sensor.id === id ? { ...sensor, ...patch } : sensor)),
    });
  }

  return (
    <section className="panel log-settings-panel">
      <div className="section-heading">
        <h3>설정</h3>
        <span>센서 해석 규칙</span>
      </div>
      <div className="settings-table">
        {settings.sensors.map((sensor) => (
          <article key={sensor.id} className="settings-row">
            <strong>{sensor.label}</strong>
            <label>
              scale
              <input
                aria-label={`${sensor.label} scale`}
                type="number"
                value={sensor.scale}
                onChange={(event) => updateSensor(sensor.id, { scale: Number(event.target.value) })}
              />
            </label>
            <label>
              offset
              <input
                aria-label={`${sensor.label} offset`}
                type="number"
                value={sensor.offset}
                onChange={(event) => updateSensor(sensor.id, { offset: Number(event.target.value) })}
              />
            </label>
          </article>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run settings UI test**

Run:

```powershell
cd Elec_app
npm test -- src/ui/logReplay/LogSettingsPanel.test.tsx
```

Expected: PASS.

---

### Task 9: Dark Data-Logger Theme And Readability

**Files:**
- Modify: `Elec_app/src/styles.css`
- Browser verify: `http://127.0.0.1:5173/`

- [ ] **Step 1: Apply log replay theme classes**

Add CSS:

```css
.log-replay {
  --logger-bg: #000;
  --logger-panel: #2c2c2c;
  --logger-card: #111;
  --logger-line: #333;
  --logger-text: #e0e0e0;
  --logger-yellow: #ffc300;
}

.log-inner-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 16px 24px 0;
  border: 2px solid var(--logger-line);
  border-radius: 10px;
  background: var(--logger-bg);
  padding: 8px;
}

.log-inner-tabs button {
  flex: 1;
  min-width: 110px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--logger-text);
  padding: 10px;
  cursor: pointer;
}

.log-inner-tabs button.active {
  color: var(--logger-yellow);
  border-bottom-color: var(--logger-yellow);
}

.overlay-tooltip {
  position: absolute;
  z-index: 5;
  min-width: 160px;
  border: 1px solid var(--logger-yellow);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.86);
  color: var(--logger-text);
  padding: 8px;
  pointer-events: none;
}
```

- [ ] **Step 2: Browser verify no horizontal overflow**

Run dev server if needed:

```powershell
cd Elec_app
npm run dev
```

Open `http://127.0.0.1:5173/` and verify:

```js
document.documentElement.scrollWidth === document.documentElement.clientWidth
```

Expected: `true` at the current in-app browser width.

---

### Task 10: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Run targeted new tests**

Run:

```powershell
cd Elec_app
npm test -- src/domain/logSettingsDefaults.test.ts src/domain/formulaEngine.test.ts src/domain/logSessionTransform.test.ts src/domain/gpsProjection.test.ts src/storage/logReplayStore.test.ts src/ui/logReplay/LogReplayTab.test.tsx src/ui/logReplay/SensorOverlayChart.test.tsx src/ui/logReplay/LogSettingsPanel.test.tsx
```

Expected: all listed tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
cd Elec_app
npm test
```

Expected: all test files pass.

- [ ] **Step 3: Run production build**

Run:

```powershell
cd Elec_app
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Browser smoke test**

Open `http://127.0.0.1:5173/` and verify:

- `Muzil Tools` brand is visible.
- `로그 재생` screen opens.
- `CSV 업로드` button is visible.
- Internal tabs are visible.
- No static `test_run_0523.csv` preview text appears before upload.
- No horizontal overflow at the current in-app browser width.

---

## Self-Review

- Spec coverage: The plan covers settings, formula sensors, persistence, inner tabs, overlay tooltip, GPS projection, ADXL/ADU separation, UI readability, and final verification.
- Placeholder scan: No `TBD`, `TODO`, or "implement later" placeholders are present.
- Type consistency: `LogReplaySettings`, `SensorConfig`, `DerivedSensorConfig`, `EventRuleConfig`, `GraphPresetConfig`, `GpsConfig`, and `AccelConfig` are introduced in Task 1 and reused consistently in later tasks.

