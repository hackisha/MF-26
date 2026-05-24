import { useEffect, useMemo, useState } from "react";
import type { Calibration, VehicleProfile } from "../domain/types";
import { useSessionStore } from "../state/sessionStore";

function resolveProfile(profiles: VehicleProfile[], profileId: string): VehicleProfile | null {
  return profiles.find((profile) => profile.id === profileId) ?? profiles[0] ?? null;
}

function calibrationDetail(calibration: Calibration): string {
  if (calibration.type === "scaleOffset") return `scale ${calibration.scale}, offset ${calibration.offset}`;
  if (calibration.type === "invert") return "inverted";
  return "none";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nextRevision(currentRevision: string): string {
  return `${currentRevision}-json-${new Date().toISOString()}`;
}

export function SettingsView() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const session = useSessionStore((state) => state.session);
  const sourceCsv = useSessionStore((state) => state.sourceCsv);
  const updateProfile = useSessionStore((state) => state.updateProfile);
  const activeProfile = useMemo(() => resolveProfile(profiles, selectedProfileId), [profiles, selectedProfileId]);
  const [profileJson, setProfileJson] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeProfile) return;
    setProfileJson(JSON.stringify(activeProfile, null, 2));
  }, [activeProfile]);

  function applyProfileJson() {
    setStatus(null);
    setError(null);

    if (!activeProfile) {
      setError("No active profile is available.");
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(profileJson);
    } catch (parseError) {
      setError(`Invalid JSON: ${parseError instanceof Error ? parseError.message : "could not parse profile."}`);
      return;
    }

    if (!isRecord(parsed)) {
      setError("Profile JSON must be an object.");
      return;
    }

    if (parsed.id !== activeProfile.id) {
      setError(`Profile id must remain ${activeProfile.id}.`);
      return;
    }

    const updatedProfile = {
      ...parsed,
      revision: nextRevision(activeProfile.revision)
    } as VehicleProfile;
    const rebuiltLoadedSession = Boolean(session && sourceCsv && session.profileId === activeProfile.id);

    updateProfile(updatedProfile);
    setProfileJson(JSON.stringify(updatedProfile, null, 2));
    setStatus(
      rebuiltLoadedSession
        ? "Profile applied and loaded session rebuilt from source CSV."
        : "Profile applied."
    );
  }

  if (!activeProfile) {
    return (
      <section className="empty-state">
        <h2>No profile available</h2>
        <p>Profile settings will appear after a vehicle profile is loaded.</p>
      </section>
    );
  }

  const channels = Object.values(activeProfile.channels);

  return (
    <section className="settings-view">
      <div className="settings-grid">
        <div className="panel">
          <h2>Profile Metadata</h2>
          <dl className="settings-metadata">
            <div>
              <dt>Name</dt>
              <dd>{activeProfile.name}</dd>
            </div>
            <div>
              <dt>ID</dt>
              <dd>{activeProfile.id}</dd>
            </div>
            <div>
              <dt>Revision</dt>
              <dd>{activeProfile.revision}</dd>
            </div>
            <div>
              <dt>Channels</dt>
              <dd>{channels.length.toLocaleString()}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <h2>Advanced Profile JSON</h2>
          <label className="json-editor-label" htmlFor="active-profile-json">
            Active profile JSON
          </label>
          <textarea
            id="active-profile-json"
            className="json-editor"
            value={profileJson}
            onChange={(event) => setProfileJson(event.target.value)}
            spellCheck={false}
          />
          <div className="settings-actions">
            <button type="button" onClick={applyProfileJson}>
              Apply JSON
            </button>
            {status && <p className="status-message">{status}</p>}
            {error && <p className="form-error">{error}</p>}
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>Channel Mapping</h2>
        <div className="table-scroll">
          <table className="data-table settings-channel-table">
            <thead>
              <tr>
                <th>Display</th>
                <th>ID</th>
                <th>Source Columns</th>
                <th>Unit</th>
                <th>Calibration</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((channel) => (
                <tr key={channel.id}>
                  <td>{channel.displayName}</td>
                  <td>{channel.id}</td>
                  <td>{channel.sourceColumns.join(", ")}</td>
                  <td>{channel.unit}</td>
                  <td>{channel.calibration.type}</td>
                  <td>{calibrationDetail(channel.calibration)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
