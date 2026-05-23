# EMU Log Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EMU-LOGGER CSV 파일을 업로드해 주요 센서 카드, 4개 센서 오버레이 그래프, 재생바, GPS 경로, G-G 다이어그램, 이벤트 스트립으로 재생/분석하는 로그 재생 탭을 만든다.

**Architecture:** CSV 파싱과 로그 분석 로직은 `src/domain/logReplay*` 파일에 분리하고, React UI는 `src/ui/logReplay/` 아래 작은 컴포넌트로 나눈다. `App.tsx`에는 새 탭을 연결하는 최소 변경만 넣는다.

**Tech Stack:** Vite, React, TypeScript, Vitest, browser File APIs, SVG 기반 경량 시각화.

---

## File Structure

- Create: `src/domain/logReplayTypes.ts`
  - 로그 세션, 샘플, 센서 정의, 이벤트, 재생 상태 타입을 정의한다.
- Create: `src/domain/logReplayColumns.ts`
  - EMU-LOGGER 컬럼 표시명, 단위, 기본 카드 추천, 이벤트 기준값을 정의한다.
- Create: `src/domain/logReplayParser.ts`
  - CSV 텍스트를 `LogSession`으로 변환한다.
- Create: `src/domain/logReplayAnalysis.ts`
  - 가장 가까운 샘플 찾기, 값 정규화, 이벤트 추출, 세션 요약을 담당한다.
- Create: `src/domain/logReplayParser.test.ts`
  - CSV 파싱, 시간축, 컬럼 매핑 테스트.
- Create: `src/domain/logReplayAnalysis.test.ts`
  - playhead 샘플 선택, 최대 4개 센서 제한, 이벤트 추출 테스트.
- Create: `src/ui/logReplay/LogReplayTab.tsx`
  - 로그 재생 탭의 컨테이너 컴포넌트.
- Create: `src/ui/logReplay/CsvLogUploader.tsx`
  - CSV 파일 업로드와 세션 요약 표시.
- Create: `src/ui/logReplay/SensorCardGrid.tsx`
  - 주요 센서 카드 표시와 선택.
- Create: `src/ui/logReplay/SensorOverlayChart.tsx`
  - 최대 4개 센서 오버레이 그래프와 playhead 표시.
- Create: `src/ui/logReplay/PlaybackControls.tsx`
  - play/pause, scrubber, 배속, 현재 시간 표시.
- Create: `src/ui/logReplay/GpsTrackPanel.tsx`
  - GPS 경로와 현재 위치 표시.
- Create: `src/ui/logReplay/GGDiagram.tsx`
  - G-G 다이어그램과 현재 점 표시.
- Create: `src/ui/logReplay/EventStrip.tsx`
  - 이상 이벤트 마커와 클릭 이동.
- Modify: `src/App.tsx`
  - 기존 참조 탭 영역에 `로그 재생` 탭을 추가한다.
- Modify: `src/styles.css`
  - 로그 재생 화면의 레이아웃, 카드, 그래프, 타임라인 스타일을 추가한다.

---

### Task 1: Domain Types and Column Metadata

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayTypes.ts`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayColumns.ts`

- [ ] **Step 1: Create log replay types**

Create `src/domain/logReplayTypes.ts`:

```ts
export type SensorValue = number | string | null;

export type SensorType = "number" | "state" | "text";

export interface SensorDefinition {
  key: string;
  label: string;
  unit?: string;
  type: SensorType;
  recommendedCard?: boolean;
  recommendedOverlay?: boolean;
}

export interface LogSample {
  rowIndex: number;
  timeMs: number;
  rawTimestamp?: string;
  values: Record<string, SensorValue>;
}

export interface LogSessionSummary {
  rowCount: number;
  durationMs: number;
  startLabel: string;
  endLabel: string;
  estimatedSampleRateHz?: number;
  invalidCounts: Record<string, number>;
}

export interface LogSession {
  id: string;
  fileName: string;
  columns: string[];
  sensors: SensorDefinition[];
  samples: LogSample[];
  summary: LogSessionSummary;
}

export type LogEventSeverity = "info" | "warning" | "danger";

export interface LogEvent {
  id: string;
  type: string;
  severity: LogEventSeverity;
  timeMs: number;
  label: string;
  description: string;
  sensorKey?: string;
  value?: SensorValue;
}

export interface PlaybackState {
  currentTimeMs: number;
  isPlaying: boolean;
  speed: number;
}
```

- [ ] **Step 2: Create EMU column metadata**

Create `src/domain/logReplayColumns.ts`:

