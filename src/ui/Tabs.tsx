export type TabId = "summary" | "diagnostics" | "time-series" | "behavior" | "map-lap" | "report" | "settings";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "summary", label: "Summary" },
  { id: "diagnostics", label: "Log Diagnostics" },
  { id: "time-series", label: "Time-Series Graph" },
  { id: "behavior", label: "Vehicle Behavior" },
  { id: "map-lap", label: "Map / Lap" },
  { id: "report", label: "Report" },
  { id: "settings", label: "Settings" }
];

export function Tabs({ activeTab, onChange }: { activeTab: TabId; onChange: (tab: TabId) => void }) {
  return (
    <nav className="tabs" aria-label="Analysis views">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={activeTab === tab.id ? "tab tab-active" : "tab"}
          aria-current={activeTab === tab.id ? "page" : undefined}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
