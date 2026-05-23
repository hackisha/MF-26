import { useEffect, useMemo, useState } from "react";
import { DEFAULT_CARD_KEYS, DEFAULT_OVERLAY_KEYS } from "../../domain/logReplayColumns";
import { extractLogEvents, findNearestSample } from "../../domain/logReplayAnalysis";
import { parseEmuLogCsv } from "../../domain/logReplayParser";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import type { LogReplaySettings } from "../../domain/logSettingsTypes";
import { applyLogReplaySettings } from "../../domain/logSessionTransform";
import type { LogSession, PlaybackState } from "../../domain/logReplayTypes";
import {
  clearStoredLogReplayState,
  loadStoredLogReplayState,
  saveStoredLogReplayState,
  type LogReplayInnerTab,
} from "../../storage/logReplayStore";
import { CsvLogUploader } from "./CsvLogUploader";
import { EventStrip } from "./EventStrip";
import { GGDiagram } from "./GGDiagram";
import { GpsTrackPanel } from "./GpsTrackPanel";
import { LogDashboard } from "./LogDashboard";
import { LogReplayInnerTabs } from "./LogReplayInnerTabs";
import { LogSensorsTable } from "./LogSensorsTable";
import { LogSettingsPanel } from "./LogSettingsPanel";
import { PlaybackControls } from "./PlaybackControls";
import { SensorCardGrid } from "./SensorCardGrid";
import { SensorOverlayChart } from "./SensorOverlayChart";

interface CsvState {
  fileName: string;
  text: string;
}

function mergeSettingsForSession(base: LogReplaySettings | null, session: LogSession): LogReplaySettings {
  const defaults = createDefaultLogReplaySettings(session.sensors);
  if (!base) return defaults;

  const existingBySource = new Map(base.sensors.map((sensor) => [sensor.sourceKey, sensor]));
  return {
    ...defaults,
    ...base,
    sensors: defaults.sensors.map((sensor) => existingBySource.get(sensor.sourceKey) ?? sensor),
    gps: { ...defaults.gps, ...base.gps },
    accel: {
      linear: { ...defaults.accel.linear, ...base.accel.linear },
      angular: { ...defaults.accel.angular, ...base.accel.angular },
    },
    matlab: { ...defaults.matlab, ...base.matlab },
  };
}

function validKeys(keys: readonly string[], session: LogSession): string[] {
  return keys.filter((key) => session.columns.includes(key));
}

