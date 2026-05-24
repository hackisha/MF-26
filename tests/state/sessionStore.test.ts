import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { SessionSnapshot } from "../../src/state/sessionStore";
import {
  createSessionSnapshot,
  hydrateSessionSnapshot,
  publishSessionSnapshot,
  startSessionSelectionSync,
  useSessionStore
} from "../../src/state/sessionStore";
import type { AnalysisSession, VehicleProfile } from "../../src/domain/types";

const csv = [
  "Timestamp,RPM,EngineSpeed_RPM,Batt_V,OilPressure_bar,ax_g,ay_g",
  "0,100,900,11.5,3.2,1,2",
  "1.2,100,900,11.4,3.1,1,2"
].join("\n");

function cloneProfile(profile: VehicleProfile): VehicleProfile {
  return structuredClone(profile) as VehicleProfile;
}

function createLoadedSession(profile = defaultProfiles[0]): AnalysisSession {
  return {
    filePath: "C:\\logs\\session.csv",
    profileId: profile.id,
    log: {
      fileName: "session.csv",
      profileId: profile.id,
      profileRevision: profile.revision,
      rawHeaders: ["Timestamp", "RPM", "Batt_V"],
      rows: [
        { index: 0, timestampSec: 0, values: { RPM: 900, Batt_V: 11.5 } },
        { index: 1, timestampSec: 1.2, values: { RPM: 900, Batt_V: 11.4 } }
      ]
    },
    diagnostics: [],
    events: [
      {
        id: "event-1",
        ruleId: "low-battery-voltage",
        name: "Low Battery Voltage",
        severity: "warning",
        startSec: 1.2,
        endSec: 1.2,
        description: "Battery voltage is below the expected operating range."
      }
    ],
    segments: []
  };
}

class MockBroadcastChannel {
  static instances: MockBroadcastChannel[] = [];

  listeners: Array<(event: MessageEvent) => void> = [];
  postMessage = vi.fn();
  close = vi.fn();

  constructor(public name: string) {
    MockBroadcastChannel.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (type === "message") this.listeners.push(listener);
  }

  dispatch(data: unknown) {
    for (const listener of this.listeners) {
      listener({ data } as MessageEvent);
    }
  }
}

function installDesktopApi(overrides: Partial<NonNullable<Window["mfLogAnalyzer"]>> = {}) {
  window.mfLogAnalyzer = {
    openCsv: vi.fn(async () => ({ filePath: "C:\\logs\\session.csv", text: csv })),
    saveHtmlReport: vi.fn(async () => null),
    popout: vi.fn(async () => true),
    ...overrides
  };
}

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

