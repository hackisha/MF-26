import type { AppliedLog, DetectedEvent, NumericLogRow, RuleCondition, ThresholdRule, VehicleProfile } from "./types";

function compare(value: number, condition: RuleCondition): boolean {
  if (condition.op === ">") return value > condition.value;
  if (condition.op === ">=") return value >= condition.value;
  if (condition.op === "<") return value < condition.value;
  if (condition.op === "<=") return value <= condition.value;
  if (condition.op === "==") return value === condition.value;
  return value !== condition.value;
}

function matchesCondition(row: NumericLogRow, condition: RuleCondition): boolean {
  const value = row.values[condition.channelId];
  if (value === null || value === undefined) return false;
  return compare(value, condition);
}

function matchesRule(row: NumericLogRow, rule: ThresholdRule): boolean {
  const all = rule.all ?? [];
  const any = rule.any ?? [];

  const allMatches = all.length === 0 || all.every((condition) => matchesCondition(row, condition));
  const anyMatches = any.length === 0 || any.some((condition) => matchesCondition(row, condition));

  return allMatches && anyMatches;
}

function createEvent(rule: ThresholdRule, startSec: number, endSec: number): DetectedEvent {
  return {
    id: `${rule.id}-${startSec.toFixed(2)}`,
    ruleId: rule.id,
    name: rule.name,
    severity: rule.severity,
    startSec,
    endSec,
    description: rule.description
  };
}

function durationMeetsRule(startSec: number, endSec: number, rule: ThresholdRule): boolean {
  return endSec - startSec >= rule.minDurationSec;
}

export function detectEvents(log: AppliedLog, profile: VehicleProfile): DetectedEvent[] {
  const events: DetectedEvent[] = [];

  for (const rule of profile.rules) {
    let openStartSec: number | null = null;
    let previousMatchedSec: number | null = null;

    for (const row of log.rows) {
      if (matchesRule(row, rule)) {
        openStartSec ??= row.timestampSec;
        previousMatchedSec = row.timestampSec;
        continue;
      }

      if (openStartSec !== null && previousMatchedSec !== null && durationMeetsRule(openStartSec, previousMatchedSec, rule)) {
        events.push(createEvent(rule, openStartSec, previousMatchedSec));
      }

      openStartSec = null;
      previousMatchedSec = null;
    }

    if (openStartSec !== null && previousMatchedSec !== null && durationMeetsRule(openStartSec, previousMatchedSec, rule)) {
      events.push(createEvent(rule, openStartSec, previousMatchedSec));
    }
  }

  return events.sort((left, right) => left.startSec - right.startSec);
}
