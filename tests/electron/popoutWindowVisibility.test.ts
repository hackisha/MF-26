import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

describe("Electron pop-out windows", () => {
  it("opens pop-out windows from the requesting window and brings them forward after load", () => {
    const mainSource = readFileSync(join(process.cwd(), "electron", "main.ts"), "utf8");

    expect(mainSource).toContain("BrowserWindow.fromWebContents(event.sender)");
    expect(mainSource).toContain('kind: "popout"');
    expect(mainSource).toContain("show: false");
    expect(mainSource).toContain("win.show()");
    expect(mainSource).toContain("win.focus()");
  });
});
