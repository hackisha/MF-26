import type { DetectedEvent, Segment } from "./types";

export function segmentsFromEvents(events: DetectedEvent[]): Segment[] {
  return events.map((event) => ({
    id: `segment-${event.id}`,
    name: event.name,
    startSec: event.startSec,
    endSec: event.endSec,
    source: "event"
  }));
}

export function createManualSegment(name: string, startSec: number, endSec: number): Segment {
  const normalizedStartSec = Math.min(startSec, endSec);
  const normalizedEndSec = Math.max(startSec, endSec);

  return {
    id: `manual-${normalizedStartSec.toFixed(2)}-${normalizedEndSec.toFixed(2)}`,
    name,
    startSec: normalizedStartSec,
    endSec: normalizedEndSec,
    source: "manual"
  };
}
