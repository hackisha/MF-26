import type { LogReplayInnerTab } from "../../storage/logReplayStore";

const TABS: Array<{ id: LogReplayInnerTab; label: string }> = [
  { id: "overview", label: "전체 분석" },
  { id: "gps", label: "GPS / 랩" },
  { id: "motion", label: "가속도 / 자세" },
  { id: "powertrain", label: "엔진 / 전장" },
  { id: "events", label: "이벤트" },
  { id: "sensors", label: "센서 목록" },
  { id: "settings", label: "설정" },
];

interface LogReplayInnerTabsProps {
  activeTab: LogReplayInnerTab;
  onTabChange: (tab: LogReplayInnerTab) => void;
}

export function LogReplayInnerTabs({ activeTab, onTabChange }: LogReplayInnerTabsProps) {
  return (
    <nav className="log-inner-tabs" aria-label="분석 카테고리">
      {TABS.map((tab) => (
        <button key={tab.id} className={activeTab === tab.id ? "active" : ""} type="button" onClick={() => onTabChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
