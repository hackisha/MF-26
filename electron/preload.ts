import { contextBridge, ipcRenderer } from "electron";

export type DesktopApi = {
  openCsv: () => Promise<{ filePath: string; text: string } | null>;
  saveHtmlReport: (html: string) => Promise<string | null>;
  popout: (route: string) => Promise<boolean>;
  setSessionSnapshot: (snapshot: unknown) => Promise<void>;
  getSessionSnapshot: () => Promise<unknown>;
};

const api: DesktopApi = {
  openCsv: () => ipcRenderer.invoke("file:openCsv"),
  saveHtmlReport: (html) => ipcRenderer.invoke("file:saveHtmlReport", html),
  popout: (route) => ipcRenderer.invoke("view:popout", route),
  setSessionSnapshot: (snapshot) => ipcRenderer.invoke("session:setSnapshot", snapshot),
  getSessionSnapshot: () => ipcRenderer.invoke("session:getSnapshot")
};

contextBridge.exposeInMainWorld("mfLogAnalyzer", api);
