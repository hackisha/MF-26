import { useEffect, useRef, type ChangeEvent } from "react";
import { fileNameFromPath, hydrateSessionSnapshot, startSessionSelectionSync, useSessionStore } from "./state/sessionStore";
import { Layout } from "./ui/Layout";

export default function App() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const session = useSessionStore((state) => state.session);
  const setSelectedProfileId = useSessionStore((state) => state.setSelectedProfileId);
  const openCsv = useSessionStore((state) => state.openCsv);
  const csvInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cleanup: () => void = () => undefined;
    let active = true;

    void hydrateSessionSnapshot()
      .catch(() => undefined)
      .finally(() => {
        if (!active) return;
        cleanup = startSessionSelectionSync();
      });

    return () => {
      active = false;
      cleanup();
    };
  }, []);

  async function handleOpenCsv() {
    if (window.mfLogAnalyzer?.openCsv) {
      await openCsv();
      return;
    }

    csvInputRef.current?.click();
  }

  async function handleCsvFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;

    await openCsv({
      filePath: file.name,
      text: await file.text()
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="topbar-title">
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
          <input
            ref={csvInputRef}
            className="sr-only"
            type="file"
            accept=".csv,text/csv"
            aria-label="CSV file picker"
            onChange={(event) => void handleCsvFileChange(event)}
          />
          <button type="button" onClick={() => void handleOpenCsv()}>
            Open CSV
          </button>
        </div>
      </header>
      <Layout />
    </main>
  );
}
