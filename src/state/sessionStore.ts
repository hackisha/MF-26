import { create } from "zustand";
import { parseCsv } from "../domain/csvImport";
import { defaultProfiles } from "../domain/defaultProfiles";
import { runDiagnostics } from "../domain/diagnostics";
import { detectEvents } from "../domain/events";
import { applyProfile } from "../domain/profileApply";
import { createManualSegment, segmentsFromEvents } from "../domain/segments";
import type { AnalysisSession, OverlayPreset, Segment, VehicleProfile } from "../domain/types";

type CsvOpenResult = {
  filePath: string;
  text: string;
};

export type SessionSnapshot = {
  profiles: VehicleProfile[];
  selectedProfileId: string;
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

type SessionState = {
  profiles: VehicleProfile[];
  selectedProfileId: string;
  session: AnalysisSession | null;
  currentTimeSec: number | null;
  selectedEventId: string | null;
  selectedOverlay: OverlayPreset | null;
  setSelectedProfileId: (profileId: string) => void;
  openCsv: () => Promise<void>;
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

function createSession(filePath: string, text: string, profile: VehicleProfile): AnalysisSession {
  const parsed = parseCsv(text);
  const log = applyProfile(fileNameFromPath(filePath), parsed, profile);
  const diagnostics = runDiagnostics(log, profile);
  const events = detectEvents(log, profile);

  return {
    filePath,
    profileId: profile.id,
    log,
    diagnostics,
    events,
    segments: segmentsFromEvents(events)
  };
}

function withRecomputedProfile(session: AnalysisSession, profile: VehicleProfile): AnalysisSession {
  const diagnostics = runDiagnostics(session.log, profile);
  const events = detectEvents(session.log, profile);

  return {
    ...session,
    profileId: profile.id,
    diagnostics,
    events,
    segments: [...segmentsFromEvents(events), ...manualSegments(session.segments)]
  };
}

export const useSessionStore = create<SessionState>((set, get) => {
  const initialProfile = defaultProfiles[0];

  return {
    profiles: defaultProfiles,
    selectedProfileId: initialProfile.id,
    session: null,
    currentTimeSec: null,
    selectedEventId: null,
    selectedOverlay: overlayForProfile(initialProfile),
    setSelectedProfileId: (profileId) => {
      const { profiles, selectedOverlay } = get();
      const profile = profileById(profiles, profileId);

      set({
        selectedProfileId: profile.id,
        selectedOverlay: overlayForProfile(profile, selectedOverlay?.id)
      });
      void publishSessionSnapshot();
    },
    openCsv: async () => {
      const result = await window.mfLogAnalyzer?.openCsv();
      if (!result) return;

      const { profiles, selectedProfileId } = get();
      const profile = profileById(profiles, selectedProfileId);
      const session = createSession(result.filePath, result.text, profile);

      set({
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
      void publishSessionSnapshot();
    },
    setSelectedEventId: (selectedEventId) => {
      set({ selectedEventId });
      void publishSessionSnapshot();
    },
    setSelectedOverlay: (overlay) => {
      const { profiles, selectedProfileId } = get();
      const profile = profileById(profiles, selectedProfileId);

      set({ selectedOverlay: selectedOverlayForProfile(profile, overlay) });
      void publishSessionSnapshot();
    },
    updateProfile: (profile) => {
      const { profiles, selectedProfileId, selectedOverlay, selectedEventId, session } = get();
      const hasExistingProfile = profiles.some((currentProfile) => currentProfile.id === profile.id);
      const nextProfiles = hasExistingProfile
        ? profiles.map((currentProfile) => (currentProfile.id === profile.id ? profile : currentProfile))
        : [...profiles, profile];
      const nextSelectedProfileId = selectedProfileId === profile.id ? profile.id : selectedProfileId;
      const selectedProfile = profileById(nextProfiles, nextSelectedProfileId);
      const nextSession = session?.profileId === profile.id ? withRecomputedProfile(session, profile) : session;
      const nextSelectedEventId = nextSession?.events.some((event) => event.id === selectedEventId) ? selectedEventId : null;

      set({
        profiles: nextProfiles,
        selectedProfileId: nextSelectedProfileId,
        session: nextSession,
        selectedEventId: nextSelectedEventId,
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
    session: state.session,
    currentTimeSec: state.currentTimeSec,
    selectedEventId: state.selectedEventId,
    selectedOverlayId: state.selectedOverlay?.id ?? null
  };
}

export async function publishSessionSnapshot(): Promise<void> {
  await window.mfLogAnalyzer?.setSessionSnapshot?.(createSessionSnapshot());
}

export async function hydrateSessionSnapshot(): Promise<void> {
  const snapshot = await window.mfLogAnalyzer?.getSessionSnapshot?.();
  if (!snapshot) return;

  const selectedProfile = profileById(snapshot.profiles, snapshot.selectedProfileId);

  useSessionStore.setState({
    profiles: snapshot.profiles,
    selectedProfileId: selectedProfile.id,
    session: snapshot.session,
    currentTimeSec: snapshot.currentTimeSec,
    selectedEventId: snapshot.selectedEventId,
    selectedOverlay: overlayForProfile(selectedProfile, snapshot.selectedOverlayId)
  });
}
