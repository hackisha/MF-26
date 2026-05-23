import { describe, expect, it } from "vitest";
import { matchUpdatedComponents } from "./updateMatcher";
import type { Component } from "./types";

function component(id: string, symbolName: string, x: number): Component {
  return {
    id,
    sourceId: id,
    rawName: symbolName,
    packageName: symbolName,
    symbolName,
    alias: symbolName,
    x,
    y: 0,
    pins: [{ id: `${id}-1`, componentId: id, number: "1", label: null, x, y: 0, raw: "" }],
    autoRole: "unknown",
    autoConfidence: 0.2,
    confirmedRole: null,
    raw: ""
  };
}

describe("updateMatcher", () => {
  it("matches by id first and falls back to symbol and coordinates", () => {
    const oldComponents = [component("old-1", "MOLEX_12PIN", 100)];
    const newComponents = [component("new-1", "MOLEX_12PIN", 102)];

    const result = matchUpdatedComponents(oldComponents, newComponents);

    expect(result.matched[0]).toMatchObject({
      previousId: "old-1",
      nextId: "new-1",
      confidence: expect.any(Number)
    });
    expect(result.added).toHaveLength(0);
    expect(result.removed).toHaveLength(0);
  });
});
