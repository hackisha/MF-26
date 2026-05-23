export default function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MF Log Analyzer</h1>
          <p>Open a CSV log to inspect vehicle health, behavior, and report outputs.</p>
        </div>
        <button type="button">Open CSV</button>
      </header>
      <section className="empty-state">No log loaded.</section>
    </main>
  );
}