```ts
import type { SensorDefinition } from "./logReplayTypes";

export const EMU_SENSOR_DEFINITIONS: Record<string, Omit<SensorDefinition, "key">> = {
  Timestamp: { label: "Timestamp", type: "text" },
  RPM: { label: "RPM", unit: "rpm", type: "number", recommendedCard: true, recommendedOverlay: true },
  VSS_kmh: { label: "Vehicle Speed", unit: "km/h", type: "number", recommendedCard: true, recommendedOverlay: true },
  GPS_Speed_KPH: { label: "GPS Speed", unit: "km/h", type: "number" },
  Gear: { label: "Gear", type: "state", recommendedCard: true },
  TPS_percent: { label: "TPS", unit: "%", type: "number", recommendedCard: true, recommendedOverlay: true },
  CLT_C: { label: "Coolant Temp", unit: "C", type: "number", recommendedCard: true, recommendedOverlay: true },
  OilTemp_C: { label: "Oil Temp", unit: "C", type: "number", recommendedCard: true },
  EOT_OUT: { label: "EOT Out", unit: "C", type: "number" },
  IAT_C: { label: "IAT", unit: "C", type: "number" },
  OilPressure_bar: { label: "Oil Pressure", unit: "bar", type: "number", recommendedCard: true },
  FuelPressure_bar: { label: "Fuel Pressure", unit: "bar", type: "number", recommendedCard: true },
  Batt_V: { label: "Battery", unit: "V", type: "number", recommendedCard: true },
  CEL_Error: { label: "CEL", type: "state", recommendedCard: true },
  Latitude: { label: "Latitude", type: "number" },
  Longitude: { label: "Longitude", type: "number" },
  Altitude_m: { label: "Altitude", unit: "m", type: "number" },
  Heading_deg: { label: "Heading", unit: "deg", type: "number" },
  ax_g: { label: "Accel X", unit: "g", type: "number" },
  ay_g: { label: "Accel Y", unit: "g", type: "number" },
  az_g: { label: "Accel Z", unit: "g", type: "number" },
  ADU_ax_g: { label: "ADU Accel X", unit: "g", type: "number" },
  ADU_ay_g: { label: "ADU Accel Y", unit: "g", type: "number" },
  ADU_az_g: { label: "ADU Accel Z", unit: "g", type: "number" },
};

export const DEFAULT_CARD_KEYS = [
  "RPM",
  "VSS_kmh",
  "Gear",
  "TPS_percent",
  "CLT_C",
  "OilTemp_C",
  "OilPressure_bar",
  "FuelPressure_bar",
  "Batt_V",
  "CEL_Error",
];

export const DEFAULT_OVERLAY_KEYS = ["RPM", "TPS_percent", "VSS_kmh", "CLT_C"];

export const EVENT_THRESHOLDS = {
  lowBatteryV: 11.5,
  highCoolantC: 105,
  highOilTempC: 125,
  lowOilPressureBar: 1.0,
  lowFuelPressureBar: 2.5,
};
```

- [ ] **Step 3: Run type check**

Run:

```bash
npm.cmd run build
```

Expected: build may still pass with no references to the new files.

---

### Task 2: CSV Parser

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayParser.test.ts`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayParser.ts`

- [ ] **Step 1: Write failing parser tests**

Create `src/domain/logReplayParser.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseEmuLogCsv } from "./logReplayParser";

describe("parseEmuLogCsv", () => {
  it("parses EMU-LOGGER CSV rows and maps sensor metadata", () => {
    const csv = [
      "Timestamp,RPM,VSS_kmh,TPS_percent,CLT_C,Batt_V,CEL_Error",
      "0.00,1000,0,2.5,82,12.4,0",
      "0.05,1200,1.5,4.0,82.1,12.3,0",
    ].join("\n");

    const session = parseEmuLogCsv(csv, "sample.csv");

    expect(session.fileName).toBe("sample.csv");
    expect(session.samples).toHaveLength(2);
    expect(session.samples[1].timeMs).toBe(50);
    expect(session.samples[1].values.RPM).toBe(1200);
    expect(session.sensors.find((sensor) => sensor.key === "CLT_C")?.unit).toBe("C");
    expect(session.summary.estimatedSampleRateHz).toBeCloseTo(20);
  });

  it("tracks invalid numeric values without crashing", () => {
    const csv = [
      "Timestamp,RPM,Batt_V",
      "0.00,1000,12.4",
      "0.05,not-number,",
    ].join("\n");

    const session = parseEmuLogCsv(csv, "bad.csv");

    expect(session.samples[1].values.RPM).toBeNull();
    expect(session.samples[1].values.Batt_V).toBeNull();
    expect(session.summary.invalidCounts.RPM).toBe(1);
    expect(session.summary.invalidCounts.Batt_V).toBe(1);
  });
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
npm.cmd test -- src/domain/logReplayParser.test.ts
```

Expected: FAIL because `logReplayParser.ts` does not exist.

- [ ] **Step 3: Implement CSV parser**

Create `src/domain/logReplayParser.ts`:

