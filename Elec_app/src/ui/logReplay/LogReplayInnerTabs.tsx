import type { LogReplayInnerTab } from "../../storage/logReplayStore";

const TABS: Array<{ id: LogReplayInnerTab; label: string }> = [
  { id: "dashboard", label: "대시보드" },
  { id: "overlay", label: "오버랩" },
  { id: "gps", label: "GPS" },
  { id: "gg", label: "G-G / 가속도" },
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
    <nav className="log-inner-tabs" aria-label="로그 재생 화면">
      {TABS.map((tab) => (
        <button key={tab.id} className={activeTab === tab.id ? "active" : ""} type="button" onClick={() => onTabChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
