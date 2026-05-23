import type { Component } from "./types";

export interface ComponentMatch {
  previousId: string;
  nextId: string;
  confidence: number;
  reason: string;
}

export interface UpdateMatchResult {
  matched: ComponentMatch[];
  added: Component[];
  removed: Component[];
  needsReview: ComponentMatch[];
}

function score(previous: Component, next: Component): ComponentMatch {
  if (previous.sourceId === next.sourceId) {
    return { previousId: previous.id, nextId: next.id, confidence: 1, reason: "EasyEDA sourceId 일치" };
  }

  let confidence = 0;
  const reasons: string[] = [];
  if (previous.symbolName && previous.symbolName === next.symbolName) {
    confidence += 0.35;
    reasons.push("symbolName 일치");
  }
  if (previous.packageName && previous.packageName === next.packageName) {
    confidence += 0.25;
    reasons.push("packageName 일치");
  }
  if (previous.pins.length === next.pins.length) {
    confidence += 0.2;
    reasons.push("핀 수 일치");
  }
  const distance = Math.hypot(previous.x - next.x, previous.y - next.y);
  if (distance <= 20) {
    confidence += 0.2;
    reasons.push("좌표 근접");
  }

  return {
    previousId: previous.id,
    nextId: next.id,
    confidence,
    reason: reasons.join(", ") || "약한 후보"
  };
}

export function matchUpdatedComponents(previous: Component[], next: Component[]): UpdateMatchResult {
  const usedPrevious = new Set<string>();
  const usedNext = new Set<string>();
  const matched: ComponentMatch[] = [];
  const needsReview: ComponentMatch[] = [];

  for (const nextComponent of next) {
    const candidates = previous
      .filter((previousComponent) => !usedPrevious.has(previousComponent.id))
      .map((previousComponent) => score(previousComponent, nextComponent))
      .sort((a, b) => b.confidence - a.confidence);
    const best = candidates[0];
    if (!best || best.confidence < 0.6) continue;

    usedPrevious.add(best.previousId);
    usedNext.add(best.nextId);
    if (best.confidence >= 0.8) matched.push(best);
    else needsReview.push(best);
  }

  return {
    matched,
    needsReview,
    added: next.filter((component) => !usedNext.has(component.id)),
    removed: previous.filter((component) => !usedPrevious.has(component.id))
  };
}
