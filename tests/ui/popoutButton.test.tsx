import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { useSessionStore } from "../../src/state/sessionStore";
import { PopoutButton } from "../../src/ui/PopoutButton";

function resetStore() {
  useSessionStore.setState({
    profiles: defaultProfiles,
    selectedProfileId: defaultProfiles[0].id,
    sourceCsv: null,
    session: null,
    currentTimeSec: 7,
    selectedEventId: null,
    selectedOverlay: defaultProfiles[0].overlays[0] ?? null
  });
}

describe("PopoutButton", () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    delete window.mfLogAnalyzer;
    vi.restoreAllMocks();
  });

  it("publishes the current snapshot before opening the requested route", async () => {
    const calls: string[] = [];
    window.mfLogAnalyzer = {
      openCsv: vi.fn(async () => null),
      saveHtmlReport: vi.fn(async () => null),
      setSessionSnapshot: vi.fn(async (snapshot) => {
        calls.push(`snapshot:${snapshot.currentTimeSec}`);
      }),
      getSessionSnapshot: vi.fn(async () => null),
      popout: vi.fn(async (route) => {
        calls.push(`popout:${route}`);
        return true;
      })
    };

    render(<PopoutButton route="/time-series" />);

    fireEvent.click(screen.getByRole("button", { name: "Open this view in a new window" }));

    await waitFor(() => {
      expect(window.mfLogAnalyzer?.popout).toHaveBeenCalledWith("/time-series");
    });
    expect(calls).toEqual(["snapshot:7", "popout:/time-series"]);
  });

  it("is disabled when the desktop pop-out API is unavailable", () => {
    window.mfLogAnalyzer = {
      openCsv: vi.fn(async () => null),
      saveHtmlReport: vi.fn(async () => null),
      popout: undefined as never
    };

    render(<PopoutButton route="/behavior" />);

    expect((screen.getByRole("button", { name: "Open this view in a new window" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
