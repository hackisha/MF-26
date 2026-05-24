import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const systemChromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const useSystemChrome = process.env.PLAYWRIGHT_USE_SYSTEM_CHROME === "1" && existsSync(systemChromePath);

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    ...(useSystemChrome
      ? {
          launchOptions: {
            executablePath: systemChromePath
          }
        }
      : {})
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true
  }
});
