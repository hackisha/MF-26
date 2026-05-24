import { app, BrowserWindow, dialog, ipcMain, Menu, type MenuItemConstructorOptions } from "electron";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import { isAllowedNavigationUrl, isDevRuntime, rendererUrlForRoute } from "./runtimeMode.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const devOrigin = process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173";
const maxHtmlReportBytes = 10 * 1024 * 1024;
const rendererEntryUrl = pathToFileURL(path.join(__dirname, "../dist/index.html")).toString();
const packagedRendererExists = existsSync(path.join(__dirname, "../dist/index.html"));
const isDev = isDevRuntime({
  appIsPackaged: app.isPackaged,
  packagedRendererExists,
  viteDevServerUrl: process.env.VITE_DEV_SERVER_URL
});
let latestSessionSnapshot: unknown = null;

function rendererUrl(route = "/") {
  return rendererUrlForRoute({ devOrigin, isDev, rendererEntryUrl, route });
}

function isAllowedNavigation(url: string) {
  return isAllowedNavigationUrl({ devOrigin, isDev, rendererEntryUrl, url });
}

function validateRoute(route: unknown) {
  if (typeof route !== "string") {
    throw new Error("Pop-out route must be a string.");
  }

  if (!route.startsWith("/") || route.startsWith("//") || /^[a-z][a-z0-9+.-]*:/i.test(route)) {
    throw new Error("Pop-out route must be an app-local path.");
  }

  return route;
}

function createWindow(route = "/") {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    title: "MF Log Analyzer",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.setAutoHideMenuBar(false);
  win.setMenuBarVisibility(true);
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event, url) => {
    if (!isAllowedNavigation(url)) {
      event.preventDefault();
    }
  });

  void win.loadURL(rendererUrl(route));
  return win;
}

function sendOpenCsvCommand(window: BrowserWindow | undefined | null) {
  window?.webContents.send("menu:openCsv");
}

function installApplicationMenu() {
  const isMac = process.platform === "darwin";
  const template: MenuItemConstructorOptions[] = [
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [{ role: "about" }, { type: "separator" }, { role: "quit" }]
          } satisfies MenuItemConstructorOptions
        ]
      : []),
    {
      label: "File",
      submenu: [
        {
          label: "Open CSV...",
          accelerator: "CmdOrCtrl+O",
          click: () => sendOpenCsvCommand(BrowserWindow.getFocusedWindow())
        },
        { type: "separator" },
        isMac ? { role: "close" } : { role: "quit", label: "Exit" }
      ]
    },
    { role: "viewMenu" },
    { role: "windowMenu" }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(() => {
  installApplicationMenu();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("file:openCsv", async () => {
  const result = await dialog.showOpenDialog({
    title: "Open CSV log",
    filters: [{ name: "CSV files", extensions: ["csv"] }],
    properties: ["openFile"]
  });

  if (result.canceled || result.filePaths.length === 0) return null;
  const filePath = result.filePaths[0];
  const text = await fs.readFile(filePath, "utf8");
  return { filePath, text };
});

ipcMain.handle("file:saveHtmlReport", async (_event, html: string) => {
  if (typeof html !== "string") {
    throw new Error("HTML report payload must be a string.");
  }

  if (Buffer.byteLength(html, "utf8") > maxHtmlReportBytes) {
    throw new Error("HTML report payload exceeds the 10 MB limit.");
  }

  const result = await dialog.showSaveDialog({
    title: "Save HTML report",
    defaultPath: "mf-log-analyzer-report.html",
    filters: [{ name: "HTML files", extensions: ["html"] }]
  });

  if (result.canceled || !result.filePath) return null;
  await fs.writeFile(result.filePath, html, "utf8");
  return result.filePath;
});

ipcMain.handle("view:popout", async (_event, route: unknown) => {
  createWindow(validateRoute(route));
  return true;
});

ipcMain.handle("session:setSnapshot", async (_event, snapshot: unknown) => {
  latestSessionSnapshot = snapshot;
});

ipcMain.handle("session:getSnapshot", async () => latestSessionSnapshot);
