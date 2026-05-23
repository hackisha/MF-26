import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

export function DiagnosticsView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to inspect log diagnostics.</section>;

  return (
    <section className="panel">
      <h2>Log Diagnostics</h2>
      <p className="muted">{session.diagnostics.length.toLocaleString()} findings</p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Finding</th>
              <th>Detail</th>
              <th>Channels</th>
            </tr>
          </thead>
          <tbody>
            {session.diagnostics.length === 0 ? (
              <tr>
                <td colSpan={4} className="table-empty">
                  No diagnostic findings detected.
                </td>
              </tr>
            ) : (
              session.diagnostics.map((finding) => (
                <tr key={finding.id}>
                  <td>
                    <SeverityBadge severity={finding.severity} />
                  </td>
                  <td>{finding.title}</td>
                  <td>{finding.detail}</td>
                  <td>{finding.affectedChannelIds.join(", ")}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
