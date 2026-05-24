import type { AppliedLog, DetectedEvent, NumericLogRow, RuleCondition, ThresholdRule, VehicleProfile } from "./types";

function compare(value: number, condition: RuleCondition): boolean {
  switch (condition.op) {
    case ">":
      return value > condition.value;
    case ">=":
      return value >= condition.value;
    case "<":
      return value < condition.value;
    case "<=":
      return value <= condition.value;
    case "==":
      return value === condition.value;
    case "!=":
      return value !== condition.value;
    default: {
      const exhaustiveCheck: never = condition.op;
      return exhaustiveCheck;
    }
  }
}

function matchesCondition(row: NumericLogRow, condition: RuleCondition): boolean {
  const value = row.values[condition.channelId];
  if (value === null || value === undefined) return false;
  return compare(value, condition);
}

function matchesRule(row: NumericLogRow, rule: ThresholdRule): boolean {
  const all = rule.all ?? [];
  const any = rule.any ?? [];
  if (all.length === 0 && any.length === 0) return false;

  const allMatches = all.length === 0 || all.every((condition) => matchesCondition(row, condition));
  const anyMatches = any.length === 0 || any.some((condition) => matchesCondition(row, condition));

  return allMatches && anyMatches;
}

function createEvent(rule: ThresholdRule, eventOrdinal: number, startSec: number, endSec: number): DetectedEvent {
  return {
    id: `${rule.id}-${eventOrdinal}-${startSec.toFixed(3)}`,
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
    let eventOrdinal = 0;

    for (const row of log.rows) {
      if (matchesRule(row, rule)) {
        openStartSec ??= row.timestampSec;
        previousMatchedSec = row.timestampSec;
        continue;
      }

      if (openStartSec !== null && previousMatchedSec !== null && durationMeetsRule(openStartSec, previousMatchedSec, rule)) {
        events.push(createEvent(rule, eventOrdinal, openStartSec, previousMatchedSec));
        eventOrdinal += 1;
      }

      openStartSec = null;
      previousMatchedSec = null;
    }

    if (openStartSec !== null && previousMatchedSec !== null && durationMeetsRule(openStartSec, previousMatchedSec, rule)) {
      events.push(createEvent(rule, eventOrdinal, openStartSec, previousMatchedSec));
    }
  }

  return events.sort((left, right) => left.startSec - right.startSec);
}