```ts
import { EMU_SENSOR_DEFINITIONS } from "./logReplayColumns";
import type { LogSample, LogSession, SensorDefinition, SensorValue } from "./logReplayTypes";

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  cells.push(current.trim());
  return cells;
}

function parseTimeMs(value: string | undefined, rowIndex: number): number {
  if (!value) return rowIndex * 50;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric < 10_000 ? numeric * 1000 : numeric;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : rowIndex * 50;
}

function inferSensor(column: string, values: SensorValue[]): SensorDefinition {
  const known = EMU_SENSOR_DEFINITIONS[column];
  if (known) return { key: column, ...known };

  const hasNumber = values.some((value) => typeof value === "number");
  return {
    key: column,
    label: column,
    type: hasNumber ? "number" : "text",
  };
}

export function parseEmuLogCsv(text: string, fileName: string): LogSession {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error("CSV에는 헤더와 최소 1개 이상의 데이터 행이 필요합니다.");
  }

  const columns = splitCsvLine(lines[0]);
  if (columns.length === 0 || columns.some((column) => !column)) {
    throw new Error("CSV 헤더를 읽을 수 없습니다.");
  }

  const invalidCounts: Record<string, number> = {};
  const samples: LogSample[] = lines.slice(1).map((line, rowIndex) => {
    const cells = splitCsvLine(line);
    const values: Record<string, SensorValue> = {};

    columns.forEach((column, columnIndex) => {
      const raw = cells[columnIndex] ?? "";
      const known = EMU_SENSOR_DEFINITIONS[column];
      const shouldParseNumber = known?.type === "number" || (known === undefined && raw !== "" && Number.isFinite(Number(raw)));

      if (raw === "") {
        values[column] = null;
        invalidCounts[column] = (invalidCounts[column] ?? 0) + 1;
      } else if (shouldParseNumber) {
        const parsed = Number(raw);
        if (Number.isFinite(parsed)) {
          values[column] = parsed;
        } else {
          values[column] = null;
          invalidCounts[column] = (invalidCounts[column] ?? 0) + 1;
        }
      } else {
        values[column] = raw;
      }
    });

    const firstTimeMs = parseTimeMs(String(values.Timestamp ?? ""), rowIndex);
    return {
      rowIndex,
      timeMs: firstTimeMs,
      rawTimestamp: String(values.Timestamp ?? ""),
      values,
    };
  });

  const baseTime = samples[0]?.timeMs ?? 0;
  const normalizedSamples = samples.map((sample) => ({
    ...sample,
    timeMs: Math.max(0, sample.timeMs - baseTime),
  }));

  const sensors = columns.map((column) =>
    inferSensor(
      column,
      normalizedSamples.map((sample) => sample.values[column]),
    ),
  );

  const durationMs = normalizedSamples.at(-1)?.timeMs ?? 0;
  const averageDeltaMs = normalizedSamples.length > 1 ? durationMs / (normalizedSamples.length - 1) : 0;

  return {
    id: `${fileName}-${Date.now()}`,
    fileName,
    columns,
    sensors,
    samples: normalizedSamples,
    summary: {
      rowCount: normalizedSamples.length,
      durationMs,
      startLabel: normalizedSamples[0]?.rawTimestamp ?? "0",
      endLabel: normalizedSamples.at(-1)?.rawTimestamp ?? "0",
      estimatedSampleRateHz: averageDeltaMs > 0 ? 1000 / averageDeltaMs : undefined,
      invalidCounts,
    },
  };
}
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
npm.cmd test -- src/domain/logReplayParser.test.ts
```

Expected: PASS.

---

### Task 3: Log Analysis Helpers

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayAnalysis.test.ts`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\domain\logReplayAnalysis.ts`

- [ ] **Step 1: Write failing analysis tests**

Create `src/domain/logReplayAnalysis.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { extractLogEvents, findNearestSample, limitOverlaySelection, normalizeSeries } from "./logReplayAnalysis";
import { parseEmuLogCsv } from "./logReplayParser";

const session = parseEmuLogCsv(
  [
    "Timestamp,RPM,VSS_kmh,TPS_percent,CLT_C,Batt_V,CEL_Error,OilPressure_bar,FuelPressure_bar",
    "0.00,1000,0,2,80,12.4,0,2.0,3.2",
    "0.05,5000,50,70,106,10.9,1,0.7,2.0",
    "0.10,4000,45,30,98,12.1,0,1.6,3.0",
  ].join("\n"),
  "events.csv",
);

describe("log replay analysis", () => {
  it("finds the nearest sample for a playhead time", () => {
    expect(findNearestSample(session.samples, 60)?.values.RPM).toBe(5000);
  });

  it("limits overlay selection to four keys", () => {
    expect(limitOverlaySelection(["RPM", "TPS_percent", "VSS_kmh", "CLT_C", "Batt_V"], "OilTemp_C")).toEqual([
      "RPM",
      "TPS_percent",
      "VSS_kmh",
      "CLT_C",
    ]);
  });

  it("normalizes numeric series to 0..1", () => {
    expect(normalizeSeries([10, 20, 30])).toEqual([0, 0.5, 1]);
  });

  it("extracts warning and danger events", () => {
    const events = extractLogEvents(session);
    expect(events.map((event) => event.type)).toContain("cel");
    expect(events.map((event) => event.type)).toContain("low-battery");
    expect(events.map((event) => event.type)).toContain("high-coolant");
    expect(events.map((event) => event.type)).toContain("low-oil-pressure");
    expect(events.map((event) => event.type)).toContain("low-fuel-pressure");
  });
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
npm.cmd test -- src/domain/logReplayAnalysis.test.ts
```

Expected: FAIL because `logReplayAnalysis.ts` does not exist.

- [ ] **Step 3: Implement analysis helpers**

Create `src/domain/logReplayAnalysis.ts`:

