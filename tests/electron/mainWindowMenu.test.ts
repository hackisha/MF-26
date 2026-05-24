import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("Electron main window menu visibility", () => {
  it("keeps the native menu bar visible in portable Windows builds", () => {
    const mainSource = readFileSync(join(process.cwd(), "electron", "main.ts"), "utf8");

    expect(mainSource).toContain("win.setAutoHideMenuBar(false)");
    expect(mainSource).toContain("win.setMenuBarVisibility(true)");
  });
});
