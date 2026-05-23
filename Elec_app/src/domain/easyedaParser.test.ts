import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";
import { parseEasyEdaSchematic } from "./easyedaParser";

const fixture = {
  editorVersion: "6.5.51",
  title: "fixture",
  schematics: [
    {
      dataStr: {
        shape: [
          "W~0 0 10 0~#000000~1~0~none~wire1~0",
          "J~10~0~2.5~#CC0000~junction1~0",
          "F~part_netLabel_VCC~10~0~0~label1~~0^^10~0^^+12V~#FF0000~0~0~0~start~1~Times New Roman~9pt",
          "LIB~100~200~package`MOLEX_12PIN_FOOTPRINT`spiceSymbolName`MOLEX_12PIN`~~0~src-molex#@$T~N~100~190~0~#000080~Arial~~~~~comment~Main Connector~1~start~text1~0~pinpart#@$P~show~1~1~90~200~180~pin1~0^^90~200^^M 90 200 h 10~#880000^^1~100#@$P~show~1~2~90~210~180~pin2~0^^90~210^^M 90 210 h 10~#880000^^1~100"
        ]
      }
    }
  ]
};

describe("parseEasyEdaSchematic", () => {
  it("extracts counts, components, pins, wires, junctions, and labels", async () => {
    const result = await parseEasyEdaSchematic({
      fileName: "fixture.json",
      text: JSON.stringify(fixture),
      uploadedAt: "2026-05-21T00:00:00.000Z",
      hash: "hash-1"
    });

    expect(result.source.shapeCounts).toMatchObject({ W: 1, J: 1, F: 1, LIB: 1 });
    expect(result.components).toHaveLength(1);
    expect(result.components[0].symbolName).toBe("MOLEX_12PIN");
    expect(result.components[0].pins.map((pin) => pin.number)).toEqual(["1", "2"]);
    expect(result.wires).toHaveLength(1);
    expect(result.junctions).toHaveLength(1);
    expect(result.labels[0].label).toBe("+12V");
  });

  it("returns warnings instead of throwing on unsupported shapes", async () => {
    const result = await parseEasyEdaSchematic({
      fileName: "fixture.json",
      text: JSON.stringify({ ...fixture, schematics: [{ dataStr: { shape: ["ZZ~bad"] } }] }),
      uploadedAt: "2026-05-21T00:00:00.000Z",
      hash: "hash-2"
    });

    expect(result.warnings[0]).toContain("Unsupported shape type: ZZ");
  });

  it("parses the checked-in MF-26 EasyEDA sample", async () => {
    const text = await readFile("SCH_26.5.11-배선도_2026-05-19.json", "utf8");
    const result = await parseEasyEdaSchematic({
      fileName: "SCH_26.5.11-배선도_2026-05-19.json",
      text,
      uploadedAt: "2026-05-21T00:00:00.000Z",
      hash: "sample"
    });

    expect(result.components).toHaveLength(39);
    expect(result.wires).toHaveLength(324);
    expect(result.junctions).toHaveLength(89);
    expect(result.source.shapeCounts).toMatchObject({
      LIB: 39,
      W: 324,
      J: 89,
      T: 248,
      F: 9
    });
    expect(result.components.some((component) => component.symbolName === "EMU_BLACK_SYMBOL")).toBe(true);
    expect(result.components.some((component) => component.symbolName === "MOLEX_12PIN")).toBe(true);
  });
});
