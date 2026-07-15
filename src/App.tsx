import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { fileNameFromPath, hydrateSessionSnapshot, startSessionSelectionSync, useSessionStore } from "./state/sessionStore";
import { Layout } from "./ui/Layout";
import { PlaybackTicker } from "./ui/PlaybackControls";

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown CSV load error.";
}

export default function App() {
  const profiles = useSessionStore((state) => state.profiles);
  const selectedProfileId = useSessionStore((state) => state.selectedProfileId);
  const session = useSessionStore((state) => state.session);
  const setSelectedProfileId = useSessionStore((state) => state.setSelectedProfileId);
  const openCsv = useSessionStore((state) => state.openCsv);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const [csvLoadError, setCsvLoadError] = useState<string | null>(null);
  const [isCsvLoading, setIsCsvLoading] = useState(false);

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

  useEffect(() => {
    return window.mfLogAnalyzer?.onOpenCsvMenu?.(() => {
      void handleOpenCsv();
    });
  });

  async function handleOpenCsv() {
    if (window.mfLogAnalyzer?.openCsv) {
      setCsvLoadError(null);
      setIsCsvLoading(true);
      try {
        await openCsv();
      } catch (error) {
        setCsvLoadError(`Could not open CSV: ${messageFromError(error)}`);
      } finally {
        setIsCsvLoading(false);
      }
      return;
    }

    csvInputRef.current?.click();
  }

  async function handleCsvFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;

    setCsvLoadError(null);
    setIsCsvLoading(true);
    try {
      await openCsv({
        filePath: file.name,
        text: await file.text()
      });
    } catch (error) {
      setCsvLoadError(`Could not open CSV: ${messageFromError(error)}`);
    } finally {
      setIsCsvLoading(false);
    }
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
          <button type="button" aria-busy={isCsvLoading} disabled={isCsvLoading} onClick={() => void handleOpenCsv()}>
            Open CSV
          </button>
        </div>
      </header>
      {csvLoadError ? (
        <section className="session-message session-message-error" role="alert">
          {csvLoadError}
        </section>
      ) : null}
      {isCsvLoading ? (
        <section className="session-message" role="status">
          Loading CSV...
        </section>
      ) : null}
      <PlaybackTicker />
      <Layout />
    </main>
  );
}
