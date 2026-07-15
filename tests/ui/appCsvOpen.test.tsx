import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../src/App";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { useSessionStore } from "../../src/state/sessionStore";

const csv = [
  "Timestamp,RPM,Batt_V,OilPressure_bar,ax_g,ay_g",
  "0,1000,12.4,3.2,8,0",
  "1,1500,12.3,3.1,16,8"
].join("\n");

function resetStore() {
  useSessionStore.setState({
    profiles: defaultProfiles,
    selectedProfileId: defaultProfiles[0].id,
    sourceCsv: null,
    session: null,
    currentTimeSec: null,
    selectedEventId: null,
    selectedOverlay: defaultProfiles[0].overlays[0] ?? null
  });
}

describe("App CSV open fallback", () => {
  beforeEach(() => {
    resetStore();
    delete window.mfLogAnalyzer;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete window.mfLogAnalyzer;
  });

  it("loads a CSV through the browser file picker when the desktop API is unavailable", async () => {
    const file = new File([csv], "fallback.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: vi.fn(async () => csv) });
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Open CSV" }));

    expect(clickSpy).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText("CSV file picker"), { target: { files: [file] } });

    expect(await screen.findByText("Loaded fallback.csv")).not.toBeNull();
    expect(useSessionStore.getState().session?.log.fileName).toBe("fallback.csv");
  });

  it("does not expose the removed Workspace tab", () => {
    render(<App />);

    expect(screen.queryByRole("tab", { name: "Workspace" })).toBeNull();
    expect(screen.getByRole("tab", { name: "CSV Playback" })).not.toBeNull();
  });

  it("shows an error when the desktop CSV open flow fails", async () => {
    window.mfLogAnalyzer = {
      openCsv: vi.fn(async () => {
        throw new Error("CSV parse failed");
      }),
      saveHtmlReport: vi.fn(async () => null),
      popout: vi.fn(async () => true)
    };

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Open CSV" }));

    expect((await screen.findByRole("alert")).textContent).toContain("CSV parse failed");
    expect(useSessionStore.getState().session).toBeNull();
  });

  it("loads a CSV when the desktop File menu open command fires", async () => {
    let menuHandler: (() => void) | null = null;
    window.mfLogAnalyzer = {
      openCsv: vi.fn(async () => ({
        filePath: "C:\\logs\\menu-open.csv",
        text: csv
      })),
      saveHtmlReport: vi.fn(async () => null),
      popout: vi.fn(async () => true),
      onOpenCsvMenu: vi.fn((handler) => {
        menuHandler = handler;
        return vi.fn();
      })
    };

    render(<App />);

    await act(async () => {
      menuHandler?.();
    });

    expect(await screen.findByText("Loaded menu-open.csv")).not.toBeNull();
    expect(window.mfLogAnalyzer.openCsv).toHaveBeenCalledTimes(1);
  });
});
