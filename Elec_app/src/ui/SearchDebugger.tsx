import { useMemo, useState } from "react";
import { traceFromPin } from "../domain/connectivity";
import type { Component, NetGraph } from "../domain/types";
import { matchesComponent } from "../utils/search";

interface SearchDebuggerProps {
  components: Component[];
  graph: NetGraph;
}

export function SearchDebugger({ components, graph }: SearchDebuggerProps) {
  const [query, setQuery] = useState("");
  const matches = useMemo(
    () => components.filter((component) => matchesComponent(component, query)).slice(0, 10),
    [components, query]
  );
  const selected = matches[0];
  const trace = selected?.pins[0] ? traceFromPin(graph, components, selected.pins[0].id) : [];

  return (
    <section className="panel">
      <h2>검색 디버거</h2>
      <label className="field">
        검색
        <input
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
          placeholder="ECU Gray pin 12, Fuel Pump, GND"
        />
      </label>
      {matches.length > 0 ? (
        <>
          <h3>연결 경로</h3>
          <div className="trace-list">
            {trace.map((component) => (
              <div className="trace-chip" key={component.id}>
                {component.alias || component.rawName}
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">검색어를 입력하면 연결 경로를 표시합니다.</p>
      )}
    </section>
  );
}
