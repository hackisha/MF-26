import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

describe("Vite packaging config", () => {
  it("emits relative asset URLs for file-based Electron packaging", () => {
    const viteConfig = readFileSync(join(process.cwd(), "vite.config.ts"), "utf8");

    expect(viteConfig).toMatch(/base:\s*["']\.\/["']/);
  });

  it("defines Node-style global for browser Plotly dependencies", () => {
    const viteConfig = readFileSync(join(process.cwd(), "vite.config.ts"), "utf8");

    expect(viteConfig).toContain('global: "globalThis"');
  });
});
