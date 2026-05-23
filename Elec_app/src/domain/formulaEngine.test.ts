import { describe, expect, test } from "vitest";
import { evaluateFormula } from "./formulaEngine";

describe("formula engine", () => {
  test("evaluates arithmetic, comparisons, booleans, and helper functions without eval", () => {
    const values = { RPM: 6400, TPS_percent: 72, ax_g: 0.42, ay_g: -0.3 };

    expect(evaluateFormula("RPM / 1000 + max(abs(ax_g), abs(ay_g))", values)).toBeCloseTo(6.82);
    expect(evaluateFormula("ax_g * 9.81", values)).toBeCloseTo(4.1202);
    expect(evaluateFormula("RPM > 6000 && TPS_percent > 50", values)).toBe(1);
    expect(evaluateFormula("RPM < 6000 || TPS_percent > 50", values)).toBe(1);
  });

  test("rejects unsafe or unknown expressions", () => {
    expect(() => evaluateFormula("constructor.constructor('return process')()", {})).toThrow();
    expect(() => evaluateFormula("unknownFn(RPM)", { RPM: 1 })).toThrow();
    expect(() => evaluateFormula("MissingSensor < 1", {})).toThrow("알 수 없는 센서");
  });
});