export function LogReplayTab() {
  const [rawSession, setRawSession] = useState<LogSession | null>(null);
  const [csvState, setCsvState] = useState<CsvState | null>(null);
  const [settings, setSettings] = useState<LogReplaySettings>(() => createDefaultLogReplaySettings());
  const [error, setError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [activeTab, setActiveTab] = useState<LogReplayInnerTab>("dashboard");
  const [playback, setPlayback] = useState<PlaybackState>({ currentTimeMs: 0, isPlaying: false, speed: 1 });
  const [cardKeys, setCardKeys] = useState<string[]>([...DEFAULT_CARD_KEYS]);
  const [overlayKeys, setOverlayKeys] = useState<string[]>([...DEFAULT_OVERLAY_KEYS]);

  const session = useMemo(() => (rawSession ? applyLogReplaySettings(rawSession, settings) : null), [rawSession, settings]);
  const events = useMemo(() => (session ? extractLogEvents(session, settings) : []), [session, settings]);
  const currentSample = useMemo(
    () => (session ? findNearestSample(session.samples, playback.currentTimeMs) : undefined),
    [session, playback.currentTimeMs],
  );

  useEffect(() => {
    let mounted = true;
    loadStoredLogReplayState().then((stored) => {
      if (!mounted) return;
      if (stored) {
        try {
          const parsed = parseEmuLogCsv(stored.csv.text, stored.csv.fileName);
          setCsvState(stored.csv);
          setRawSession(parsed);
          setSettings(mergeSettingsForSession(stored.settings, parsed));
          setActiveTab(stored.ui.activeTab);
          setOverlayKeys(stored.ui.overlayKeys.length ? stored.ui.overlayKeys : validKeys(DEFAULT_OVERLAY_KEYS, parsed).slice(0, 4));
          setCardKeys(stored.ui.cardKeys.length ? stored.ui.cardKeys : validKeys(DEFAULT_CARD_KEYS, parsed));
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : "저장된 CSV를 다시 읽지 못했습니다.");
        }
      }
      setHydrated(true);
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!session || !playback.isPlaying) return undefined;

    const startedAt = performance.now();
    const startTime = playback.currentTimeMs;
    const timer = window.setInterval(() => {
      const elapsed = (performance.now() - startedAt) * playback.speed;
      setPlayback((current) => {
        const nextTime = Math.min(session.summary.durationMs, startTime + elapsed);
        return { ...current, currentTimeMs: nextTime, isPlaying: nextTime < session.summary.durationMs };
      });
    }, 100);

    return () => window.clearInterval(timer);
  }, [session, playback.isPlaying, playback.currentTimeMs, playback.speed]);

  useEffect(() => {
    if (!hydrated || !csvState) return;
    saveStoredLogReplayState({
      csv: csvState,
      settings,
      ui: { activeTab, overlayKeys, cardKeys },
    }).catch((caught) => {
      setError(caught instanceof Error ? caught.message : "로그 자동 저장에 실패했습니다.");
    });
  }, [activeTab, cardKeys, csvState, hydrated, overlayKeys, settings]);

  function handleFileText(fileName: string, text: string) {
    if (!fileName.toLowerCase().endsWith(".csv")) {
      setError("CSV 파일만 업로드할 수 있습니다.");
      return;
    }

    try {
      const parsed = parseEmuLogCsv(text, fileName);
      const nextSettings = mergeSettingsForSession(null, parsed);
      setCsvState({ fileName, text });
      setRawSession(parsed);
      setSettings(nextSettings);
      setError(null);
      setPlayback({ currentTimeMs: 0, isPlaying: false, speed: 1 });
      setActiveTab("dashboard");
      setCardKeys(validKeys(DEFAULT_CARD_KEYS, parsed));
      setOverlayKeys(validKeys(DEFAULT_OVERLAY_KEYS, parsed).slice(0, 4));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "CSV를 읽지 못했습니다.");
    }
  }

  function toggleCardKey(key: string) {
    setCardKeys((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  }

  function seek(timeMs: number) {
    setPlayback((current) => ({ ...current, currentTimeMs: timeMs }));
  }

  function clearSavedReplay() {
    clearStoredLogReplayState();
    setRawSession(null);
    setCsvState(null);
    setError(null);
    setPlayback({ currentTimeMs: 0, isPlaying: false, speed: 1 });
    setActiveTab("dashboard");
  }

  return (
    <div className="log-replay">
      <CsvLogUploader session={session} error={error} onFileText={handleFileText} onClear={clearSavedReplay} />
      {session && currentSample ? (
        <div className="log-replay-workspace">
          <PlaybackControls session={session} playback={playback} events={events} onPlaybackChange={setPlayback} onSeek={seek} />
          <LogReplayInnerTabs activeTab={activeTab} onTabChange={setActiveTab} />
          {activeTab === "dashboard" ? (
            <LogDashboard session={session} sample={currentSample} selectedKeys={cardKeys} events={events} currentTimeMs={playback.currentTimeMs} />
          ) : null}
          {activeTab === "overlay" ? (
            <SensorOverlayChart
              session={session}
              selectedKeys={overlayKeys}
              currentTimeMs={playback.currentTimeMs}
              onSelectedKeysChange={setOverlayKeys}
              onSeek={seek}
            />
          ) : null}
          {activeTab === "gps" ? <GpsTrackPanel session={session} currentSample={currentSample} gpsConfig={settings.gps} /> : null}
          {activeTab === "gg" ? <GGDiagram session={session} currentSample={currentSample} accelConfig={settings.accel} /> : null}
          {activeTab === "events" ? <EventStrip session={session} events={events} currentTimeMs={playback.currentTimeMs} onSeek={seek} /> : null}
          {activeTab === "sensors" ? (
            <SensorCardGrid session={session} sample={currentSample} selectedKeys={cardKeys} onToggleKey={toggleCardKey} />
          ) : null}
          {activeTab === "sensors" ? <LogSensorsTable session={session} sample={currentSample} /> : null}
          {activeTab === "settings" ? <LogSettingsPanel settings={settings} onSettingsChange={setSettings} /> : null}
        </div>
      ) : null}
    </div>
  );
}
