import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import type { AnalysisSession, NumericLogRow, SensorChannel, VehicleProfile } from "../domain/types";
import { useSessionStore } from "../state/sessionStore";

const playbackSpeeds = [0.25, 0.5, 1, 2, 4, 8];
const tickMs = 100;

type ChannelReadout = {
  channel: SensorChannel;
  value: number;
};

function activeProfile(profiles: VehicleProfile[], profileId: string): VehicleProfile | null {
  return profiles.find((profile) => profile.id === profileId) ?? profiles[0] ?? null;
}

function finiteValue(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function clampIndex(index: number, rows: NumericLogRow[]): number {
  return Math.min(rows.length - 1, Math.max(0, index));
}

function nearestRowIndex(rows: NumericLogRow[], timeSec: number): number {
  if (rows.length === 0) return -1;
  if (timeSec <= rows[0].timestampSec) return 0;
  if (timeSec >= rows[rows.length - 1].timestampSec) return rows.length - 1;

  let low = 0;
  let high = rows.length - 1;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (rows[mid].timestampSec < timeSec) low = mid + 1;
    else high = mid;
  }

  const after = rows[low];
  const before = rows[low - 1];
  return Math.abs(after.timestampSec - timeSec) < Math.abs(timeSec - before.timestampSec) ? low : low - 1;
}

function formatSeconds(value: number | null | undefined): string {
  return finiteValue(value) ? `${value.toFixed(2)} s` : "n/a";
}

function formatValue(value: number, channel: SensorChannel): string {
  if (channel.unit === "rpm" || channel.unit === "gear") return value.toFixed(0);
  return value.toFixed(2);
}

function channelReadouts(row: NumericLogRow | null, profile: VehicleProfile | null): ChannelReadout[] {
  if (!row || !profile) return [];

  return Object.values(profile.channels)
    .filter((channel) => channel.defaultVisible)
    .map((channel) => {
      const value = row.values[channel.id];
      return finiteValue(value) ? { channel, value } : null;
    })
    .filter((entry): entry is ChannelReadout => entry !== null);
}

function timeBounds(session: AnalysisSession | null): { startSec: number | null; endSec: number | null } {
  const rows = session?.log.rows ?? [];
  return {
    startSec: rows[0]?.timestampSec ?? null,
    endSec: rows.at(-1)?.timestampSec ?? null
  };
}

