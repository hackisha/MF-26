import { useRef } from "react";

export type TabId =
  | "summary"
  | "diagnostics"
  | "playback"
  | "time-series"
  | "behavior"
  | "map-lap"
  | "report"
  | "settings";

export const tabs: Array<{ id: TabId; label: string }> = [
  { id: "summary", label: "Summary" },
  { id: "diagnostics", label: "Log Diagnostics" },
  { id: "playback", label: "CSV Playback" },
  { id: "time-series", label: "Time-Series Graph" },
  { id: "behavior", label: "Vehicle Behavior" },
  { id: "map-lap", label: "Map / Lap" },
  { id: "report", label: "Report" },
  { id: "settings", label: "Settings" }
];

export function tabButtonId(tabId: TabId): string {
  return `analysis-tab-${tabId}`;
}

export function tabPanelId(tabId: TabId): string {
  return `analysis-panel-${tabId}`;
}

export function Tabs({ activeTab, onChange }: { activeTab: TabId; onChange: (tab: TabId) => void }) {
  const tabRefs = useRef<Record<TabId, HTMLButtonElement | null>>({
    summary: null,
    diagnostics: null,
    playback: null,
    "time-series": null,
    behavior: null,
    "map-lap": null,
    report: null,
    settings: null
  });

  function activateTab(tabId: TabId) {
    onChange(tabId);
    tabRefs.current[tabId]?.focus();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    const currentIndex = tabs.findIndex((tab) => tab.id === activeTab);
    if (currentIndex < 0) return;

    if (event.key === "ArrowRight") {
      event.preventDefault();
      activateTab(tabs[(currentIndex + 1) % tabs.length].id);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      activateTab(tabs[(currentIndex - 1 + tabs.length) % tabs.length].id);
    } else if (event.key === "Home") {
      event.preventDefault();
      activateTab(tabs[0].id);
    } else if (event.key === "End") {
      event.preventDefault();
      activateTab(tabs[tabs.length - 1].id);
    }
  }

  return (
    <div className="tabs" role="tablist" aria-label="Analysis views">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          id={tabButtonId(tab.id)}
          ref={(element) => {
            tabRefs.current[tab.id] = element;
          }}
          type="button"
          role="tab"
          className={activeTab === tab.id ? "tab tab-active" : "tab"}
          aria-selected={activeTab === tab.id}
          aria-controls={tabPanelId(tab.id)}
          tabIndex={activeTab === tab.id ? 0 : -1}
          onKeyDown={handleKeyDown}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
