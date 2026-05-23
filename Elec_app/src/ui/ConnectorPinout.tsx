import type { Component, Measurement, Note } from "../domain/types";

interface ConnectorPinoutProps {
  components: Component[];
  notes: Note[];
  measurements: Measurement[];
}

export function ConnectorPinout({ components, notes, measurements }: ConnectorPinoutProps) {
  const connectors = components.filter((component) => (component.confirmedRole ?? component.autoRole) === "connector");
  const selected = connectors[0] ?? null;

  return (
    <section className="panel">
      <h2>커넥터 Pinout</h2>
      {selected ? (
        <table className="pinout-table">
          <caption>{selected.alias || selected.rawName}</caption>
          <thead>
            <tr>
              <th>Pin</th>
              <th>Net</th>
              <th>ECU</th>
              <th>대상</th>
              <th>메모</th>
              <th>측정</th>
            </tr>
          </thead>
          <tbody>
            {selected.pins.map((pin) => {
              const noteCount = notes.filter((note) => note.targetId === pin.id).length;
              const lastMeasurement = measurements.find((measurement) => measurement.pinId === pin.id);
              return (
                <tr key={pin.id}>
                  <td>{pin.number}</td>
                  <td>{pin.label ?? "-"}</td>
                  <td>-</td>
                  <td>-</td>
                  <td>{noteCount || "-"}</td>
                  <td>{lastMeasurement?.measuredValue ?? "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="muted">분류된 커넥터가 없습니다.</p>
      )}
    </section>
  );
}
