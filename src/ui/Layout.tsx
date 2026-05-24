import { lazy, Suspense, useState } from "react";
import { DiagnosticsView } from "./DiagnosticsView";
import { PopoutButton } from "./PopoutButton";
import { SummaryView } from "./SummaryView";
import { Tabs, tabButtonId, tabPanelId, tabs, type TabId } from "./Tabs";

const TimeSeriesView = lazy(() => import("./TimeSeriesView").then((module) => ({ default: module.TimeSeriesView })));
const BehaviorView = lazy(() => import("./BehaviorView").then((module) => ({ default: module.BehaviorView })));
const MapLapView = lazy(() => import("./MapLapView").then((module) => ({ default: module.MapLapView })));
const ReportView = lazy(() => import("./ReportView").then((module) => ({ default: module.ReportView })));
const SettingsView = lazy(() => import("./SettingsView").then((module) => ({ default: module.SettingsView })));

export function routeForTab(tabId: TabId): string {
  return tabId === "summary" ? "/" : `/${tabId}`;
}

function tabFromRoute(): TabId {
  const route = window.location.hash.startsWith("#/")
    ? window.location.hash.slice(1)
    : `${window.location.pathname}${window.location.search}`;
  const tabId = route.replace(/^\//, "").split(/[?#]/)[0] || "summary";
  return tabs.some((tab) => tab.id === tabId) ? (tabId as TabId) : "summary";
}

function replaceTabRoute(tabId: TabId) {
  const route = routeForTab(tabId);
  const nextUrl = window.location.protocol === "file:" ? `#${route}` : route;
  window.history.replaceState(null, "", nextUrl);
}

export function Layout() {
  const [activeTab, setActiveTab] = useState<TabId>(() => tabFromRoute());

  function handleTabChange(tabId: TabId) {
    setActiveTab(tabId);
    replaceTabRoute(tabId);
  }

  return (
    <>
      <Tabs activeTab={activeTab} onChange={handleTabChange} />
      <div className="content-toolbar" aria-label="Active view controls">
        <PopoutButton route={routeForTab(activeTab)} />
      </div>
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
