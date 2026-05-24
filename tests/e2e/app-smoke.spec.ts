import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const fixturePath = join(process.cwd(), "tests", "fixtures", "2025-sample.csv");
const fixtureText = readFileSync(fixturePath, "utf8");

type MfLogAnalyzerTestWindow = Window & {
  __mfPopoutRoutes: string[];
  mfLogAnalyzer?: {
    openCsv: () => Promise<{ filePath: string; text: string }>;
    saveHtmlReport: (html: string) => Promise<string | null>;
    popout: (route: string) => Promise<boolean>;
    setSessionSnapshot: (snapshot: unknown) => Promise<void>;
    getSessionSnapshot: () => Promise<unknown | null>;
  };
};

test("loads a CSV and exposes the app shell views", async ({ page }) => {
  await page.addInitScript((csvText) => {
    const testWindow = window as unknown as MfLogAnalyzerTestWindow;
    testWindow.__mfPopoutRoutes = [];
    testWindow.mfLogAnalyzer = {
      openCsv: async () => ({
        filePath: "C:\\logs\\2025-sample.csv",
        text: csvText
      }),
      saveHtmlReport: async () => "C:\\logs\\2025-sample-report.html",
      popout: async (route: string) => {
        testWindow.__mfPopoutRoutes.push(route);
        return true;
      },
      setSessionSnapshot: async () => undefined,
      getSessionSnapshot: async () => null
    };
  }, fixtureText);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "MF Log Analyzer" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open CSV" })).toBeVisible();

  const expectedTabs = [
    "Summary",
    "Log Diagnostics",
    "Time-Series Graph",
    "Vehicle Behavior",
    "Map / Lap",
    "Report",
    "Settings"
  ];

  for (const tabName of expectedTabs) {
    await expect(page.getByRole("tab", { name: tabName })).toBeVisible();
  }

  await page.getByRole("button", { name: "Open CSV" }).click();
  await expect(page.getByText("Loaded 2025-sample.csv")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Run Summary" })).toBeVisible();
  await expect(page.getByText("Max Corrected G")).toBeVisible();
  await expect(page.getByText("Max EOT_IN")).toBeVisible();

  const popoutButton = page.getByRole("button", { name: "Open this view in a new window" });
  await expect(popoutButton).toBeEnabled();
  await popoutButton.click();
  await expect.poll(() => page.evaluate(() => (window as unknown as MfLogAnalyzerTestWindow).__mfPopoutRoutes)).toEqual(["/"]);

  for (const tabName of expectedTabs) {
    const tab = page.getByRole("tab", { name: tabName });
    await tab.click();
    await expect(tab).toHaveAttribute("aria-selected", "true");
    await expect(popoutButton).toBeEnabled();
  }
});
