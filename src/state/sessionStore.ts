import { create } from "zustand";
import { parseCsv, type CsvImportWarning } from "../domain/csvImport";
import { defaultProfiles } from "../domain/defaultProfiles";
import { runDiagnostics } from "../domain/diagnostics";
import { detectEvents } from "../domain/events";
import { applyProfile } from "../domain/profileApply";
import { createManualSegment, segmentsFromEvents } from "../domain/segments";
import type { AnalysisSession, DiagnosticFinding, OverlayPreset, Segment, VehicleProfile } from "../domain/types";

type CsvOpenResult = {
  filePath: string;
  text: string;
};

type SourceCsv = CsvOpenResult;

export type SessionSnapshot = {
  profiles: VehicleProfile[];
  selectedProfileId: string;
  sourceCsv: SourceCsv | null;
  session: AnalysisSession | null;
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlayId: string | null;
};

type MfLogAnalyzerApi = {
  openCsv: () => Promise<CsvOpenResult | null>;
  saveHtmlReport: (html: string) => Promise<string | null>;
  popout: (route: string) => Promise<boolean>;
  setSessionSnapshot?: (snapshot: SessionSnapshot) => Promise<void> | void;
  getSessionSnapshot?: () => Promise<SessionSnapshot | null> | SessionSnapshot | null;
};

declare global {
  interface Window {
    mfLogAnalyzer?: MfLogAnalyzerApi;
  }
}

type SelectionSyncMessage = {
  type: "session-selection";
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlayId: string | null;
};

type SessionState = {
  profiles: VehicleProfile[];
  selectedProfileId: string;
  sourceCsv: SourceCsv | null;
  session: AnalysisSession | null;
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlay: OverlayPreset | null;
  setSelectedProfileId: (profileId: string) => void;
  openCsv: (sourceCsv?: CsvOpenResult) => Promise<void>;
  addManualSegment: (name: string, startSec: number, endSec: number) => void;
  setCurrentTimeSec: (currentTimeSec: number | null) => void;
  setSelectedEventId: (selectedEventId: string | null) => void;
  setSelectedOverlay: (overlay: OverlayPreset | null) => void;
  updateProfile: (profile: VehicleProfile) => void;
};

export function fileNameFromPath(filePath: string): string {
  return filePath.split(/[\\/]/).pop() || filePath;
}

function profileById(profiles: VehicleProfile[], profileId: string): VehicleProfile {
  return profiles.find((profile) => profile.id === profileId) ?? profiles[0] ?? defaultProfiles[0];
}

function overlayForProfile(profile: VehicleProfile, overlayId?: string | null): OverlayPreset | null {
  if (overlayId) {
    const matchingOverlay = profile.overlays.find((overlay) => overlay.id === overlayId);
    if (matchingOverlay) return matchingOverlay;
  }

  return profile.overlays[0] ?? null;
}

function selectedOverlayForProfile(profile: VehicleProfile, overlay: OverlayPreset | null): OverlayPreset | null {
  if (overlay && profile.overlays.some((profileOverlay) => profileOverlay.id === overlay.id)) return overlay;
  return profile.overlays[0] ?? null;
}

function firstTimestampSec(session: AnalysisSession | null): number | null {
  return session?.log.rows[0]?.timestampSec ?? null;
}

function manualSegments(segments: Segment[]): Segment[] {
  return segments.filter((segment) => segment.source === "manual");
}

function createSession(sourceCsv: SourceCsv, profile: VehicleProfile, preservedManualSegments: Segment[] = []): AnalysisSession {
  const parsed = parseCsv(sourceCsv.text);
  const log = applyProfile(fileNameFromPath(sourceCsv.filePath), parsed, profile);
  const diagnostics = [...csvImportDiagnostics(parsed.warnings), ...runDiagnostics(log, profile)];
  const events = detectEvents(log, profile);

  return {
    filePath: sourceCsv.filePath,
    profileId: profile.id,
    log,
    diagnostics,
    events,
    segments: [...segmentsFromEvents(events), ...preservedManualSegments]
  };
}

