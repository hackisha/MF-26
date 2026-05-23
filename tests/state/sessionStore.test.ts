import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { SessionSnapshot } from "../../src/state/sessionStore";
import { createSessionSnapshot, hydrateSessionSnapshot, publishSessionSnapshot, useSessionStore } from "../../src/state/sessionStore";
import type { VehicleProfile } from "../../src/domain/types";

const csv = [
  "Timestamp,RPM,EngineSpeed_RPM,Batt_V,OilPressure_bar,ax_g,ay_g",
  "0,100,900,11.5,3.2,1,2",
  "1.2,100,900,11.4,3.1,1,2"
].join("\n");

function cloneProfile(profile: VehicleProfile): VehicleProfile {
  return structuredClone(profile) as VehicleProfile;
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
});
