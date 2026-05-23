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
