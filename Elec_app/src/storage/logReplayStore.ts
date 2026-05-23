import type { LogReplaySettings } from "../domain/logSettingsTypes";

export type LogReplayInnerTab = "dashboard" | "overlay" | "gps" | "gg" | "events" | "sensors" | "settings";

export interface StoredLogReplayState {
  csv: {
    fileName: string;
    text: string;
  };
  settings: LogReplaySettings;
  ui: {
    activeTab: LogReplayInnerTab;
    overlayKeys: string[];
    cardKeys: string[];
  };
}

const STORAGE_KEY = "muzil-tools:log-replay-state:v1";
const MAX_LOCAL_STORAGE_CSV_BYTES = 4_000_000;

function isStoredLogReplayState(value: unknown): value is StoredLogReplayState {
  if (!value || typeof value !== "object") return false;
  const state = value as Partial<StoredLogReplayState>;
  return (
    Boolean(state.csv) &&
    typeof state.csv?.fileName === "string" &&
    typeof state.csv?.text === "string" &&
    Boolean(state.settings) &&
    Array.isArray(state.settings?.sensors) &&
    Boolean(state.ui) &&
    Array.isArray(state.ui?.overlayKeys) &&
    Array.isArray(state.ui?.cardKeys)
  );
}

export async function saveStoredLogReplayState(state: StoredLogReplayState): Promise<void> {
  const payload = JSON.stringify(state);
  if (payload.length > MAX_LOCAL_STORAGE_CSV_BYTES) {
    throw new Error("CSV가 브라우저 임시 저장 한도를 넘었습니다. 업로드는 유지되지만 자동 복원은 생략됩니다.");
  }
  localStorage.setItem(STORAGE_KEY, payload);
}

export async function loadStoredLogReplayState(): Promise<StoredLogReplayState | null> {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!isStoredLogReplayState(parsed)) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export async function clearStoredLogReplayState(): Promise<void> {
  localStorage.removeItem(STORAGE_KEY);
}
