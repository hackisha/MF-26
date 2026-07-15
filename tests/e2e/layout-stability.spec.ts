import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const fixturePath = join(process.cwd(), "tests", "fixtures", "2025-sample.csv");
const fixtureText = readFileSync(fixturePath, "utf8");

type MfLogAnalyzerWindow = Window & {
  mfLogAnalyzer?: {
    openCsv: () => Promise<{ filePath: string; text: string }>;
    saveHtmlReport: (html: string) => Promise<string | null>;
    popout: (route: string) => Promise<boolean>;
    setSessionSnapshot: (snapshot: unknown) => Promise<void>;
    getSessionSnapshot: () => Promise<unknown | null>;
  };
};

async function installCsvApi(page: Page) {
  await page.addInitScript((csvText) => {
    const testWindow = window as MfLogAnalyzerWindow;
    testWindow.mfLogAnalyzer = {
      openCsv: async () => ({
        filePath: "C:\\logs\\2025-sample.csv",
        text: csvText as string
      }),
      saveHtmlReport: async () => "C:\\logs\\2025-sample-report.html",
      popout: async () => true,
      setSessionSnapshot: async () => undefined,
      getSessionSnapshot: async () => null
    };
  }, fixtureText);
}

async function sampleBoxHeights(page: Page, selector: string) {
  const samples: number[] = [];
  for (let index = 0; index < 8; index += 1) {
    const height = await page.locator(selector).evaluate((element) => element.getBoundingClientRect().height);
    samples.push(Math.round(height * 100) / 100);
    await page.waitForTimeout(250);
  }
  return samples;
}

function maxDrift(values: number[]): number {
  return Math.max(...values) - Math.min(...values);
}

async function canvasPixelSummary(page: Page, selector: string) {
  return page.locator(selector).evaluate((canvas) => {
    if (!(canvas instanceof HTMLCanvasElement)) return { width: 0, height: 0, coloredPixels: 0 };

    const probe = document.createElement("canvas");
    probe.width = 80;
    probe.height = 60;
    const context = probe.getContext("2d", { willReadFrequently: true });
    if (!context) return { width: canvas.width, height: canvas.height, coloredPixels: 0 };

    context.drawImage(canvas, 0, 0, probe.width, probe.height);
    const pixels = context.getImageData(0, 0, probe.width, probe.height).data;
    let coloredPixels = 0;

    for (let index = 0; index < pixels.length; index += 4) {
      const red = pixels[index];
      const green = pixels[index + 1];
      const blue = pixels[index + 2];
      const alpha = pixels[index + 3];
      const differsFromPanelBackground = red < 238 || green < 238 || blue < 238 || Math.abs(red - green) > 6 || Math.abs(green - blue) > 6;
      if (alpha > 10 && differsFromPanelBackground) coloredPixels += 1;
    }

    return { width: canvas.width, height: canvas.height, coloredPixels };
  });
}

test("keeps behavior model and GPS plot heights stable after render", async ({ page }) => {
  await installCsvApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Open CSV" }).click();

  const modelResponse = page.waitForResponse((response) => response.url().endsWith("/models/car.glb") && response.ok());
  await page.getByRole("tab", { name: "Vehicle Behavior" }).click();
  await expect(page.locator(".behavior-model-shell")).toBeVisible();
  await modelResponse;
  await expect.poll(async () => (await canvasPixelSummary(page, ".behavior-canvas canvas")).coloredPixels).toBeGreaterThan(120);
  const canvasSummary = await canvasPixelSummary(page, ".behavior-canvas canvas");
  expect(canvasSummary.width).toBeGreaterThan(100);
  expect(canvasSummary.height).toBeGreaterThan(100);
  expect(canvasSummary.coloredPixels).toBeGreaterThan(120);
  const behaviorHeights = await sampleBoxHeights(page, ".behavior-model-shell");

  await page.getByRole("tab", { name: "Map / Lap" }).click();
  await expect(page.locator(".map-lap-plot")).toBeVisible();
  const mapHeights = await sampleBoxHeights(page, ".map-lap-plot");

  expect(maxDrift(behaviorHeights)).toBeLessThanOrEqual(2);
  expect(maxDrift(mapHeights)).toBeLessThanOrEqual(2);
});
