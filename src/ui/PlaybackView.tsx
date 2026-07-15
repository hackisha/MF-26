import { useMemo } from "react";
import { useSessionStore } from "../state/sessionStore";
import {
  PlaybackControls,
  activeProfile,
  channelReadouts,
  formatPlaybackValue,
  formatSeconds,
  nearestRowIndex,
  timeBounds
} from "./PlaybackControls";

export function PlaybackView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);
  const currentTimeSec = useSessionStore((state) => state.currentTimeSec);
  const rows = session?.log.rows ?? [];
  const { startSec } = timeBounds(session);
  const effectiveTimeSec = currentTimeSec ?? startSec ?? 0;
  const currentIndex = nearestRowIndex(rows, effectiveTimeSec);
  const currentRow = currentIndex >= 0 ? rows[currentIndex] : null;
  const profile = session ? activeProfile(profiles, session.profileId) : null;
  const readouts = useMemo(() => channelReadouts(currentRow, profile), [currentRow, profile]);

  if (!session) {
    return <section className="empty-state">Open a CSV log to replay the run.</section>;
  }

  return (
    <section className="playback-view" aria-label="CSV playback">
      <div className="playback-grid">
        <PlaybackControls />

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
                      <td>{formatPlaybackValue(value, channel)}</td>
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