export function PlaybackView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);
  const currentTimeSec = useSessionStore((state) => state.currentTimeSec);
  const setCurrentTimeSec = useSessionStore((state) => state.setCurrentTimeSec);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const rows = session?.log.rows ?? [];
  const { startSec, endSec } = timeBounds(session);
  const effectiveTimeSec = currentTimeSec ?? startSec ?? 0;
  const currentIndex = nearestRowIndex(rows, effectiveTimeSec);
  const currentRow = currentIndex >= 0 ? rows[currentIndex] : null;
  const profile = session ? activeProfile(profiles, session.profileId) : null;
  const readouts = useMemo(() => channelReadouts(currentRow, profile), [currentRow, profile]);
  const durationSec = finiteValue(startSec) && finiteValue(endSec) ? endSec - startSec : null;

  useEffect(() => {
    setIsPlaying(false);
  }, [session]);

  useEffect(() => {
    if (!isPlaying || !finiteValue(startSec) || !finiteValue(endSec) || endSec <= startSec) return;

    const intervalId = window.setInterval(() => {
      const baseTimeSec = useSessionStore.getState().currentTimeSec ?? startSec;
      const nextTimeSec = Math.min(endSec, baseTimeSec + speed * (tickMs / 1000));
      setCurrentTimeSec(nextTimeSec);
      if (nextTimeSec >= endSec) setIsPlaying(false);
    }, tickMs);

    return () => window.clearInterval(intervalId);
  }, [endSec, isPlaying, setCurrentTimeSec, speed, startSec]);

  if (!session) {
    return <section className="empty-state">Open a CSV log to replay the run.</section>;
  }

  function seekToIndex(index: number) {
    const row = rows[clampIndex(index, rows)];
    if (row) setCurrentTimeSec(row.timestampSec);
  }

  function handleTimelineChange(event: ChangeEvent<HTMLInputElement>) {
    const nextTimeSec = Number(event.currentTarget.value);
    if (Number.isFinite(nextTimeSec)) setCurrentTimeSec(nextTimeSec);
  }

  function handleSpeedChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextSpeed = Number(event.currentTarget.value);
    if (Number.isFinite(nextSpeed)) setSpeed(nextSpeed);
  }

  function togglePlayback() {
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }

    if (finiteValue(startSec) && finiteValue(endSec) && effectiveTimeSec >= endSec) {
      setCurrentTimeSec(startSec);
    }
    setIsPlaying(true);
  }

  function stopPlayback() {
    setIsPlaying(false);
    if (finiteValue(startSec)) setCurrentTimeSec(startSec);
  }

  return (
    <section className="playback-view" aria-label="CSV playback">
      <div className="playback-grid">
        <section className="playback-panel playback-controls-panel">
          <div className="playback-heading">
            <h2>CSV Playback</h2>
            <p>Shared time cursor for replaying the loaded log across analysis views.</p>
          </div>

          <div className="playback-metrics" aria-label="Playback metrics">
            <Metric label="Current Time" value={formatSeconds(effectiveTimeSec)} />
            <Metric label="Sample" value={currentIndex >= 0 ? `${currentIndex + 1} / ${rows.length}` : "n/a"} />
            <Metric label="Duration" value={formatSeconds(durationSec)} />
            <Metric label="Speed" value={`${speed}x`} />
          </div>

          <div className="playback-timeline">
            <input
              type="range"
              min={startSec ?? 0}
              max={endSec ?? 0}
              step="0.01"
              value={Math.min(endSec ?? effectiveTimeSec, Math.max(startSec ?? effectiveTimeSec, effectiveTimeSec))}
              aria-label="Playback timeline"
              onChange={handleTimelineChange}
            />
            <div className="timeline-meta">
              <span>{formatSeconds(startSec)}</span>
              <strong>{currentRow ? `Row ${currentRow.index + 1}` : "No row"}</strong>
              <span>{formatSeconds(endSec)}</span>
            </div>
          </div>

          <div className="playback-transport" aria-label="Playback controls">
            <button type="button" aria-label="Previous sample" disabled={currentIndex <= 0} onClick={() => seekToIndex(currentIndex - 1)}>
              Back
            </button>
            <button type="button" aria-label={isPlaying ? "Pause CSV log" : "Play CSV log"} onClick={togglePlayback}>
              {isPlaying ? "Pause" : "Play"}
            </button>
            <button type="button" aria-label="Stop CSV log" onClick={stopPlayback}>
              Stop
            </button>
            <button
              type="button"
              aria-label="Next sample"
              disabled={currentIndex < 0 || currentIndex >= rows.length - 1}
              onClick={() => seekToIndex(currentIndex + 1)}
            >
              Next
            </button>
            <label className="playback-speed-field">
              <span>Speed</span>
              <select aria-label="Playback speed" value={speed} onChange={handleSpeedChange}>
                {playbackSpeeds.map((playbackSpeed) => (
                  <option key={playbackSpeed} value={playbackSpeed}>
                    {playbackSpeed}x
                  </option>
                ))}
              </select>
            </label>
          </div>
        </section>

        <section className="playback-panel">
          <div className="playback-heading">
            <h2>Current Sample</h2>
            <p>{currentRow ? `${formatSeconds(currentRow.timestampSec)} from ${session.log.fileName}` : "No finite timestamp sample."}</p>
          </div>

          <div className="table-scroll playback-table-scroll">
            <table className="data-table playback-value-table" aria-label="Current sample values">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Value</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {readouts.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="table-empty">
                      No visible finite channel values at the current sample.
                    </td>
                  </tr>
                ) : (
                  readouts.map(({ channel, value }) => (
                    <tr key={channel.id}>
                      <td>{channel.displayName}</td>
                      <td>{formatValue(value, channel)}</td>
                      <td>{channel.unit || "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="playback-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
