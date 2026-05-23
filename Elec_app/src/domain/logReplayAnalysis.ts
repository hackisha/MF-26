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
  if (current.length >= 4) return current.slice(0, 4);
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

function isValidGps(sample: LogSample): boolean {
  return numeric(sample.values.Latitude) !== undefined && numeric(sample.values.Longitude) !== undefined;
}

export function extractLogEvents(session: LogSession): LogEvent[] {
  const events: LogEvent[] = [];
  const activeTypes = new Set<string>();
  let previousSample: LogSample | undefined;
  let lastValidGpsSample: LogSample | undefined;

  function addEpisode(sample: LogSample, active: boolean, event: Omit<LogEvent, "id" | "timeMs">) {
    if (active && !activeTypes.has(event.type)) {
      activeTypes.add(event.type);
      addEvent(events, { ...event, timeMs: sample.timeMs });
    } else if (!active) {
      activeTypes.delete(event.type);
    }
  }

  session.samples.forEach((sample) => {
    const cel = numeric(sample.values.CEL_Error);
    addEpisode(
      sample,
      cel !== undefined && cel !== 0,
      {
        type: "cel",
        severity: "danger",
        label: "CEL",
        description: `CEL_Error가 ${cel ?? "-"}입니다.`,
        sensorKey: "CEL_Error",
        value: cel ?? null,
      },
    );

    const batt = numeric(sample.values.Batt_V);
    addEpisode(
      sample,
      batt !== undefined && batt < EVENT_THRESHOLDS.lowBatteryV,
      {
        type: "low-battery",
        severity: "warning",
        label: "Batt low",
        description: `배터리 전압이 ${batt?.toFixed(1) ?? "-"}V로 낮습니다.`,
        sensorKey: "Batt_V",
        value: batt ?? null,
      },
    );

    const coolant = numeric(sample.values.CLT_C);
    addEpisode(
      sample,
      coolant !== undefined && coolant >= EVENT_THRESHOLDS.highCoolantC,
      {
        type: "high-coolant",
        severity: "warning",
        label: "CLT high",
        description: `수온이 ${coolant?.toFixed(1) ?? "-"}C입니다.`,
        sensorKey: "CLT_C",
        value: coolant ?? null,
      },
    );

    const oilTemp = numeric(sample.values.OilTemp_C);
    addEpisode(
      sample,
      oilTemp !== undefined && oilTemp >= EVENT_THRESHOLDS.highOilTempC,
      {
        type: "high-oil-temp",
        severity: "warning",
        label: "Oil T high",
        description: `유온이 ${oilTemp?.toFixed(1) ?? "-"}C입니다.`,
        sensorKey: "OilTemp_C",
        value: oilTemp ?? null,
      },
    );

    const oilPressure = numeric(sample.values.OilPressure_bar);
    addEpisode(
      sample,
      oilPressure !== undefined && oilPressure < EVENT_THRESHOLDS.lowOilPressureBar,
      {
        type: "low-oil-pressure",
        severity: "danger",
        label: "Oil P low",
        description: `유압이 ${oilPressure?.toFixed(1) ?? "-"}bar로 낮습니다.`,
        sensorKey: "OilPressure_bar",
        value: oilPressure ?? null,
      },
    );

    const fuelPressure = numeric(sample.values.FuelPressure_bar);
    addEpisode(
      sample,
      fuelPressure !== undefined && fuelPressure < EVENT_THRESHOLDS.lowFuelPressureBar,
      {
        type: "low-fuel-pressure",
        severity: "warning",
        label: "Fuel P low",
        description: `연압이 ${fuelPressure?.toFixed(1) ?? "-"}bar로 낮습니다.`,
        sensorKey: "FuelPressure_bar",
        value: fuelPressure ?? null,
      },
    );

    const rpm = numeric(sample.values.RPM);
    const previousRpm = previousSample ? numeric(previousSample.values.RPM) : undefined;
    addEpisode(
      sample,
      rpm === 0 && previousRpm !== undefined && previousRpm > 500,
      {
        type: "rpm-zero",
        severity: "warning",
        label: "RPM zero",
        description: `RPM이 ${previousRpm?.toFixed(0) ?? "-"}에서 0으로 떨어졌습니다.`,
        sensorKey: "RPM",
        value: rpm ?? null,
      },
    );
    addEpisode(
      sample,
      rpm !== undefined && previousRpm !== undefined && Math.abs(rpm - previousRpm) >= 3000,
      {
        type: "rpm-jump",
        severity: "info",
        label: "RPM jump",
        description: `RPM 변화량이 ${
          rpm !== undefined && previousRpm !== undefined ? Math.abs(rpm - previousRpm).toFixed(0) : "-"
        }입니다.`,
        sensorKey: "RPM",
        value: rpm,
      },
    );

    if (previousSample) {
      const previousGpsValid = isValidGps(previousSample);
      const currentGpsValid = isValidGps(sample);
      addEpisode(sample, previousGpsValid && !currentGpsValid, {
        type: "gps-gap",
        severity: "warning",
        label: "GPS gap",
        description: "GPS 좌표가 끊겼습니다.",
        sensorKey: "Latitude",
        value: null,
      });

      const previousLat = lastValidGpsSample ? numeric(lastValidGpsSample.values.Latitude) : undefined;
      const previousLon = lastValidGpsSample ? numeric(lastValidGpsSample.values.Longitude) : undefined;
      const lat = numeric(sample.values.Latitude);
      const lon = numeric(sample.values.Longitude);
      const jumped =
        previousLat !== undefined &&
        previousLon !== undefined &&
        lat !== undefined &&
        lon !== undefined &&
        (Math.abs(lat - previousLat) > 0.01 || Math.abs(lon - previousLon) > 0.01);
      addEpisode(sample, jumped, {
        type: "gps-jump",
        severity: "warning",
        label: "GPS jump",
        description: "GPS 좌표가 비정상적으로 크게 이동했습니다.",
        sensorKey: "Latitude",
        value: lat ?? null,
      });
    }

    if (isValidGps(sample)) lastValidGpsSample = sample;
    previousSample = sample;
  });

  return events;
}
