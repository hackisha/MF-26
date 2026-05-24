import { lazy, Suspense, useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";
import { Tabs, tabButtonId, tabPanelId, type TabId } from "./Tabs";

const TimeSeriesView = lazy(() => import("./TimeSeriesView").then((module) => ({ default: module.TimeSeriesView })));
const BehaviorView = lazy(() => import("./BehaviorView").then((module) => ({ default: module.BehaviorView })));
const MapLapView = lazy(() => import("./MapLapView").then((module) => ({ default: module.MapLapView })));

const placeholders: Record<Exclude<TabId, "summary" | "diagnostics" | "time-series" | "behavior" | "map-lap">, string> = {
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
        {activeTab === "time-series" && (
          <Suspense fallback={<section className="empty-state">Loading graph...</section>}>
            <TimeSeriesView />
          </Suspense>
        )}
        {activeTab === "behavior" && (
          <Suspense fallback={<section className="empty-state">Loading behavior view...</section>}>
            <BehaviorView />
          </Suspense>
        )}
        {activeTab === "map-lap" && (
          <Suspense fallback={<section className="empty-state">Loading map / lap view...</section>}>
            <MapLapView />
          </Suspense>
        )}
        {activeTab !== "summary" &&
          activeTab !== "diagnostics" &&
          activeTab !== "time-series" &&
          activeTab !== "behavior" &&
          activeTab !== "map-lap" && (
          <section className="empty-state">{placeholders[activeTab]}</section>
        )}
      </section>
    </>
  );
}
