import { useMemo, useState } from "react";
import { buildReportHtml } from "../domain/reportHtml";
import { summarizeLog } from "../domain/summary";
import type { VehicleProfile } from "../domain/types";
import { useSessionStore } from "../state/sessionStore";

function resolveProfile(profiles: VehicleProfile[], profileId: string): VehicleProfile | null {
  return profiles.find((profile) => profile.id === profileId) ?? null;
}

export function ReportView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeProfile = useMemo(() => {
    const sessionProfile = session ? resolveProfile(profiles, session.profileId) : null;
    return sessionProfile ?? resolveProfile(profiles, selectedProfileId) ?? profiles[0] ?? null;
  }, [profiles, selectedProfileId, session]);

  const html = useMemo(() => {
    if (!session || !activeProfile) return "";
    const summary = summarizeLog(session.log, session.events);
    return buildReportHtml({
      log: session.log,
      profile: activeProfile,
      events: session.events,
      diagnostics: session.diagnostics,
      summary
    });
  }, [activeProfile, session]);

  async function saveReport() {
    setStatus(null);
    setError(null);

    const saveHtmlReport = window.mfLogAnalyzer?.saveHtmlReport;
    if (!saveHtmlReport) {
      setError("Desktop save API is unavailable.");
      return;
    }

    try {
      const savedPath = await saveHtmlReport(html);
      if (savedPath) {
        setStatus(`Saved report to ${savedPath}.`);
      } else {
        setStatus("Save cancelled.");
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save HTML report.");
    }
  }

  if (!session) {
    return (
      <section className="empty-state">
        <h2>No log loaded</h2>
        <p>Open a CSV log to preview and save an HTML report.</p>
      </section>
    );
  }

  return (
    <section className="report-view">
      <div className="view-toolbar">
        <button type="button" onClick={saveReport}>
          Save HTML
        </button>
        <p className="toolbar-note">
          Previewing {session.log.fileName} with {activeProfile?.name ?? session.profileId}.
        </p>
      </div>
      {status && <p className="status-message">{status}</p>}
      {error && <p className="form-error">{error}</p>}
      <iframe className="report-preview" title="HTML report preview" srcDoc={html} sandbox="" />
    </section>
  );
}