function csvImportDiagnostics(warnings: CsvImportWarning[]): DiagnosticFinding[] {
  return warnings.map((warning) => {
    const row = warning.row ?? "unknown";

    return {
      id: `csv-import-warning-${row}-${warning.code}`,
      severity: "warning",
      title: "Skipped malformed CSV row",
      detail: `Row ${row} was skipped: ${warning.message}`,
      affectedChannelIds: ["CSV"]
    };
  });
}

function sanitizeSelectedEventId(session: AnalysisSession | null, selectedEventId: string | null): string | null {
  return session?.events.some((event) => event.id === selectedEventId) ? selectedEventId : null;
}

let snapshotPublishQueue: Promise<void> = Promise.resolve();
let selectionSyncChannel: BroadcastChannel | null = null;
let suppressSelectionSyncPublish = false;

function createSelectionSyncMessage(): SelectionSyncMessage {
  const state = useSessionStore.getState();

  return {
    type: "session-selection",
    currentTimeSec: state.currentTimeSec,
    selectedEventId: state.selectedEventId,
    selectedOverlayId: state.selectedOverlay?.id ?? null
  };
}

function publishSelectionSync() {
  if (suppressSelectionSyncPublish) return;
  selectionSyncChannel?.postMessage(createSelectionSyncMessage());
}

function applySelectionSync(message: SelectionSyncMessage) {
  const { profiles, selectedProfileId, session } = useSessionStore.getState();
  const profile = profileById(profiles, selectedProfileId);

  suppressSelectionSyncPublish = true;
  try {
    useSessionStore.setState({
      currentTimeSec: message.currentTimeSec,
      selectedEventId: sanitizeSelectedEventId(session, message.selectedEventId),
      selectedOverlay: overlayForProfile(profile, message.selectedOverlayId)
    });
  } finally {
    suppressSelectionSyncPublish = false;
  }
}

export const useSessionStore = create<SessionState>((set, get) => {
  const initialProfile = defaultProfiles[0];

  return {
    profiles: defaultProfiles,
    selectedProfileId: initialProfile.id,
    sourceCsv: null,
    session: null,
    currentTimeSec: null,
    selectedEventId: null,
    selectedOverlay: overlayForProfile(initialProfile),
    setSelectedProfileId: (profileId) => {
      const { profiles, selectedOverlay, selectedEventId, session, sourceCsv } = get();
      const profile = profileById(profiles, profileId);
      const nextSession = sourceCsv ? createSession(sourceCsv, profile, manualSegments(session?.segments ?? [])) : session;
      const nextCurrentTimeSec = nextSession ? firstTimestampSec(nextSession) : get().currentTimeSec;

      set({
        selectedProfileId: profile.id,
        session: nextSession,
        currentTimeSec: nextCurrentTimeSec,
        selectedEventId: sanitizeSelectedEventId(nextSession, selectedEventId),
        selectedOverlay: overlayForProfile(profile, selectedOverlay?.id)
      });
      void publishSessionSnapshot();
    },
    openCsv: async (sourceCsv) => {
      const result = sourceCsv ?? (await window.mfLogAnalyzer?.openCsv());
      if (!result) return;

      const { profiles, selectedProfileId } = get();
      const profile = profileById(profiles, selectedProfileId);
      const session = createSession(result, profile);

      set({
        sourceCsv: result,
        session,
        currentTimeSec: firstTimestampSec(session),
        selectedEventId: null,
        selectedOverlay: overlayForProfile(profile, get().selectedOverlay?.id)
      });
      await publishSessionSnapshot();
    },
    addManualSegment: (name, startSec, endSec) => {
      const { session } = get();
      if (!session) return;

      set({
        session: {
          ...session,
          segments: [...session.segments, createManualSegment(name, startSec, endSec)]
        }
      });
      void publishSessionSnapshot();
    },
    setCurrentTimeSec: (currentTimeSec) => {
      set({ currentTimeSec });
      publishSelectionSync();
      void publishSessionSnapshot();
    },
    setSelectedEventId: (selectedEventId) => {
      set({ selectedEventId });
      publishSelectionSync();
      void publishSessionSnapshot();
    },
    setSelectedOverlay: (overlay) => {
      const { profiles, selectedProfileId } = get();
      const profile = profileById(profiles, selectedProfileId);

      set({ selectedOverlay: selectedOverlayForProfile(profile, overlay) });
      publishSelectionSync();
      void publishSessionSnapshot();
    },
    updateProfile: (profile) => {
      const { profiles, selectedProfileId, selectedOverlay, selectedEventId, session, sourceCsv } = get();
      const hasExistingProfile = profiles.some((currentProfile) => currentProfile.id === profile.id);
      const nextProfiles = hasExistingProfile
        ? profiles.map((currentProfile) => (currentProfile.id === profile.id ? profile : currentProfile))
        : [...profiles, profile];
      const nextSelectedProfileId = selectedProfileId === profile.id ? profile.id : selectedProfileId;
      const selectedProfile = profileById(nextProfiles, nextSelectedProfileId);
      const shouldRebuildSession = session?.profileId === profile.id && sourceCsv;
      const nextSession = shouldRebuildSession ? createSession(sourceCsv, profile, manualSegments(session.segments)) : session;

      set({
        profiles: nextProfiles,
        selectedProfileId: nextSelectedProfileId,
        session: nextSession,
        selectedEventId: sanitizeSelectedEventId(nextSession, selectedEventId),
        selectedOverlay: overlayForProfile(selectedProfile, selectedOverlay?.id)
      });
      void publishSessionSnapshot();
    }
  };
});

