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

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function validateCalibrationShape(channelId: string, calibration: Record<string, unknown>): string | null {
  if (calibration.type === "identity" || calibration.type === "invert") return null;

  if (calibration.type === "scaleOffset") {
    if (typeof calibration.scale !== "number" || !Number.isFinite(calibration.scale)) {
      return `Channel ${channelId} scaleOffset calibration needs a finite scale.`;
    }
    if (typeof calibration.offset !== "number" || !Number.isFinite(calibration.offset)) {
      return `Channel ${channelId} scaleOffset calibration needs a finite offset.`;
    }
    return null;
  }

  return `Channel ${channelId} calibration type must be identity, invert, or scaleOffset.`;
}

function validateRuleCondition(ruleId: string, condition: unknown): string | null {
  if (!isRecord(condition)) return `Rule ${ruleId} conditions must be objects.`;
  if (typeof condition.channelId !== "string" || condition.channelId.trim() === "") {
    return `Rule ${ruleId} condition channelId must be a string.`;
  }
  if (![">", ">=", "<", "<=", "==", "!="].includes(String(condition.op))) {
    return `Rule ${ruleId} condition op is invalid.`;
  }
  if (typeof condition.value !== "number" || !Number.isFinite(condition.value)) {
    return `Rule ${ruleId} condition value must be finite.`;
  }
  return null;
}

function validateConditionArray(ruleId: string, key: "all" | "any", value: unknown): string | null {
  if (value === undefined) return null;
  if (!Array.isArray(value)) return `Rule ${ruleId} ${key} must be an array.`;
  for (const condition of value) {
    const conditionError = validateRuleCondition(ruleId, condition);
    if (conditionError) return conditionError;
  }
  return null;
}

function validateRuleShape(rule: unknown, index: number): string | null {
  if (!isRecord(rule)) return `Rule ${index + 1} must be an object.`;
  const ruleId = typeof rule.id === "string" && rule.id.trim() ? rule.id : `${index + 1}`;
  if (typeof rule.id !== "string" || rule.id.trim() === "") return `Rule ${index + 1} needs a string id.`;
  if (typeof rule.name !== "string") return `Rule ${ruleId} needs a name.`;
  if (rule.severity !== "info" && rule.severity !== "warning" && rule.severity !== "critical") {
    return `Rule ${ruleId} severity must be info, warning, or critical.`;
  }
  const allError = validateConditionArray(ruleId, "all", rule.all);
  if (allError) return allError;
  const anyError = validateConditionArray(ruleId, "any", rule.any);
  if (anyError) return anyError;
  if (typeof rule.minDurationSec !== "number" || !Number.isFinite(rule.minDurationSec)) {
    return `Rule ${ruleId} minDurationSec must be finite.`;
  }
  if (typeof rule.description !== "string") return `Rule ${ruleId} description must be a string.`;
  if (!Array.isArray(rule.views) || !rule.views.every((view) => ["summary", "diagnostics", "graph", "behavior", "map", "report"].includes(String(view)))) {
    return `Rule ${ruleId} views must be valid view ids.`;
  }
  return null;
}

function validateProfileShape(value: Record<string, unknown>): string | null {
  if (typeof value.name !== "string" || value.name.trim() === "") return "Profile name must be a non-empty string.";
  if (typeof value.revision !== "string") return "Profile revision must be a string.";
  if (!isRecord(value.channels) || Object.keys(value.channels).length === 0) return "Profile channels must be a non-empty object.";
  if (!Array.isArray(value.rules)) return "Profile rules must be an array.";
  if (!Array.isArray(value.overlays)) return "Profile overlays must be an array.";
  if (!isStringArray(value.reportSections)) return "Profile reportSections must be an array of strings.";

  for (const [channelId, channel] of Object.entries(value.channels)) {
    if (!isRecord(channel)) return `Channel ${channelId} must be an object.`;
    if (typeof channel.id !== "string" || channel.id.trim() === "") return `Channel ${channelId} needs a string id.`;
    if (typeof channel.displayName !== "string") return `Channel ${channelId} needs a displayName.`;
    if (!isStringArray(channel.sourceColumns)) return `Channel ${channelId} sourceColumns must be an array of strings.`;
    if (typeof channel.unit !== "string") return `Channel ${channelId} unit must be a string.`;
    if (!isRecord(channel.calibration) || typeof channel.calibration.type !== "string") {
      return `Channel ${channelId} calibration must include a type.`;
    }
    const calibrationError = validateCalibrationShape(channelId, channel.calibration);
    if (calibrationError) return calibrationError;
    if (typeof channel.defaultVisible !== "boolean") return `Channel ${channelId} defaultVisible must be boolean.`;
    if (typeof channel.color !== "string") return `Channel ${channelId} color must be a string.`;
  }

  for (const [ruleIndex, rule] of value.rules.entries()) {
    const ruleError = validateRuleShape(rule, ruleIndex);
    if (ruleError) return ruleError;
  }

  for (const [overlayIndex, overlay] of value.overlays.entries()) {
    if (!isRecord(overlay)) return `Overlay ${overlayIndex + 1} must be an object.`;
    if (typeof overlay.id !== "string" || overlay.id.trim() === "") return `Overlay ${overlayIndex + 1} needs a string id.`;
    if (typeof overlay.name !== "string") return `Overlay ${overlayIndex + 1} needs a name.`;
    if (!isStringArray(overlay.channelIds)) return `Overlay ${overlay.id} channelIds must be an array of strings.`;
    if (overlay.mode !== "separateAxes" && overlay.mode !== "normalized") {
      return `Overlay ${overlay.id} mode must be separateAxes or normalized.`;
    }
  }

  return null;
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

    const shapeError = validateProfileShape(parsed);
    if (shapeError) {
      setError(shapeError);
      return;
    }

    const updatedProfile = {
      ...parsed,
      revision: nextRevision(activeProfile.revision)
    } as VehicleProfile;
    const rebuiltLoadedSession = Boolean(session && sourceCsv && session.profileId === activeProfile.id);

    try {
      updateProfile(updatedProfile);
      setProfileJson(JSON.stringify(updatedProfile, null, 2));
      setStatus(
        rebuiltLoadedSession
          ? "Profile applied and loaded session rebuilt from source CSV."
          : "Profile applied."
      );
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "Profile JSON could not be applied.");
    }
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
