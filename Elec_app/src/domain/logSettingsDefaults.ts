import type { SensorDefinition } from "./logReplayTypes";
import type { LogReplaySettings, SensorConfig, SensorGroup } from "./logSettingsTypes";

const COLORS = ["#ffc300", "#4cc9f0", "#f72585", "#22c55e", "#a78bfa", "#fb7185", "#f97316", "#38bdf8"];

function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function groupForKey(key: string): SensorGroup {
  const lower = key.toLowerCase();
  const normalized = normalizeKey(key);
  if (lower.includes("latitude") || lower.includes("longitude") || lower.includes("gps")) return "gps";
  if (lower.includes("adxl") || normalized === "axg" || normalized === "ayg" || normalized === "azg") return "linear-accel";
  if (lower.startsWith("adu_") || lower.startsWith("adu") || normalized.startsWith("adux")) return "angular";
  if (lower.includes("batt") || lower.includes("volt") || lower.includes("cel")) return "electric";
  if (lower.includes("rpm") || lower.includes("oil") || lower.includes("fuel") || lower.includes("clt") || lower.includes("tps")) {
    return "engine";
  }
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
      precision: sensor.type === "state" ? 0 : 2,
      color: COLORS[index % COLORS.length],
      showInDashboard: Boolean(sensor.recommendedCard),
      showInOverlay: Boolean(sensor.recommendedOverlay),
      showInSensorTable: true,
    }));
}

function firstAvailable(keys: string[], fallback: string): string {
  return keys.find(Boolean) ?? fallback;
}

export function createDefaultLogReplaySettings(sensors: SensorDefinition[] = []): LogReplaySettings {
  const keys = new Set(sensors.map((sensor) => sensor.key));
  const pick = (candidates: string[], fallback: string) => firstAvailable(candidates.filter((key) => keys.has(key)), fallback);

  return {
    version: 1,
    sensors: inferSensorConfigs(sensors),
    derivedSensors: [],
    eventRules: [
      {
        id: "low-oil-pressure",
        label: "오일 압력 낮음",
        expression: "OilPressure_bar < 1",
        severity: "danger",
        enabled: true,
      },
      {
        id: "low-battery",
        label: "배터리 전압 낮음",
        expression: "Batt_V < 11.5",
        severity: "warning",
        enabled: true,
      },
      {
        id: "high-coolant",
        label: "수온 높음",
        expression: "CLT_C >= 105",
        severity: "warning",
        enabled: true,
      },
    ],
    graphPresets: [
      { id: "engine", label: "엔진", sensorIds: ["RPM", "TPS_percent", "CLT_C", "OilPressure_bar"] },
      { id: "accel", label: "가속도", sensorIds: ["ax_g", "ay_g", "az_g"] },
    ],
    gps: {
      latitudeKey: "Latitude",
      longitudeKey: "Longitude",
      speedKey: "GPS_Speed_KPH",
      jumpThresholdMeters: 120,
      smoothing: "light",
    },
    accel: {
      linear: {
        xKey: pick(["ax_g", "ADXL_ax_g"], "ax_g"),
        yKey: pick(["ay_g", "ADXL_ay_g"], "ay_g"),
        zKey: pick(["az_g", "ADXL_az_g"], "az_g"),
        unit: "g",
        swapXY: false,
        invertX: false,
        invertY: false,
        invertZ: false,
        lowPassAlpha: 0.25,
      },
      angular: {
        xKey: pick(["adu_x", "ADU_x", "ADU_ax_g"], "adu_x"),
        yKey: pick(["adu_y", "ADU_y", "ADU_ay_g"], "adu_y"),
        zKey: pick(["adu_z", "ADU_z", "ADU_az_g"], "adu_z"),
        unit: "degps",
        scale: 1,
        offset: 0,
      },
    },
    matlab: {
      variablePrefix: "muzil",
      sanitizeVariableNames: true,
    },
  };
}