describe("session store", () => {
  beforeEach(() => {
    resetStore();
    installDesktopApi();
  });

  afterEach(() => {
    delete window.mfLogAnalyzer;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("rebuilds a loaded session from source CSV when the selected profile changes", async () => {
    const store = useSessionStore.getState();
    await store.openCsv();
    store.addManualSegment("Warmup", 0.2, 0.8);

    useSessionStore.getState().setSelectedProfileId("2026-vehicle");

    const nextState = useSessionStore.getState();
    expect(nextState.session?.profileId).toBe("2026-vehicle");
    expect(nextState.session?.log.profileId).toBe("2026-vehicle");
    expect(nextState.session?.log.profileRevision).toBe("2026.1");
    expect(nextState.session?.segments.some((segment) => segment.source === "manual" && segment.name === "Warmup")).toBe(true);
  });

  it("reapplies source mapping and calibration when updating the loaded profile", async () => {
    await useSessionStore.getState().openCsv();

    const updatedProfile = cloneProfile(defaultProfiles[0]);
    updatedProfile.revision = "2025.2";
    updatedProfile.channels.RPM = {
      ...updatedProfile.channels.RPM,
      sourceColumns: ["EngineSpeed_RPM"],
      calibration: { type: "scaleOffset", scale: 2, offset: 1 }
    };

    useSessionStore.getState().updateProfile(updatedProfile);

    const firstRow = useSessionStore.getState().session?.log.rows[0];
    expect(useSessionStore.getState().session?.log.profileRevision).toBe("2025.2");
    expect(firstRow?.values.RPM).toBe(1801);
  });

  it("clears a stale selected event after profile recompute", async () => {
    await useSessionStore.getState().openCsv();

    const eventId = useSessionStore.getState().session?.events[0]?.id;
    expect(eventId).toBeTypeOf("string");
    useSessionStore.getState().setSelectedEventId(eventId ?? null);

    const updatedProfile = cloneProfile(defaultProfiles[0]);
    updatedProfile.rules = [];
    useSessionStore.getState().updateProfile(updatedProfile);

    expect(useSessionStore.getState().session?.events).toEqual([]);
    expect(useSessionStore.getState().selectedEventId).toBeNull();
  });

  it("adds CSV import warnings to log diagnostics", async () => {
    const malformedCsv = "Timestamp,RPM\n0,1000\nmalformed-row\n1,2000\n";

    await useSessionStore.getState().openCsv({ filePath: "malformed.csv", text: malformedCsv });

    expect(useSessionStore.getState().session?.log.rows).toHaveLength(2);
    expect(useSessionStore.getState().session?.diagnostics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "csv-import-warning-1-TooFewFields",
          severity: "warning",
          title: "Skipped malformed CSV row",
          detail: "Row 1 was skipped: Too few fields: expected 2 fields but parsed 1"
        })
      ])
    );
  });

  it("keeps snapshot APIs optional at runtime", async () => {
    installDesktopApi({
      openCsv: vi.fn(async () => null)
    });

    expect(() => useSessionStore.getState().setCurrentTimeSec(12)).not.toThrow();
    await expect(publishSessionSnapshot()).resolves.toBeUndefined();
    await expect(hydrateSessionSnapshot()).resolves.toBeUndefined();
  });

  it("publishes snapshots in invocation order", async () => {
    let releaseFirstPublish: (() => void) | undefined;
    const persistedSnapshots: SessionSnapshot[] = [];

    installDesktopApi({
      setSessionSnapshot: vi
        .fn()
        .mockImplementationOnce(
          (snapshot: SessionSnapshot) =>
            new Promise<void>((resolve) => {
              releaseFirstPublish = () => {
                persistedSnapshots.push(snapshot);
                resolve();
              };
            })
        )
        .mockImplementationOnce(async (snapshot: SessionSnapshot) => {
          persistedSnapshots.push(snapshot);
        })
    });

    const firstPublish = publishSessionSnapshot();
    useSessionStore.setState({ currentTimeSec: 42 });
    const secondPublish = publishSessionSnapshot();

    await Promise.resolve();
    expect(persistedSnapshots).toEqual([]);

    releaseFirstPublish?.();
    await Promise.all([firstPublish, secondPublish]);

    expect(persistedSnapshots.map((snapshot) => snapshot.currentTimeSec)).toEqual([null, 42]);
  });

  it("broadcasts selection changes from local setters", () => {
    vi.stubGlobal("BroadcastChannel", MockBroadcastChannel);
    const cleanup = startSessionSelectionSync();
    const channel = MockBroadcastChannel.instances.at(-1);

    useSessionStore.getState().setCurrentTimeSec(1.2);

    expect(channel?.postMessage).toHaveBeenCalledWith({
      type: "session-selection",
      currentTimeSec: 1.2,
      selectedEventId: null,
      selectedOverlayId: defaultProfiles[0].overlays[0]?.id ?? null
    });

    cleanup();
  });

  it("does not persist full snapshots for high-frequency time cursor changes", async () => {
    const setSessionSnapshot = vi.fn(async () => undefined);
    installDesktopApi({ setSessionSnapshot });

    useSessionStore.getState().setCurrentTimeSec(1.2);
    await Promise.resolve();

    expect(setSessionSnapshot).not.toHaveBeenCalled();
  });

  it("hydrates selection changes from another window without rebroadcasting them", () => {
    vi.stubGlobal("BroadcastChannel", MockBroadcastChannel);
    const setSessionSnapshot = vi.fn(async () => undefined);
    installDesktopApi({ setSessionSnapshot });
    useSessionStore.setState({
      sourceCsv: { filePath: "C:\\logs\\session.csv", text: csv },
      session: createLoadedSession()
    });
    const cleanup = startSessionSelectionSync();
    const channel = MockBroadcastChannel.instances.at(-1);

    channel?.dispatch({
      type: "session-selection",
      currentTimeSec: 1.2,
      selectedEventId: "event-1",
      selectedOverlayId: defaultProfiles[0].overlays[1]?.id ?? null
    });

    const state = useSessionStore.getState();
    expect(state.currentTimeSec).toBe(1.2);
    expect(state.selectedEventId).toBe("event-1");
    expect(state.selectedOverlay?.id).toBe(defaultProfiles[0].overlays[1]?.id);
    expect(channel?.postMessage).not.toHaveBeenCalled();
    expect(setSessionSnapshot).not.toHaveBeenCalled();

    cleanup();
  });

  it("sanitizes stale event and overlay ids received from another window", () => {
    vi.stubGlobal("BroadcastChannel", MockBroadcastChannel);
    const setSessionSnapshot = vi.fn(async () => undefined);
    installDesktopApi({ setSessionSnapshot });
    useSessionStore.setState({
      sourceCsv: { filePath: "C:\\logs\\session.csv", text: csv },
      session: createLoadedSession()
    });
    const cleanup = startSessionSelectionSync();

    MockBroadcastChannel.instances.at(-1)?.dispatch({
      type: "session-selection",
      currentTimeSec: 2,
      selectedEventId: "missing-event",
      selectedOverlayId: "missing-overlay"
    });

    const state = useSessionStore.getState();
    expect(state.selectedEventId).toBeNull();
    expect(state.selectedOverlay?.id).toBe(defaultProfiles[0].overlays[0]?.id);
    expect(setSessionSnapshot).not.toHaveBeenCalled();

    cleanup();
  });
});
