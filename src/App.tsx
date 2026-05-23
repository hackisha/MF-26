import { useEffect } from "react";
import { fileNameFromPath, hydrateSessionSnapshot, useSessionStore } from "./state/sessionStore";

export default function App() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const session = useSessionStore((state) => state.session);
  const setSelectedProfileId = useSessionStore((state) => state.setSelectedProfileId);
  const openCsv = useSessionStore((state) => state.openCsv);

  useEffect(() => {
    void hydrateSessionSnapshot();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MF Log Analyzer</h1>
          <p>
            {session
              ? `Loaded ${fileNameFromPath(session.filePath)}`
              : "Open a CSV log to inspect vehicle health, behavior, and report outputs."}
          </p>
        </div>
        <div className="topbar-actions" aria-label="Session controls">
          <label>
            <span>Profile</span>
            <select value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void openCsv()}>
            Open CSV
          </button>
        </div>
      </header>
      <section className="empty-state">
        {session ? (
          <>
            <h2>{session.log.fileName}</h2>
            <p>
              {session.log.rows.length.toLocaleString()} rows, {session.diagnostics.length.toLocaleString()} diagnostics,{" "}
              {session.events.length.toLocaleString()} events.
            </p>
          </>
        ) : (
          "No log loaded."
        )}
      </section>
    </main>
  );
}
