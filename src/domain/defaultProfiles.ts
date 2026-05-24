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

const createBaseChannels = (): Record<string, SensorChannel> => ({
  Timestamp: channel("Timestamp", "Timestamp", ["Timestamp", "Time", "Time_s"], "s", "Diagnostics", "#64748b"),
  GPS_Speed_KPH: channel("GPS_Speed_KPH", "GPS Speed", ["GPS_Speed_KPH", "GPSSpeed_KPH"], "km/h", "GPS", "#2563eb"),
  VSS_kmh: channel("VSS_kmh", "Vehicle Speed", ["VSS_kmh"], "km/h", "GPS", "#0f766e"),
  Latitude: channel("Latitude", "Latitude", ["Latitude"], "deg", "GPS", "#0284c7", false),
  Longitude: channel("Longitude", "Longitude", ["Longitude"], "deg", "GPS", "#0369a1", false),
  Satellites: channel("Satellites", "Satellites", ["Satellites", "GPS_Satellites"], "count", "GPS", "#0891b2", false),
  Altitude_m: channel("Altitude_m", "Altitude", ["Altitude_m"], "m", "GPS", "#0e7490", false),
  Heading_deg: channel("Heading_deg", "Heading", ["Heading_deg"], "deg", "GPS", "#155e75", false),
  RPM: channel("RPM", "Engine RPM", ["RPM", "EngineSpeed_RPM"], "rpm", "Engine", "#dc2626", true, { min: 0, max: 12000 }),
  TPS_percent: channel("TPS_percent", "Throttle Position", ["TPS_percent", "TPS", "TPS_%"], "%", "DriverInput", "#ea580c"),
  IAT_C: channel("IAT_C", "Intake Air Temperature", ["IAT_C"], "degC", "Engine", "#fb7185", false),
  MAP_kPa: channel("MAP_kPa", "Manifold Pressure", ["MAP_kPa", "MAP"], "kPa", "Engine", "#9333ea"),
  PulseWidth_ms: channel("PulseWidth_ms", "Injector Pulse Width", ["PulseWidth_ms"], "ms", "Fuel", "#65a30d", false),
  AnalogIn1_V: channel("AnalogIn1_V", "Analog Input 1", ["AnalogIn1_V"], "V", "Diagnostics", "#64748b", false),
  AnalogIn2_V: channel("AnalogIn2_V", "Analog Input 2", ["AnalogIn2_V"], "V", "Diagnostics", "#6b7280", false),
  AnalogIn3_V: channel("AnalogIn3_V", "Analog Input 3", ["AnalogIn3_V"], "V", "Diagnostics", "#71717a", false),
  AnalogIn4_V: channel("AnalogIn4_V", "Analog Input 4", ["AnalogIn4_V"], "V", "Diagnostics", "#78716c", false),
  Baro_kPa: channel("Baro_kPa", "Barometric Pressure", ["Baro_kPa"], "kPa", "Engine", "#7e22ce", false),
  EOT_IN: channel("EOT_IN", "Engine Oil Temp In", ["EOT_IN", "OilTemp_C"], "degC", "CoolingOil", "#f59e0b"),
  EOT_OUT: channel("EOT_OUT", "Engine Oil Temp Out", ["EOT_OUT"], "degC", "CoolingOil", "#d97706"),
  OilPressure_bar: channel("OilPressure_bar", "Oil Pressure", ["OilPressure_bar"], "bar", "CoolingOil", "#16a34a"),
  FuelPressure_bar: channel("FuelPressure_bar", "Fuel Pressure", ["FuelPressure_bar"], "bar", "Fuel", "#22c55e"),
  CLT_C: channel("CLT_C", "Coolant Temperature", ["CLT_C"], "degC", "CoolingOil", "#0ea5e9"),
  fuelPumpTemp: channel("fuelPumpTemp", "Fuel Pump Temperature", ["fuelPumpTemp"], "degC", "Fuel", "#4ade80", false),
  IgnAngle_deg: channel("IgnAngle_deg", "Ignition Angle", ["IgnAngle_deg"], "deg", "Engine", "#e11d48", false),
  DwellTime_ms: channel("DwellTime_ms", "Dwell Time", ["DwellTime_ms"], "ms", "Engine", "#be123c", false),
  WBO_Lambda: channel("WBO_Lambda", "Wideband Lambda", ["WBO_Lambda"], "lambda", "Fuel", "#84cc16"),
  LambdaCorrection_percent: channel(
    "LambdaCorrection_percent",
    "Lambda Correction",
    ["LambdaCorrection_percent"],
    "%",
    "Fuel",
    "#a3e635",
    false
  ),
  EGT1_C: channel("EGT1_C", "Exhaust Gas Temp 1", ["EGT1_C"], "degC", "Engine", "#ef4444"),
  EGT2_C: channel("EGT2_C", "Exhaust Gas Temp 2", ["EGT2_C"], "degC", "Engine", "#f97316"),
  Gear: channel("Gear", "Gear", ["Gear"], "gear", "DriverInput", "#f97316", false),
  EmuTemp_C: channel("EmuTemp_C", "ECU Temperature", ["EmuTemp_C"], "degC", "Diagnostics", "#a1a1aa", false),
  Batt_V: channel("Batt_V", "Battery Voltage", ["Batt_V", "Battery_V"], "V", "Electrical", "#eab308"),
  CEL_Error: channel("CEL_Error", "CEL Error", ["CEL_Error"], "flag", "Diagnostics", "#dc2626", false),
  Flags1: channel("Flags1", "Flags 1", ["Flags1"], "flags", "Diagnostics", "#52525b", false),
  Ethanol_percent: channel("Ethanol_percent", "Ethanol Content", ["Ethanol_percent"], "%", "Fuel", "#bef264", false),
  DBW_Pos_percent: channel("DBW_Pos_percent", "DBW Position", ["DBW_Pos_percent"], "%", "DriverInput", "#f59e0b", false),
  DBW_Target_percent: channel(
    "DBW_Target_percent",
    "DBW Target",
    ["DBW_Target_percent"],
    "%",
    "DriverInput",
    "#fbbf24",
    false
  ),
  TC_drpm_raw: channel("TC_drpm_raw", "Traction Control Delta RPM Raw", ["TC_drpm_raw"], "rpm", "Engine", "#c084fc", false),
  TC_drpm: channel("TC_drpm", "Traction Control Delta RPM", ["TC_drpm"], "rpm", "Engine", "#a855f7", false),
  TC_TorqueReduction_percent: channel(
    "TC_TorqueReduction_percent",
    "TC Torque Reduction",
    ["TC_TorqueReduction_percent"],
    "%",
    "Engine",
    "#9333ea",
    false
  ),
  PitLimit_TorqueReduction_percent: channel(
    "PitLimit_TorqueReduction_percent",
    "Pit Limit Torque Reduction",
    ["PitLimit_TorqueReduction_percent"],
    "%",
    "Engine",
    "#7e22ce",
    false
  ),
  AnalogIn5_V: channel("AnalogIn5_V", "Analog Input 5", ["AnalogIn5_V"], "V", "Diagnostics", "#57534e", false),
  AnalogIn6_V: channel("AnalogIn6_V", "Analog Input 6", ["AnalogIn6_V"], "V", "Diagnostics", "#44403c", false),
  OutFlags1: channel("OutFlags1", "Output Flags 1", ["OutFlags1"], "flags", "Diagnostics", "#475569", false),
  OutFlags2: channel("OutFlags2", "Output Flags 2", ["OutFlags2"], "flags", "Diagnostics", "#475569", false),
  OutFlags3: channel("OutFlags3", "Output Flags 3", ["OutFlags3"], "flags", "Diagnostics", "#475569", false),
  OutFlags4: channel("OutFlags4", "Output Flags 4", ["OutFlags4"], "flags", "Diagnostics", "#475569", false),
  BoostTarget_kPa: channel("BoostTarget_kPa", "Boost Target", ["BoostTarget_kPa"], "kPa", "Engine", "#6d28d9", false),
  PWM1_DC_percent: channel("PWM1_DC_percent", "PWM 1 Duty Cycle", ["PWM1_DC_percent"], "%", "Diagnostics", "#737373", false),
  DSG_Mode: channel("DSG_Mode", "DSG Mode", ["DSG_Mode"], "mode", "Diagnostics", "#525252", false),
  LambdaTarget: channel("LambdaTarget", "Lambda Target", ["LambdaTarget"], "lambda", "Fuel", "#bef264", false),
  PWM2_DC_percent: channel("PWM2_DC_percent", "PWM 2 Duty Cycle", ["PWM2_DC_percent"], "%", "Diagnostics", "#737373", false),
  FuelUsed_L: channel("FuelUsed_L", "Fuel Used", ["FuelUsed_L"], "L", "Fuel", "#15803d", false),
  ax_g: channel("ax_g", "Raw Accel X", ["ax_g"], "g", "IMU", "#475569", false),
  ay_g: channel("ay_g", "Raw Accel Y", ["ay_g"], "g", "IMU", "#64748b", false),
  az_g: channel("az_g", "Raw Accel Z", ["az_g"], "g", "IMU", "#94a3b8", false),
  ax_corrected_g: channel("ax_corrected_g", "Corrected Accel X", ["ax_g"], "g", "IMU", "#7c3aed", true, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  ay_corrected_g: channel("ay_corrected_g", "Corrected Accel Y", ["ay_g"], "g", "IMU", "#db2777", true, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  az_corrected_g: channel("az_corrected_g", "Corrected Accel Z", ["az_g"], "g", "IMU", "#4f46e5", false, undefined, {
    type: "scaleOffset",
    scale: 0.125,
    offset: 0
  }),
  gx_dps: channel("gx_dps", "Gyro X", ["gx_dps", "GyroX_dps"], "deg/s", "IMU", "#0369a1", false),
  gy_dps: channel("gy_dps", "Gyro Y", ["gy_dps", "GyroY_dps"], "deg/s", "IMU", "#0284c7", false),
  gz_dps: channel("gz_dps", "Gyro Z", ["gz_dps", "GyroZ_dps"], "deg/s", "IMU", "#38bdf8", false),
  ADU_ax_g: channel("ADU_ax_g", "ADU Accel X", ["ADU_ax_g"], "g", "IMU", "#0f766e", false),
  ADU_ay_g: channel("ADU_ay_g", "ADU Accel Y", ["ADU_ay_g"], "g", "IMU", "#0d9488", false),
  ADU_az_g: channel("ADU_az_g", "ADU Accel Z", ["ADU_az_g"], "g", "IMU", "#14b8a6", false)
});

const createProfile2026Channels = (): Record<string, SensorChannel> => ({
  ...createBaseChannels(),
  Susp_FL_mm: channel("Susp_FL_mm", "Suspension Front Left", ["Susp_FL_mm"], "mm", "Suspension", "#0d9488"),
  Susp_FR_mm: channel("Susp_FR_mm", "Suspension Front Right", ["Susp_FR_mm"], "mm", "Suspension", "#14b8a6"),
  Susp_RL_mm: channel("Susp_RL_mm", "Suspension Rear Left", ["Susp_RL_mm"], "mm", "Suspension", "#2dd4bf"),
  Susp_RR_mm: channel("Susp_RR_mm", "Suspension Rear Right", ["Susp_RR_mm"], "mm", "Suspension", "#5eead4"),
  Pitot_dP_Pa: channel("Pitot_dP_Pa", "Pitot Delta Pressure", ["Pitot_dP_Pa"], "Pa", "Aero", "#4338ca"),
  Pitot_AirSpeed_KPH: channel("Pitot_AirSpeed_KPH", "Pitot Air Speed", ["Pitot_AirSpeed_KPH"], "km/h", "Aero", "#6366f1"),
  SteeringAngle_deg: channel("SteeringAngle_deg", "Steering Angle", ["SteeringAngle_deg"], "deg", "DriverInput", "#be123c")
});

const createDefaultRules = (): ThresholdRule[] => [
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

const createBaseOverlays = (): OverlayPreset[] => [
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
    id: "gg-inputs",
    name: "Driver Input vs Response",
    channelIds: ["TPS_percent", "ay_corrected_g"],
    mode: "normalized"
  }
];

const reportSections2025 = ["summary", "diagnostics", "events", "overlays", "behavior", "segments"];
const reportSections2026 = ["summary", "diagnostics", "events", "overlays", "behavior", "map", "segments"];

const createDefaultProfiles = (): VehicleProfile[] => [
  {
    id: "2025-vehicle",
    name: "2025 Vehicle",
    revision: "2025.1",
    channels: createBaseChannels(),
    rules: createDefaultRules(),
    overlays: createBaseOverlays(),
    reportSections: [...reportSections2025]
  },
  {
    id: "2026-vehicle",
    name: "2026 Vehicle",
    revision: "2026.1",
    channels: createProfile2026Channels(),
    rules: createDefaultRules(),
    overlays: [
      ...createBaseOverlays(),
      {
        id: "suspension-balance",
        name: "Suspension Balance",
        channelIds: ["Susp_FL_mm", "Susp_FR_mm", "Susp_RL_mm", "Susp_RR_mm"],
        mode: "separateAxes"
      }
    ],
    reportSections: [...reportSections2026]
  }
];

export const defaultProfiles: VehicleProfile[] = createDefaultProfiles();
