import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("Electron preload packaging", () => {
  it("uses a CommonJS preload file for packaged Electron windows", () => {
    const mainSource = readFileSync(join(process.cwd(), "electron", "main.ts"), "utf8");

    expect(mainSource).toContain('path.join(__dirname, "preload.cjs")');
  });

  it("builds and waits for the CommonJS preload output", () => {
    const packageJson = JSON.parse(readFileSync(join(process.cwd(), "package.json"), "utf8")) as {
      scripts: Record<string, string>;
    };

    expect(existsSync(join(process.cwd(), "electron", "preload.cts"))).toBe(true);
    expect(packageJson.scripts["electron:dev"]).toContain("dist-electron/preload.cjs");
  });
});
