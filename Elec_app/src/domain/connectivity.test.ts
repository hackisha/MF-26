import { describe, expect, it } from "vitest";
import { buildConnectivityGraph, traceFromPin } from "./connectivity";
import type { Component, ParsedSchematic } from "./types";

function component(id: string, role: Component["autoRole"], x: number, y: number): Component {
  return {
    id,
    sourceId: id,
    rawName: id,
    packageName: id,
    symbolName: id,
    alias: id,
    x,
    y,
    pins: [{ id: `${id}-1`, componentId: id, number: "1", label: null, x, y, raw: "" }],
    autoRole: role,
    autoConfidence: 1,
    confirmedRole: role,
    raw: ""
  };
}

describe("connectivity", () => {
  it("connects pins through wire endpoints and traces connected components", () => {
    const ecu = component("ecu", "ecu", 0, 0);
    const connector = component("connector", "connector", 10, 0);
    const sensor = component("sensor", "sensor", 20, 0);
    const parsed: ParsedSchematic = {
      source: {
        fileName: "fixture.json",
        title: "fixture",
        editorVersion: "6.5.51",
        uploadedAt: "2026-05-21T00:00:00.000Z",
        hash: "hash",
        shapeCounts: {}
      },
      components: [ecu, connector, sensor],
      wires: [
        { id: "w1", points: [{ x: 0, y: 0 }, { x: 10, y: 0 }], raw: "" },
        { id: "w2", points: [{ x: 10, y: 0 }, { x: 20, y: 0 }], raw: "" }
      ],
      junctions: [{ id: "j1", x: 10, y: 0, raw: "" }],
      labels: [],
      warnings: []
    };

    const graph = buildConnectivityGraph(parsed);
    const trace = traceFromPin(graph, parsed.components, "ecu-1");

    expect(trace.map((item) => item.id)).toEqual(["ecu", "connector", "sensor"]);
  });
});
