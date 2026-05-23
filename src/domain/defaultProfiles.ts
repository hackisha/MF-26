import type { OverlayPreset, SensorChannel, ThresholdRule, VehicleProfile } from "./types";

const channel = (
  id: string,
  displayName: string,
  sourceColumns: string[],
  unit: string,
  group: SensorChannel["group"],
  color: string,
  defaultVisible = true,
  validRange?: SensorChannel["validRange"],
  calibration: SensorChannel["calibration"] = { type: "identity" }
): SensorChannel => ({
  id,
  displayName,
  sourceColumns,
  unit,
  group,
  calibration,
  validRange,
  defaultVisible,
  color
});

const baseChannels: Record<string, SensorChannel> = {
  Timestamp: channel("Timestamp", "Timestamp", ["Timestamp", "Time", "Time_s"], "s", "Diagnostics", "#64748b"),
  GPS_Speed_KPH: channel("GPS_Speed_KPH", "GPS Speed", ["GPS_Speed_KPH", "GPSSpeed_KPH"], "km/h", "GPS", "#2563eb"),
  VSS_KPH: channel("VSS_KPH", "Vehicle Speed", ["VSS_KPH", "VSS", "Speed_KPH"], "km/h", "GPS", "#0f766e"),
  Satellites: channel("Satellites", "Satellites", ["Satellites", "GPS_Satellites"], "count", "GPS", "#0891b2", false),
  RPM: channel("RPM", "Engine RPM", ["RPM", "EngineSpeed_RPM"], "rpm", "Engine", "#dc2626", true, { min: 0, max: 12000 }),
  TPS_percent: channel("TPS_percent", "Throttle Position", ["TPS_percent", "TPS", "TPS_%"], "%", "DriverInput", "#ea580c"),
  MAP_kPa: channel("MAP_kPa", "Manifold Pressure", ["MAP_kPa", "MAP"], "kPa", "Engine", "#9333ea"),
  EOT_IN: channel("EOT_IN", "Engine Oil Temp In", ["EOT_IN", "OilTemp_C"], "degC", "CoolingOil", "#f59e0b"),
  EOT_OUT: channel("EOT_OUT", "Engine Oil Temp Out", ["EOT_OUT"], "degC", "CoolingOil", "#d97706"),
  OilPressure_bar: channel("OilPressure_bar", "Oil Pressure", ["OilPressure_bar"], "bar", "CoolingOil", "#16a34a"),
  FuelPressure_bar: channel("FuelPressure_bar", "Fuel Pressure", ["FuelPressure_bar"], "bar", "Fuel", "#22c55e"),
  CLT_C: channel("CLT_C", "Coolant Temperature", ["CLT_C"], "degC", "CoolingOil", "#0ea5e9"),
  WBO_Lambda: channel("WBO_Lambda", "Wideband Lambda", ["WBO_Lambda"], "lambda", "Fuel", "#84cc16"),
  EGT1_C: channel("EGT1_C", "Exhaust Gas Temp 1", ["EGT1_C"], "degC", "Engine", "#ef4444"),
  EGT2_C: channel("EGT2_C", "Exhaust Gas Temp 2", ["EGT2_C"], "degC", "Engine", "#f97316"),
  Batt_V: channel("Batt_V", "Battery Voltage", ["Batt_V", "Battery_V"], "V", "Electrical", "#eab308"),
  ax_raw: channel("ax_raw", "Raw Accel X", ["ax_raw", "AccelX_raw"], "count", "IMU", "#475569", false),
  ay_raw: channel("ay_raw", "Raw Accel Y", ["ay_raw", "AccelY_raw"], "count", "IMU", "#64748b", false),
  az_raw: channel("az_raw", "Raw Accel Z", ["az_raw", "AccelZ_raw"], "count", "IMU", "#94a3b8", false),
  ax_corrected_g: channel("ax_corrected_g", "Corrected Accel X", ["ax_corrected_g", "ax_raw"], "g", "IMU", "#7c3aed", true, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  ay_corrected_g: channel("ay_corrected_g", "Corrected Accel Y", ["ay_corrected_g", "ay_raw"], "g", "IMU", "#db2777", true, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  az_corrected_g: channel("az_corrected_g", "Corrected Accel Z", ["az_corrected_g", "az_raw"], "g", "IMU", "#4f46e5", false, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  gx_dps: channel("gx_dps", "Gyro X", ["gx_dps", "GyroX_dps"], "deg/s", "IMU", "#0369a1", false),
  gy_dps: channel("gy_dps", "Gyro Y", ["gy_dps", "GyroY_dps"], "deg/s", "IMU", "#0284c7", false),
  gz_dps: channel("gz_dps", "Gyro Z", ["gz_dps", "GyroZ_dps"], "deg/s", "IMU", "#38bdf8", false)
};

const profile2026Channels: Record<string, SensorChannel> = {
  ...baseChannels,
  Susp_FL_mm: channel("Susp_FL_mm", "Suspension Front Left", ["Susp_FL_mm"], "mm", "Suspension", "#0d9488"),
  Susp_FR_mm: channel("Susp_FR_mm", "Suspension Front Right", ["Susp_FR_mm"], "mm", "Suspension", "#14b8a6"),
  Susp_RL_mm: channel("Susp_RL_mm", "Suspension Rear Left", ["Susp_RL_mm"], "mm", "Suspension", "#2dd4bf"),
  Susp_RR_mm: channel("Susp_RR_mm", "Suspension Rear Right", ["Susp_RR_mm"], "mm", "Suspension", "#5eead4"),
  Pitot_dP_Pa: channel("Pitot_dP_Pa", "Pitot Delta Pressure", ["Pitot_dP_Pa"], "Pa", "Aero", "#4338ca"),
  Pitot_AirSpeed_KPH: channel("Pitot_AirSpeed_KPH", "Pitot Air Speed", ["Pitot_AirSpeed_KPH"], "km/h", "Aero", "#6366f1"),
  SteeringAngle_deg: channel("SteeringAngle_deg", "Steering Angle", ["SteeringAngle_deg"], "deg", "DriverInput", "#be123c")
};

const defaultRules: ThresholdRule[] = [
  {
    id: "high-rpm-low-oil-pressure",
    name: "High RPM Low Oil Pressure",
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
    description: "Battery voltage is below the expected operating range.",
    views: ["summary", "diagnostics", "graph", "report"]
  },
  {
    id: "high-lateral-g",
    name: "High Lateral G",
    severity: "info",
    all: [{ channelId: "ay_corrected_g", op: ">", value: 1.1 }],
    minDurationSec: 0.2,
    description: "Lateral acceleration exceeded the default behavior threshold.",
    views: ["behavior", "graph", "map", "report"]
  }
];

const baseOverlays: OverlayPreset[] = [
  {
    id: "cooling",
    name: "Cooling",
    channelIds: ["EOT_IN", "EOT_OUT", "CLT_C"],
    mode: "separateAxes"
  },
  {
    id: "oil-stability",
    name: "Oil Stability",
    channelIds: ["RPM", "OilPressure_bar", "EOT_IN"],
    mode: "separateAxes"
  },
  {
    id: "driver-input-vs-response",
    name: "Driver Input vs Response",
    channelIds: ["TPS_percent", "ay_corrected_g"],
    mode: "normalized"
  }
];

const defaultReportSections = ["summary", "diagnostics", "graphs", "events"];

export const defaultProfiles: VehicleProfile[] = [
  {
    id: "2025-vehicle",
    name: "2025 Vehicle",
    revision: "2025.1",
    channels: baseChannels,
    rules: defaultRules,
    overlays: baseOverlays,
    reportSections: defaultReportSections
  },
  {
    id: "2026-vehicle",
    name: "2026 Vehicle",
    revision: "2026.1",
    channels: profile2026Channels,
    rules: defaultRules,
    overlays: [
      ...baseOverlays,
      {
        id: "suspension-balance",
        name: "Suspension Balance",
        channelIds: ["Susp_FL_mm", "Susp_FR_mm", "Susp_RL_mm", "Susp_RR_mm"],
        mode: "separateAxes"
      }
    ],
    reportSections: defaultReportSections
  }
];
