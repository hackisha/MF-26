import type { SensorDefinition } from "./logReplayTypes";

export const EMU_SENSOR_DEFINITIONS = {
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
} as const satisfies Record<string, Omit<SensorDefinition, "key">>;

export type EmuSensorKey = keyof typeof EMU_SENSOR_DEFINITIONS;

export const DEFAULT_CARD_KEYS: readonly EmuSensorKey[] = [
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

export const DEFAULT_OVERLAY_KEYS: readonly EmuSensorKey[] = ["RPM", "TPS_percent", "VSS_kmh", "CLT_C"];

export const EVENT_THRESHOLDS = {
  lowBatteryV: 11.5,
  highCoolantC: 105,
  highOilTempC: 125,
  lowOilPressureBar: 1.0,
  lowFuelPressureBar: 2.5,
};
