import { describe, expect, it } from "vitest";
import { classifyComponent, createClassificationQueue } from "./classification";
import type { Component } from "./types";

function baseComponent(partial: Partial<Component>): Component {
  return {
    id: "c1",
    sourceId: "c1",
    rawName: "",
    packageName: "",
    symbolName: "",
    alias: "",
    x: 0,
    y: 0,
    pins: [],
    autoRole: "unknown",
    autoConfidence: 0,
    confirmedRole: null,
    raw: "",
    ...partial
  };
}

describe("classification", () => {
  it("classifies EMU parts as ECU with high confidence", () => {
    expect(
      classifyComponent({
        packageName: "EMU_GRAY_FOOTPRINT",
        symbolName: "EMU_GRAY_SYMBOL",
        rawName: "EMU Gray",
        pinCount: 34
      })
    ).toMatchObject({ role: "ecu", confidence: 0.9 });
  });

  it("classifies connector-like parts but still queues generic headers", () => {
    const molex = classifyComponent({
      packageName: "MOLEX_12PIN_FOOTPRINT",
      symbolName: "MOLEX_12PIN",
      rawName: "Main Connector",
      pinCount: 12
    });
    const header = classifyComponent({
      packageName: "HDR-F-2.54_1X3",
      symbolName: "HDR-F-2.54_1x3",
      rawName: "Fuel Pump",
      pinCount: 3
    });

    expect(molex.role).toBe("connector");
    expect(molex.confidence).toBeGreaterThan(header.confidence);
    expect(header.role).toBe("connector");
  });

  it("queues components below the confidence threshold", () => {
    const queue = createClassificationQueue([
      baseComponent({ id: "strong", autoRole: "ecu", autoConfidence: 0.9 }),
      baseComponent({ id: "weak", autoRole: "connector", autoConfidence: 0.55 })
    ]);

    expect(queue.map((item) => item.componentId)).toEqual(["weak"]);
  });
});