export function createSessionSnapshot(): SessionSnapshot {
  const state = useSessionStore.getState();

  return {
    profiles: state.profiles,
    selectedProfileId: state.selectedProfileId,
    sourceCsv: state.sourceCsv,
    session: state.session,
    currentTimeSec: state.currentTimeSec,
    selectedEventId: state.selectedEventId,
    selectedOverlayId: state.selectedOverlay?.id ?? null
  };
}

export async function publishSessionSnapshot(): Promise<void> {
  const setSessionSnapshot = window.mfLogAnalyzer?.setSessionSnapshot;
  if (!setSessionSnapshot) return;

  const snapshot = createSessionSnapshot();
  const publish = snapshotPublishQueue.then(() => setSessionSnapshot(snapshot));
  snapshotPublishQueue = publish.catch(() => undefined);
  await publish;
}

export async function hydrateSessionSnapshot(): Promise<void> {
  const snapshot = await window.mfLogAnalyzer?.getSessionSnapshot?.();
  if (!snapshot) return;

  const selectedProfile = profileById(snapshot.profiles, snapshot.selectedProfileId);
  const selectedEventId = sanitizeSelectedEventId(snapshot.session, snapshot.selectedEventId);

  useSessionStore.setState({
    profiles: snapshot.profiles,
    selectedProfileId: selectedProfile.id,
    sourceCsv: snapshot.sourceCsv,
    session: snapshot.session,
    currentTimeSec: snapshot.currentTimeSec,
    selectedEventId,
    selectedOverlay: overlayForProfile(selectedProfile, snapshot.selectedOverlayId)
  });
}

export function startSessionSelectionSync(): () => void {
  if (typeof BroadcastChannel === "undefined") return () => undefined;

  selectionSyncChannel?.close();
  const channel = new BroadcastChannel("mf-log-analyzer-session-selection");
  selectionSyncChannel = channel;

  channel.addEventListener("message", (event: MessageEvent<SelectionSyncMessage>) => {
    if (event.data?.type !== "session-selection") return;
    applySelectionSync(event.data);
  });

  return () => {
    if (selectionSyncChannel === channel) {
      selectionSyncChannel = null;
    }
    channel.close();
  };
}
