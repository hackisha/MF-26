import { fireEvent, render, screen } from "@testing-library/react";
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
});
