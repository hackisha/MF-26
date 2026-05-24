import { describe, expect, it } from "vitest";
import { isAllowedNavigationUrl, isDevRuntime, rendererUrlForRoute } from "../../electron/runtimeMode";

describe("Electron runtime mode", () => {
  it("uses packaged renderer files for a loose portable app with built assets", () => {
    expect(isDevRuntime({ appIsPackaged: false, packagedRendererExists: true, viteDevServerUrl: undefined })).toBe(false);
    expect(rendererUrlForRoute({
      devOrigin: "http://127.0.0.1:5173",
      isDev: false,
      rendererEntryUrl: "file:///C:/mf/resources/app/dist/index.html",
      route: "/vehicle-behavior"
    })).toBe("file:///C:/mf/resources/app/dist/index.html#/vehicle-behavior");
  });

  it("uses the Vite dev server when a dev server URL is explicitly provided", () => {
    expect(isDevRuntime({ appIsPackaged: false, packagedRendererExists: true, viteDevServerUrl: "http://127.0.0.1:5173" })).toBe(true);
    expect(rendererUrlForRoute({
      devOrigin: "http://127.0.0.1:5173",
      isDev: true,
      rendererEntryUrl: "file:///C:/mf/resources/app/dist/index.html",
      route: "/map-lap"
    })).toBe("http://127.0.0.1:5173/map-lap");
  });

  it("allows only the active renderer origin or entry file", () => {
    expect(isAllowedNavigationUrl({
      devOrigin: "http://127.0.0.1:5173",
      isDev: false,
      rendererEntryUrl: "file:///C:/mf/resources/app/dist/index.html",
      url: "file:///C:/mf/resources/app/dist/index.html#/map-lap"
    })).toBe(true);
    expect(isAllowedNavigationUrl({
      devOrigin: "http://127.0.0.1:5173",
      isDev: false,
      rendererEntryUrl: "file:///C:/mf/resources/app/dist/index.html",
      url: "http://127.0.0.1:5173/map-lap"
    })).toBe(false);
  });
});
