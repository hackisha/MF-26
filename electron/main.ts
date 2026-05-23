import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs/promises";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = process.env.VITE_DEV_SERVER_URL !== undefined || !app.isPackaged;

function rendererUrl(route = "/") {
  if (isDev) {
    return `http://127.0.0.1:5173${route}`;
  }
  return `file://${path.join(__dirname, "../dist/index.html")}${route === "/" ? "" : `#${route}`}`;
}

function createWindow(route = "/") {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    title: "MF Log Analyzer",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  void win.loadURL(rendererUrl(route));
  return win;
}

app.whenReady().then(() => {
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
  const result = await dialog.showSaveDialog({
    title: "Save HTML report",
    defaultPath: "mf-log-analyzer-report.html",
    filters: [{ name: "HTML files", extensions: ["html"] }]
  });

  if (result.canceled || !result.filePath) return null;
  await fs.writeFile(result.filePath, html, "utf8");
  return result.filePath;
});

ipcMain.handle("view:popout", async (_event, route: string) => {
  createWindow(route);
  return true;
});
