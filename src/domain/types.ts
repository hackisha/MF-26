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
