import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const systemChromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const useSystemChrome = process.env.PLAYWRIGHT_USE_SYSTEM_CHROME === "1" && existsSync(systemChromePath);
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEB_SERVER === "1";
const configuredPort = process.env.PLAYWRIGHT_PORT;
const port = configuredPort && /^\d+$/.test(configuredPort) ? configuredPort : "5173";
const baseUrl = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30000,
  use: {
    baseURL: baseUrl,
    ...(useSystemChrome
      ? {
          launchOptions: {
            executablePath: systemChromePath
          }
        }
      : {})
  },
  webServer: skipWebServer
    ? undefined
    : {
        command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${port} --strictPort`,
        env: {
          VITE_DISABLE_WATCH: "1"
        },
        url: baseUrl,
        reuseExistingServer: true
      }
});
