import type { Component, ComponentRole } from "./types";

export interface ClassificationInput {
  packageName: string;
  symbolName: string;
  rawName: string;
  pinCount: number;
}

export interface ClassificationResult {
  role: ComponentRole;
  confidence: number;
  reason: string;
}

export interface ClassificationQueueItem {
  componentId: string;
  suggestedRole: ComponentRole;
  confidence: number;
  reason: string;
}

export function classifyComponent(input: ClassificationInput): ClassificationResult {
  const haystack = `${input.packageName} ${input.symbolName} ${input.rawName}`.toUpperCase();

  if (haystack.includes("EMU_")) {
    return { role: "ecu", confidence: 0.9, reason: "EMU 이름 패턴" };
  }

  if (haystack.includes("MOLEX")) {
    return { role: "connector", confidence: 0.82, reason: "MOLEX 커넥터 이름 패턴" };
  }

  if (haystack.includes("HDR-")) {
    const confidence = input.rawName && !haystack.includes("HDR-F") ? 0.65 : 0.55;
    return { role: "connector", confidence, reason: "HDR 헤더 이름 패턴" };
  }

  if (haystack.includes("RELAY")) {
    return { role: "actuator", confidence: 0.62, reason: "relay 이름 패턴" };
  }

  if (haystack.includes("VCC") || haystack.includes("+12V") || haystack.includes("GND")) {
    return { role: "power", confidence: 0.7, reason: "전원 관련 이름 패턴" };
  }

  return { role: "unknown", confidence: 0.2, reason: "강한 자동 분류 규칙 없음" };
}

export function createClassificationQueue(
  components: Component[],
  threshold = 0.7
): ClassificationQueueItem[] {
  return components
    .filter((component) => !component.confirmedRole && component.autoConfidence < threshold)
    .map((component) => ({
      componentId: component.id,
      suggestedRole: component.autoRole,
      confidence: component.autoConfidence,
      reason: `자동 분류 confidence ${component.autoConfidence.toFixed(2)}`
    }));
}
