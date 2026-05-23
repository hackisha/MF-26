import { classifyComponent } from "./classification";
import type {
  Component,
  Junction,
  NetLabel,
  ParsedSchematic,
  Pin,
  SourceSchematic,
  WireSegment
} from "./types";

interface ParseInput {
  fileName: string;
  text: string;
  uploadedAt: string;
  hash: string;
}

interface EasyEdaSheet {
  dataStr?: {
    shape?: string[];
  };
}

function getShapeType(shape: string): string {
  return shape.split("~", 1)[0] || "UNKNOWN";
}

function readBacktickProperty(raw: string, key: string): string {
  const marker = `${key}\``;
  const start = raw.indexOf(marker);
  if (start < 0) return "";
  const valueStart = start + marker.length;
  const valueEnd = raw.indexOf("`", valueStart);
  if (valueEnd < 0) return raw.slice(valueStart);
  return raw.slice(valueStart, valueEnd);
}

function toNumber(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function stableId(prefix: string, raw: string): string {
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash * 31 + raw.charCodeAt(i)) >>> 0;
  }
  return `${prefix}-${hash.toString(16)}`;
}

function parseWire(shape: string): WireSegment {
  const fields = shape.split("~");
  const coordinateTokens = (fields[1] ?? "")
    .trim()
    .split(/\s+/)
    .map(Number)
    .filter(Number.isFinite);

  const points = [];
  for (let i = 0; i < coordinateTokens.length - 1; i += 2) {
    points.push({ x: coordinateTokens[i], y: coordinateTokens[i + 1] });
  }

  return {
    id: fields[6] || stableId("wire", shape),
    points,
    raw: shape
  };
}

function parseJunction(shape: string): Junction {
  const fields = shape.split("~");
  return {
    id: fields[5] || stableId("junction", shape),
    x: toNumber(fields[1]),
    y: toNumber(fields[2]),
    raw: shape
  };
}

function parseNetLabel(shape: string): NetLabel | null {
  const fields = shape.split("~");
  const payload = shape.split("^^");
  const label = payload[2]?.split("~")[0];
  if (!label) return null;

  return {
    id: fields[4] || stableId("label", shape),
    x: toNumber(fields[2]),
    y: toNumber(fields[3]),
    label,
    raw: shape
  };
}

function parsePin(componentId: string, segment: string): Pin | null {
  const fields = segment.split("~");
  if (fields[0] !== "P") return null;

  const number = fields[3] || "?";
  const pinId = fields[7] || `${componentId}-pin-${number}`;
  const labelParts = segment.split("^^");
  const maybeLabel = labelParts[3]?.split("~")[3] ?? null;

  return {
    id: pinId,
    componentId,
    number,
    label: maybeLabel && maybeLabel !== number ? maybeLabel : null,
    x: toNumber(fields[4]),
    y: toNumber(fields[5]),
    raw: segment
  };
}

function parseComponent(shape: string): Component {
  const segments = shape.split("#@$");
  const header = segments[0];
  const fields = header.split("~");
  const sourceId = fields[7] || fields[6] || stableId("component", header);
  const packageName = readBacktickProperty(header, "package");
  const symbolName = readBacktickProperty(header, "spiceSymbolName");
  const textNames = segments
    .filter((segment) => segment.startsWith("T~"))
    .map((segment) => segment.split("~")[10])
    .filter(Boolean);
  const rawName = textNames[0] || symbolName || packageName || sourceId;
  const pins = segments
    .map((segment) => parsePin(sourceId, segment))
    .filter((pin): pin is Pin => Boolean(pin));
  const auto = classifyComponent({ packageName, symbolName, rawName, pinCount: pins.length });

  return {
    id: sourceId,
    sourceId,
    rawName,
    packageName,
    symbolName,
    alias: rawName,
    x: toNumber(fields[1]),
    y: toNumber(fields[2]),
    pins,
    autoRole: auto.role,
    autoConfidence: auto.confidence,
    confirmedRole: null,
    raw: shape
  };
}

export async function parseEasyEdaSchematic(input: ParseInput): Promise<ParsedSchematic> {
  const json = JSON.parse(input.text) as {
    title?: string;
    editorVersion?: string;
    schematics?: EasyEdaSheet[];
  };
  const shapes = json.schematics?.flatMap((sheet) => sheet.dataStr?.shape ?? []);

  if (!Array.isArray(shapes)) {
    throw new Error("지원하지 않는 EasyEDA 구조: schematics[].dataStr.shape[]가 없습니다.");
  }

  const source: SourceSchematic = {
    fileName: input.fileName,
    title: json.title ?? "",
    editorVersion: json.editorVersion ?? "",
    uploadedAt: input.uploadedAt,
    hash: input.hash,
    shapeCounts: {}
  };
  const components: Component[] = [];
  const wires: WireSegment[] = [];
  const junctions: Junction[] = [];
  const labels: NetLabel[] = [];
  const warnings: string[] = [];

  for (const shape of shapes) {
    const type = getShapeType(shape);
    source.shapeCounts[type] = (source.shapeCounts[type] ?? 0) + 1;

    try {
      if (type === "LIB") components.push(parseComponent(shape));
      else if (type === "W") wires.push(parseWire(shape));
      else if (type === "J") junctions.push(parseJunction(shape));
      else if (type === "F") {
        const label = parseNetLabel(shape);
        if (label) labels.push(label);
      } else if (!["R", "T", "N", "E", "PL", "O"].includes(type)) {
        warnings.push(`Unsupported shape type: ${type}`);
      }
    } catch (cause) {
      warnings.push(`Failed to parse ${type}: ${cause instanceof Error ? cause.message : String(cause)}`);
    }
  }

  return { source, components, wires, junctions, labels, warnings };
}
