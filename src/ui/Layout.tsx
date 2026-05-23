import { useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";
import { Tabs, tabButtonId, tabPanelId, type TabId } from "./Tabs";
import { TimeSeriesView } from "./TimeSeriesView";

const placeholders: Record<Exclude<TabId, "summary" | "diagnostics" | "time-series">, string> = {
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
      <section
        className="content-area"
        role="tabpanel"
        id={tabPanelId(activeTab)}
        aria-labelledby={tabButtonId(activeTab)}
      >
        {activeTab === "summary" && <SummaryView />}
        {activeTab === "diagnostics" && <DiagnosticsView />}
        {activeTab === "time-series" && <TimeSeriesView />}
        {activeTab !== "summary" && activeTab !== "diagnostics" && activeTab !== "time-series" && (
          <section className="empty-state">{placeholders[activeTab]}</section>
        )}
      </section>
    </>
  );
}