```ts
import { EVENT_THRESHOLDS } from "./logReplayColumns";
import type { LogEvent, LogSample, LogSession, SensorValue } from "./logReplayTypes";

function numeric(value: SensorValue): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function findNearestSample(samples: LogSample[], timeMs: number): LogSample | undefined {
  if (samples.length === 0) return undefined;
  let low = 0;
  let high = samples.length - 1;

  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (samples[mid].timeMs < timeMs) low = mid + 1;
    else high = mid;
  }

  const current = samples[low];
  const previous = samples[low - 1];
  if (!previous) return current;
  return Math.abs(previous.timeMs - timeMs) <= Math.abs(current.timeMs - timeMs) ? previous : current;
}

export function limitOverlaySelection(current: string[], nextKey: string): string[] {
  if (current.includes(nextKey)) return current.filter((key) => key !== nextKey);
  if (current.length >= 4) return current;
  return [...current, nextKey];
}

export function normalizeSeries(values: number[]): number[] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return values.map(() => 0);
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return values.map(() => 0.5);
  return values.map((value) => (Number.isFinite(value) ? (value - min) / (max - min) : 0));
}

function addEvent(events: LogEvent[], event: Omit<LogEvent, "id">): void {
  events.push({ id: `${event.type}-${event.timeMs}-${events.length}`, ...event });
}

export function extractLogEvents(session: LogSession): LogEvent[] {
  const events: LogEvent[] = [];

  session.samples.forEach((sample) => {
    const cel = numeric(sample.values.CEL_Error);
    if (cel !== undefined && cel !== 0) {
      addEvent(events, {
        type: "cel",
        severity: "danger",
        timeMs: sample.timeMs,
        label: "CEL",
        description: `CEL_Error가 ${cel}입니다.`,
        sensorKey: "CEL_Error",
        value: cel,
      });
    }

    const batt = numeric(sample.values.Batt_V);
    if (batt !== undefined && batt < EVENT_THRESHOLDS.lowBatteryV) {
      addEvent(events, {
        type: "low-battery",
        severity: "warning",
        timeMs: sample.timeMs,
        label: "Batt low",
        description: `배터리 전압이 ${batt.toFixed(1)}V로 낮습니다.`,
        sensorKey: "Batt_V",
        value: batt,
      });
    }

    const coolant = numeric(sample.values.CLT_C);
    if (coolant !== undefined && coolant >= EVENT_THRESHOLDS.highCoolantC) {
      addEvent(events, {
        type: "high-coolant",
        severity: "warning",
        timeMs: sample.timeMs,
        label: "CLT high",
        description: `수온이 ${coolant.toFixed(1)}C입니다.`,
        sensorKey: "CLT_C",
        value: coolant,
      });
    }

    const oilPressure = numeric(sample.values.OilPressure_bar);
    if (oilPressure !== undefined && oilPressure < EVENT_THRESHOLDS.lowOilPressureBar) {
      addEvent(events, {
        type: "low-oil-pressure",
        severity: "danger",
        timeMs: sample.timeMs,
        label: "Oil P low",
        description: `유압이 ${oilPressure.toFixed(1)}bar로 낮습니다.`,
        sensorKey: "OilPressure_bar",
        value: oilPressure,
      });
    }

    const fuelPressure = numeric(sample.values.FuelPressure_bar);
    if (fuelPressure !== undefined && fuelPressure < EVENT_THRESHOLDS.lowFuelPressureBar) {
      addEvent(events, {
        type: "low-fuel-pressure",
        severity: "warning",
        timeMs: sample.timeMs,
        label: "Fuel P low",
        description: `연압이 ${fuelPressure.toFixed(1)}bar로 낮습니다.`,
        sensorKey: "FuelPressure_bar",
        value: fuelPressure,
      });
    }
  });

  return events;
}
```

- [ ] **Step 4: Run analysis tests**

Run:

```bash
npm.cmd test -- src/domain/logReplayAnalysis.test.ts
```

Expected: PASS.

---

### Task 4: Log Replay Container and Uploader

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\LogReplayTab.tsx`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\CsvLogUploader.tsx`

- [ ] **Step 1: Implement uploader**

Create `src/ui/logReplay/CsvLogUploader.tsx`:

```tsx
import type { LogSession } from "../../domain/logReplayTypes";

interface CsvLogUploaderProps {
  session: LogSession | null;
  error: string | null;
  onFileText: (fileName: string, text: string) => void;
}

export function CsvLogUploader({ session, error, onFileText }: CsvLogUploaderProps) {
  async function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      onFileText(file.name, "");
      return;
    }
    onFileText(file.name, await file.text());
  }

  return (
    <section className="panel log-uploader">
      <div>
        <h2>EMU 로그 재생</h2>
        <p>EMU-LOGGER CSV를 업로드해서 차량 상태를 시간축에 맞춰 재생합니다.</p>
      </div>
      <label className="file-picker">
        <input type="file" accept=".csv,text/csv" onChange={handleChange} />
        CSV 업로드
      </label>
      {error ? <p className="error-text">{error}</p> : null}
      {session ? (
        <div className="log-summary-grid">
          <span>파일: {session.fileName}</span>
          <span>행: {session.summary.rowCount.toLocaleString()}</span>
          <span>길이: {(session.summary.durationMs / 1000).toFixed(1)}s</span>
          <span>추정 주기: {session.summary.estimatedSampleRateHz?.toFixed(1) ?? "-"}Hz</span>
        </div>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 2: Implement container state**

Create `src/ui/logReplay/LogReplayTab.tsx`:

```tsx
import { useMemo, useState } from "react";
import { DEFAULT_CARD_KEYS, DEFAULT_OVERLAY_KEYS } from "../../domain/logReplayColumns";
import { extractLogEvents, findNearestSample } from "../../domain/logReplayAnalysis";
import { parseEmuLogCsv } from "../../domain/logReplayParser";
import type { LogSession, PlaybackState } from "../../domain/logReplayTypes";
import { CsvLogUploader } from "./CsvLogUploader";

