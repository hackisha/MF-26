import { useEffect, useMemo, useState } from "react";
import { DEFAULT_CARD_KEYS, DEFAULT_OVERLAY_KEYS } from "../../domain/logReplayColumns";
import { extractLogEvents, findNearestSample } from "../../domain/logReplayAnalysis";
import { parseEmuLogCsv } from "../../domain/logReplayParser";
import type { LogSession, PlaybackState } from "../../domain/logReplayTypes";
import { CsvLogUploader } from "./CsvLogUploader";
import { EventStrip } from "./EventStrip";
import { GGDiagram } from "./GGDiagram";
import { GpsTrackPanel } from "./GpsTrackPanel";
import { PlaybackControls } from "./PlaybackControls";
import { SensorCardGrid } from "./SensorCardGrid";
import { SensorOverlayChart } from "./SensorOverlayChart";

export function LogReplayTab() {
  const [session, setSession] = useState<LogSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playback, setPlayback] = useState<PlaybackState>({ currentTimeMs: 0, isPlaying: false, speed: 1 });
  const [cardKeys, setCardKeys] = useState<string[]>([...DEFAULT_CARD_KEYS]);
  const [overlayKeys, setOverlayKeys] = useState<string[]>([...DEFAULT_OVERLAY_KEYS]);

  const events = useMemo(() => (session ? extractLogEvents(session) : []), [session]);
  const currentSample = useMemo(
    () => (session ? findNearestSample(session.samples, playback.currentTimeMs) : undefined),
    [session, playback.currentTimeMs],
  );

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

  function handleFileText(fileName: string, text: string) {
    if (!fileName.toLowerCase().endsWith(".csv")) {
      setError("CSV 파일만 업로드할 수 있습니다.");
      return;
    }

    try {
      const parsed = parseEmuLogCsv(text, fileName);
      setSession(parsed);
      setError(null);
      setPlayback({ currentTimeMs: 0, isPlaying: false, speed: 1 });
      setCardKeys(DEFAULT_CARD_KEYS.filter((key) => parsed.columns.includes(key)));
      setOverlayKeys(DEFAULT_OVERLAY_KEYS.filter((key) => parsed.columns.includes(key)).slice(0, 4));
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

  return (
    <div className="log-replay">
      <CsvLogUploader session={session} error={error} onFileText={handleFileText} />
      {session && currentSample ? (
        <div className="log-replay-workspace">
          <PlaybackControls session={session} playback={playback} events={events} onPlaybackChange={setPlayback} onSeek={seek} />
          <div className="log-replay-layout">
            <div className="log-replay-layout__main">
              <SensorOverlayChart
                session={session}
                selectedKeys={overlayKeys}
                currentTimeMs={playback.currentTimeMs}
                onSelectedKeysChange={setOverlayKeys}
                onSeek={seek}
              />
              <div className="log-visual-grid">
                <GpsTrackPanel session={session} currentSample={currentSample} />
                <GGDiagram session={session} currentSample={currentSample} />
              </div>
            </div>
            <aside className="log-replay-layout__rail">
              <SensorCardGrid session={session} sample={currentSample} selectedKeys={cardKeys} onToggleKey={toggleCardKey} />
              <EventStrip session={session} events={events} currentTimeMs={playback.currentTimeMs} onSeek={seek} />
            </aside>
          </div>
        </div>
      ) : null}
    </div>
  );
}
