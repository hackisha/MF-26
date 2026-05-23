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
