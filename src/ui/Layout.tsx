import { lazy, Suspense, useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";
import { Tabs, tabButtonId, tabPanelId, type TabId } from "./Tabs";

const TimeSeriesView = lazy(() => import("./TimeSeriesView").then((module) => ({ default: module.TimeSeriesView })));
const BehaviorView = lazy(() => import("./BehaviorView").then((module) => ({ default: module.BehaviorView })));
const MapLapView = lazy(() => import("./MapLapView").then((module) => ({ default: module.MapLapView })));
const ReportView = lazy(() => import("./ReportView").then((module) => ({ default: module.ReportView })));
const SettingsView = lazy(() => import("./SettingsView").then((module) => ({ default: module.SettingsView })));

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
        {activeTab === "report" && (
          <Suspense fallback={<section className="empty-state">Loading report view...</section>}>
            <ReportView />
          </Suspense>
        )}
        {activeTab === "settings" && (
          <Suspense fallback={<section className="empty-state">Loading settings view...</section>}>
            <SettingsView />
          </Suspense>
        )}
      </section>
    </>
  );
}
