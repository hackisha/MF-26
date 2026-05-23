import { useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";
import { Tabs, type TabId } from "./Tabs";

const placeholders: Record<Exclude<TabId, "summary" | "diagnostics">, string> = {
  "time-series": "Time-series view is next.",
  behavior: "Vehicle behavior view is next.",
  "map-lap": "Map / Lap view is next.",
  report: "Report view is next.",
  settings: "Settings view is next."
};

export function Layout() {
  const [activeTab, setActiveTab] = useState<TabId>("summary");

  return (
    <>
      <Tabs activeTab={activeTab} onChange={setActiveTab} />
      <section className="content-area">
        {activeTab === "summary" && <SummaryView />}
        {activeTab === "diagnostics" && <DiagnosticsView />}
        {activeTab !== "summary" && activeTab !== "diagnostics" && (
          <section className="empty-state">{placeholders[activeTab]}</section>
        )}
      </section>
    </>
  );
}
