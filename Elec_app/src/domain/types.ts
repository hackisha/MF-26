export type ComponentRole =
  | "ecu"
  | "connector"
  | "sensor"
  | "actuator"
  | "power"
  | "other"
  | "unknown";

export type MeasurementStatus = "pass" | "fail" | "unknown";

export interface SourceSchematic {
  fileName: string;
  title: string;
  editorVersion: string;
  uploadedAt: string;
  hash: string;
  shapeCounts: Record<string, number>;
}

export interface Pin {
  id: string;
  componentId: string;
  number: string;
  label: string | null;
  x: number;
  y: number;
  raw: string;
}

export interface Component {
  id: string;
  sourceId: string;
  rawName: string;
  packageName: string;
  symbolName: string;
  alias: string;
  x: number;
  y: number;
  pins: Pin[];
  autoRole: ComponentRole;
  autoConfidence: number;
  confirmedRole: ComponentRole | null;
  raw: string;
}

export interface WireSegment {
  id: string;
  points: Array<{ x: number; y: number }>;
  raw: string;
}

export interface Junction {
  id: string;
  x: number;
  y: number;
  raw: string;
}

export interface NetLabel {
  id: string;
  x: number;
  y: number;
  label: string;
  raw: string;
}

export interface GraphNode {
  id: string;
  kind: "pin" | "wire-point" | "junction" | "label";
  x: number;
  y: number;
  label: string | null;
  refId: string | null;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  kind: "wire" | "pin-contact" | "label-contact";
  confidence: number;
}

export interface NetGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ParsedSchematic {
  source: SourceSchematic;
  components: Component[];
  wires: WireSegment[];
  junctions: Junction[];
  labels: NetLabel[];
  warnings: string[];
}

export interface UserClassification {
  componentId: string;
  role: ComponentRole;
  alias: string;
  confirmedAt: string;
}

export interface Note {
  id: string;
  targetType: "component" | "pin" | "regulation";
  targetId: string;
  body: string;
  updatedAt: string;
}

export interface Measurement {
  id: string;
  pinId: string;
  expectedValue: string;
  condition: string;
  measuredValue: string;
  status: MeasurementStatus;
  measuredAt: string;
  note: string;
}

export interface Attachment {
  id: string;
  targetType: "component" | "wiring-diagram" | "regulation";
  targetId: string | null;
  label: string;
  kind: "link" | "file";
  url: string | null;
  blobKey: string | null;
  mimeType: string | null;
}

export interface ElecProject {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  source: SourceSchematic | null;
  components: Component[];
  graph: NetGraph;
  classifications: Record<string, UserClassification>;
  notes: Note[];
  measurements: Measurement[];
  attachments: Attachment[];
}