export function LogReplayTab() {
  const [session, setSession] = useState<LogSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playback, setPlayback] = useState<PlaybackState>({ currentTimeMs: 0, isPlaying: false, speed: 1 });
  const [cardKeys, setCardKeys] = useState<string[]>(DEFAULT_CARD_KEYS);
  const [overlayKeys, setOverlayKeys] = useState<string[]>(DEFAULT_OVERLAY_KEYS);

  const events = useMemo(() => (session ? extractLogEvents(session) : []), [session]);
  const currentSample = useMemo(
    () => (session ? findNearestSample(session.samples, playback.currentTimeMs) : undefined),
    [session, playback.currentTimeMs],
  );

  function handleFileText(fileName: string, text: string) {
    if (!fileName.toLowerCase().endsWith(".csv")) {
      setError("CSV 파일만 업로드할 수 있습니다.");
      return;
    }
    try {
      const parsed = parseEmuLogCsv(text, fileName);
      setSession(parsed);
      setError(null);
      setPlayback({ currentTimeMs: 0, isPlaying: false, speed: 1 });
      setCardKeys(DEFAULT_CARD_KEYS.filter((key) => parsed.columns.includes(key)));
      setOverlayKeys(DEFAULT_OVERLAY_KEYS.filter((key) => parsed.columns.includes(key)).slice(0, 4));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CSV를 읽지 못했습니다.");
    }
  }

  return (
    <div className="log-replay">
      <CsvLogUploader session={session} error={error} onFileText={handleFileText} />
      {session && currentSample ? (
        <div className="log-replay-workspace">
          <p className="muted">
            현재 샘플: #{currentSample.rowIndex + 1}, 이벤트 {events.length}개, 카드 {cardKeys.length}개, 오버레이 {overlayKeys.length}개
          </p>
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 3: Run build**

Run:

```bash
npm.cmd run build
```

Expected: PASS after later unused-state warnings are either acceptable or fixed by rendering child components in following tasks.

---

### Task 5: Sensor Cards and Playback Controls

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\SensorCardGrid.tsx`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\PlaybackControls.tsx`
- Modify: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\LogReplayTab.tsx`

- [ ] **Step 1: Create sensor card grid**

Create `src/ui/logReplay/SensorCardGrid.tsx`:

```tsx
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface SensorCardGridProps {
  session: LogSession;
  sample: LogSample;
  selectedKeys: string[];
  onToggleKey: (key: string) => void;
}

export function SensorCardGrid({ session, sample, selectedKeys, onToggleKey }: SensorCardGridProps) {
  const available = session.sensors.filter((sensor) => sensor.type === "number" || sensor.type === "state");

  return (
    <section className="panel sensor-card-section">
      <div className="section-heading">
        <h3>주요 센서 카드</h3>
        <span>{selectedKeys.length}개 선택</span>
      </div>
      <div className="sensor-picker-row">
        {available.map((sensor) => (
          <button
            key={sensor.key}
            className={selectedKeys.includes(sensor.key) ? "chip selected" : "chip"}
            type="button"
            onClick={() => onToggleKey(sensor.key)}
          >
            {sensor.label}
          </button>
        ))}
      </div>
      <div className="sensor-card-grid">
        {selectedKeys.map((key) => {
          const sensor = session.sensors.find((item) => item.key === key);
          const value = sample.values[key];
          return (
            <article className="sensor-card" key={key}>
              <span>{sensor?.label ?? key}</span>
              <strong>{value ?? "-"}</strong>
              <small>{sensor?.unit ?? ""}</small>
            </article>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create playback controls**

Create `src/ui/logReplay/PlaybackControls.tsx`:

```tsx
import type { LogEvent, LogSession, PlaybackState } from "../../domain/logReplayTypes";

interface PlaybackControlsProps {
  session: LogSession;
  playback: PlaybackState;
  events: LogEvent[];
  onPlaybackChange: (next: PlaybackState) => void;
  onSeek: (timeMs: number) => void;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds - minutes * 60;
  return `${minutes}:${seconds.toFixed(1).padStart(4, "0")}`;
}

export function PlaybackControls({ session, playback, events, onPlaybackChange, onSeek }: PlaybackControlsProps) {
  const duration = Math.max(1, session.summary.durationMs);

  function jumpToEvent(direction: -1 | 1) {
    const sorted = [...events].sort((a, b) => a.timeMs - b.timeMs);
    const target =
      direction > 0
        ? sorted.find((event) => event.timeMs > playback.currentTimeMs)
        : sorted.reverse().find((event) => event.timeMs < playback.currentTimeMs);
    if (target) onSeek(target.timeMs);
  }

  return (
    <section className="panel playback-panel">
      <div className="playback-controls">
        <button type="button" onClick={() => onSeek(0)}>처음</button>
        <button type="button" onClick={() => jumpToEvent(-1)}>이전 이벤트</button>
        <button type="button" onClick={() => onPlaybackChange({ ...playback, isPlaying: !playback.isPlaying })}>
          {playback.isPlaying ? "일시정지" : "재생"}
        </button>
        <button type="button" onClick={() => jumpToEvent(1)}>다음 이벤트</button>
        <select
          value={playback.speed}
          onChange={(event) => onPlaybackChange({ ...playback, speed: Number(event.target.value) })}
        >
          {[0.25, 0.5, 1, 2, 4].map((speed) => (
            <option key={speed} value={speed}>{speed}x</option>
          ))}
        </select>
        <span>{formatTime(playback.currentTimeMs)} / {formatTime(duration)}</span>
      </div>
      <input
        className="playback-range"
        type="range"
        min={0}
        max={duration}
        value={Math.min(playback.currentTimeMs, duration)}
        onChange={(event) => onSeek(Number(event.target.value))}
      />
    </section>
  );
}
```

- [ ] **Step 3: Wire cards and controls into container**

Modify `LogReplayTab.tsx` imports:

```ts
import { useEffect, useMemo, useState } from "react";
import { PlaybackControls } from "./PlaybackControls";
import { SensorCardGrid } from "./SensorCardGrid";
```

Add playback timer inside `LogReplayTab`:

```tsx
  useEffect(() => {
    if (!session || !playback.isPlaying) return undefined;
    const startedAt = performance.now();
    const startTime = playback.currentTimeMs;
    const timer = window.setInterval(() => {
      const elapsed = (performance.now() - startedAt) * playback.speed;
      setPlayback((current) => {
        const nextTime = Math.min(session.summary.durationMs, startTime + elapsed);
        return { ...current, currentTimeMs: nextTime, isPlaying: nextTime < session.summary.durationMs };
      });
    }, 100);
    return () => window.clearInterval(timer);
  }, [session, playback.isPlaying, playback.currentTimeMs, playback.speed]);

  function toggleCardKey(key: string) {
    setCardKeys((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  }

  function seek(timeMs: number) {
    setPlayback((current) => ({ ...current, currentTimeMs: timeMs }));
  }
```

Replace the placeholder workspace with:

```tsx
        <div className="log-replay-workspace">
          <SensorCardGrid session={session} sample={currentSample} selectedKeys={cardKeys} onToggleKey={toggleCardKey} />
          <PlaybackControls session={session} playback={playback} events={events} onPlaybackChange={setPlayback} onSeek={seek} />
        </div>
```

- [ ] **Step 4: Run build**

Run:

```bash
npm.cmd run build
```

Expected: PASS.

---

### Task 6: Overlay Chart and Event Strip

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\SensorOverlayChart.tsx`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\EventStrip.tsx`
- Modify: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\LogReplayTab.tsx`

- [ ] **Step 1: Create overlay chart**

Create `src/ui/logReplay/SensorOverlayChart.tsx`:

```tsx
import { limitOverlaySelection, normalizeSeries } from "../../domain/logReplayAnalysis";
import type { LogSession } from "../../domain/logReplayTypes";

interface SensorOverlayChartProps {
  session: LogSession;
  selectedKeys: string[];
  currentTimeMs: number;
  onSelectedKeysChange: (keys: string[]) => void;
  onSeek: (timeMs: number) => void;
}

const COLORS = ["#22c55e", "#38bdf8", "#facc15", "#f97316"];

export function SensorOverlayChart({ session, selectedKeys, currentTimeMs, onSelectedKeysChange, onSeek }: SensorOverlayChartProps) {
  const numericSensors = session.sensors.filter((sensor) => sensor.type === "number" && sensor.key !== "Timestamp");
  const duration = Math.max(1, session.summary.durationMs);
  const playheadX = (currentTimeMs / duration) * 100;

  function pathFor(key: string): string {
    const values = session.samples.map((sample) => Number(sample.values[key]));
    const normalized = normalizeSeries(values);
    return normalized
      .map((value, index) => {
        const sample = session.samples[index];
        const x = (sample.timeMs / duration) * 800;
        const y = 220 - value * 190;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }

  return (
    <section className="panel overlay-panel">
      <div className="section-heading">
        <h3>센서 오버레이</h3>
        <span>최대 4개</span>
      </div>
      <div className="sensor-picker-row">
        {numericSensors.map((sensor) => (
          <button
            key={sensor.key}
            className={selectedKeys.includes(sensor.key) ? "chip selected" : "chip"}
            type="button"
            onClick={() => onSelectedKeysChange(limitOverlaySelection(selectedKeys, sensor.key))}
          >
            {sensor.label}
          </button>
        ))}
      </div>
      <div className="overlay-legend">
        {selectedKeys.map((key, index) => (
          <span key={key} style={{ color: COLORS[index] }}>{session.sensors.find((sensor) => sensor.key === key)?.label ?? key}</span>
        ))}
      </div>
      <div className="overlay-chart" onClick={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        onSeek(((event.clientX - bounds.left) / bounds.width) * duration);
      }}>
        <svg viewBox="0 0 800 240" preserveAspectRatio="none" aria-label="선택 센서 오버레이 그래프">
          {[0, 1, 2, 3].map((line) => <line key={line} x1="0" x2="800" y1={30 + line * 55} y2={30 + line * 55} className="chart-grid" />)}
          {selectedKeys.map((key, index) => <path key={key} d={pathFor(key)} fill="none" stroke={COLORS[index]} strokeWidth="4" />)}
        </svg>
        <div className="playhead-line" style={{ left: `${playheadX}%` }} />
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create event strip**

Create `src/ui/logReplay/EventStrip.tsx`:

```tsx
import type { LogEvent, LogSession } from "../../domain/logReplayTypes";

interface EventStripProps {
  session: LogSession;
  events: LogEvent[];
  currentTimeMs: number;
  onSeek: (timeMs: number) => void;
}

export function EventStrip({ session, events, currentTimeMs, onSeek }: EventStripProps) {
  const duration = Math.max(1, session.summary.durationMs);

  return (
    <section className="panel event-strip-panel">
      <div className="section-heading">
        <h3>이벤트 / 이상값</h3>
        <span>{events.length}개</span>
      </div>
      <div className="event-strip">
        <div className="playhead-line" style={{ left: `${(currentTimeMs / duration) * 100}%` }} />
        {events.map((event) => (
          <button
            key={event.id}
            className={`event-marker ${event.severity}`}
            type="button"
            style={{ left: `${(event.timeMs / duration) * 100}%` }}
            title={event.description}
            onClick={() => onSeek(event.timeMs)}
          >
            {event.label}
          </button>
        ))}
      </div>
      <div className="event-list">
        {events.slice(0, 8).map((event) => (
          <button key={event.id} type="button" onClick={() => onSeek(event.timeMs)}>
            <strong>{event.label}</strong>
            <span>{(event.timeMs / 1000).toFixed(2)}s</span>
            <small>{event.description}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Wire chart and events**

Modify `LogReplayTab.tsx` imports:

```ts
import { EventStrip } from "./EventStrip";
import { SensorOverlayChart } from "./SensorOverlayChart";
```

Add inside `.log-replay-workspace` after `PlaybackControls`:

```tsx
          <SensorOverlayChart
            session={session}
            selectedKeys={overlayKeys}
            currentTimeMs={playback.currentTimeMs}
            onSelectedKeysChange={setOverlayKeys}
            onSeek={seek}
          />
          <EventStrip session={session} events={events} currentTimeMs={playback.currentTimeMs} onSeek={seek} />
```

- [ ] **Step 4: Run tests and build**

Run:

```bash
npm.cmd test -- src/domain/logReplayAnalysis.test.ts src/domain/logReplayParser.test.ts
npm.cmd run build
```

Expected: PASS.

---

### Task 7: GPS and G-G Panels

**Files:**
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\GpsTrackPanel.tsx`
- Create: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\GGDiagram.tsx`
- Modify: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\ui\logReplay\LogReplayTab.tsx`

- [ ] **Step 1: Create GPS track panel**

Create `src/ui/logReplay/GpsTrackPanel.tsx`:

```tsx
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GpsTrackPanelProps {
  session: LogSession;
  currentSample: LogSample;
}

function scale(value: number, min: number, max: number, size: number): number {
  if (min === max) return size / 2;
  return ((value - min) / (max - min)) * size;
}

export function GpsTrackPanel({ session, currentSample }: GpsTrackPanelProps) {
  const points = session.samples
    .map((sample) => ({ lat: Number(sample.values.Latitude), lon: Number(sample.values.Longitude), sample }))
    .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon));

  if (points.length < 2) {
    return <section className="panel empty-panel">GPS 컬럼이 없거나 경로를 그리기에 데이터가 부족합니다.</section>;
  }

  const lats = points.map((point) => point.lat);
  const lons = points.map((point) => point.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const path = points
    .map((point, index) => {
      const x = scale(point.lon, minLon, maxLon, 500);
      const y = 300 - scale(point.lat, minLat, maxLat, 300);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  const currentLat = Number(currentSample.values.Latitude);
  const currentLon = Number(currentSample.values.Longitude);
  const currentX = scale(currentLon, minLon, maxLon, 500);
  const currentY = 300 - scale(currentLat, minLat, maxLat, 300);

  return (
    <section className="panel gps-panel">
      <div className="section-heading">
        <h3>GPS 경로</h3>
        <span>{points.length.toLocaleString()} points</span>
      </div>
      <svg viewBox="0 0 500 300" preserveAspectRatio="xMidYMid meet" aria-label="GPS 경로">
        <path d={path} fill="none" stroke="#38bdf8" strokeWidth="4" />
        {Number.isFinite(currentX) && Number.isFinite(currentY) ? <circle cx={currentX} cy={currentY} r="8" fill="#facc15" /> : null}
      </svg>
    </section>
  );
}
```

- [ ] **Step 2: Create G-G diagram**

Create `src/ui/logReplay/GGDiagram.tsx`:

```tsx
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GGDiagramProps {
  session: LogSession;
  currentSample: LogSample;
}

function getAccel(sample: LogSample, primary: string, fallback: string): number {
  const value = sample.values[primary] ?? sample.values[fallback];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toPoint(ax: number, ay: number) {
  const range = 2;
  return {
    x: 150 + Math.max(-range, Math.min(range, ay)) * 65,
    y: 150 - Math.max(-range, Math.min(range, ax)) * 65,
  };
}

export function GGDiagram({ session, currentSample }: GGDiagramProps) {
  const hasAccel = session.columns.includes("ax_g") || session.columns.includes("ADU_ax_g");
  if (!hasAccel) {
    return <section className="panel empty-panel">가속도 컬럼이 없어 G-G 다이어그램을 표시할 수 없습니다.</section>;
  }

  const points = session.samples.map((sample) => toPoint(getAccel(sample, "ax_g", "ADU_ax_g"), getAccel(sample, "ay_g", "ADU_ay_g")));
  const current = toPoint(getAccel(currentSample, "ax_g", "ADU_ax_g"), getAccel(currentSample, "ay_g", "ADU_ay_g"));

  return (
    <section className="panel gg-panel">
      <div className="section-heading">
        <h3>G-G 다이어그램</h3>
        <span>현재 점 강조</span>
      </div>
      <svg viewBox="0 0 300 300" aria-label="G-G 다이어그램">
        <circle cx="150" cy="150" r="65" className="gg-ring" />
        <circle cx="150" cy="150" r="130" className="gg-ring" />
        <line x1="0" x2="300" y1="150" y2="150" className="chart-grid" />
        <line x1="150" x2="150" y1="0" y2="300" className="chart-grid" />
        {points.map((point, index) => <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r="2" fill="rgba(56,189,248,.35)" />)}
        <circle cx={current.x} cy={current.y} r="8" fill="#facc15" />
      </svg>
    </section>
  );
}
```

- [ ] **Step 3: Wire panels into container**

Modify `LogReplayTab.tsx` imports:

```ts
import { GGDiagram } from "./GGDiagram";
import { GpsTrackPanel } from "./GpsTrackPanel";
```

Add after `SensorOverlayChart`:

```tsx
          <div className="log-visual-grid">
            <GpsTrackPanel session={session} currentSample={currentSample} />
            <GGDiagram session={session} currentSample={currentSample} />
          </div>
```

- [ ] **Step 4: Run build**

Run:

```bash
npm.cmd run build
```

Expected: PASS.

---

### Task 8: App Tab Integration and Styling

**Files:**
- Modify: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\App.tsx`
- Modify: `C:\Users\hacki\Desktop\03_workspace\MF-26_repo\Elec_app\src\styles.css`

- [ ] **Step 1: Add LogReplayTab to App**

Modify `src/App.tsx` imports:

```ts
import { LogReplayTab } from "./ui/logReplay/LogReplayTab";
```

Add a new navigation item where the existing app tab/navigation list is defined:

```tsx
{ id: "logReplay", label: "로그 재생" }
```

Add render branch:

```tsx
{activeView === "logReplay" ? <LogReplayTab /> : null}
```

If `App.tsx` uses a different active view variable name, follow the existing pattern exactly and only add the new `로그 재생` tab.

- [ ] **Step 2: Add log replay styles**

Append to `src/styles.css`:

```css
.log-replay {
  display: grid;
  gap: 16px;
}

.log-replay-workspace {
  display: grid;
  gap: 16px;
}

.log-summary-grid,
.sensor-card-grid,
.log-visual-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.sensor-picker-row,
.playback-controls,
.overlay-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.sensor-card {
  min-height: 96px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface);
  display: grid;
  gap: 6px;
}

.sensor-card strong {
  font-size: 1.8rem;
  line-height: 1;
}

.chip.selected {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.playback-range {
  width: 100%;
}

.overlay-chart,
.event-strip {
  position: relative;
  min-height: 220px;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}

.overlay-chart svg,
.gps-panel svg,
.gg-panel svg {
  width: 100%;
  height: 100%;
  display: block;
}

.playhead-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.72);
  pointer-events: none;
}

.chart-grid,
.gg-ring {
  stroke: var(--border);
  fill: none;
}

.event-strip {
  min-height: 76px;
}

.event-marker {
  position: absolute;
  top: 20px;
  transform: translateX(-50%);
  font-size: 0.75rem;
}

.event-marker.danger {
  border-color: #ef4444;
}

.event-marker.warning {
  border-color: #f59e0b;
}

.event-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
```

If existing CSS variables use different names, replace `var(--border)`, `var(--surface)`, `var(--accent)`, `var(--accent-muted)` with the closest existing variables.

- [ ] **Step 3: Run full verification**

Run:

```bash
npm.cmd test
npm.cmd run build
```

Expected: all tests pass and production build succeeds.

- [ ] **Step 4: Manual browser verification**

Start or reuse the dev server:

```bash
npm.cmd run dev -- --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

Verify:

- `로그 재생` tab is visible.
- Uploading a small EMU CSV shows summary.
- Sensor cards update when scrubber moves.
- Overlay graph shows up to 4 selected sensors.
- Playhead line moves with the scrubber.
- Event strip markers seek correctly.
- GPS panel shows a disabled state when GPS columns are missing.
- G-G panel shows a disabled state when accel columns are missing.

---

## Self-Review

- Spec coverage: This plan covers CSV upload, session summary, sensor cards, 4-sensor overlay, playhead, playback controls, GPS, G-G, and event strip.
- Placeholder scan: No `TBD`, `TODO`, or vague "implement later" steps are included.
- Type consistency: Domain types are defined first and reused by parser, analysis, and UI tasks.
- Scope check: Advanced lap detection, live Socket.IO replay, multi-log comparison, and scatter plot analysis remain outside MVP as specified.
