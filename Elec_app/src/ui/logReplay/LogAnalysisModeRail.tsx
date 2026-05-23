import { Activity, Gauge, ListChecks, SlidersHorizontal, TableProperties, Zap } from "lucide-react";
import type { LogReplayInnerTab } from "../../storage/logReplayStore";

type LogAnalysisMode = Exclude<LogReplayInnerTab, "gps">;

export const LOG_ANALYSIS_MODES: Array<{
  id: LogAnalysisMode;
  label: string;
  description: string;
  icon: typeof Gauge;
}> = [
  { id: "overview", label: "한눈에 보기", description: "전체 주행 상황", icon: Gauge },
  { id: "motion", label: "차량 거동", description: "G-G / 가속도 / ADU", icon: Activity },
  { id: "powertrain", label: "파워트레인", description: "RPM / 속도 / 전장", icon: Zap },
  { id: "events", label: "이벤트", description: "이상 감지 기록", icon: ListChecks },
  { id: "sensors", label: "센서 테이블", description: "현재 값 / 원본 컬럼", icon: TableProperties },
  { id: "settings", label: "설정", description: "보정 / 수식 / 기준", icon: SlidersHorizontal },
];

interface LogAnalysisModeRailProps {
  activeMode: LogReplayInnerTab;
  onModeChange: (mode: LogReplayInnerTab) => void;
}

export function LogAnalysisModeRail({ activeMode, onModeChange }: LogAnalysisModeRailProps) {
  return (
    <aside className="analysis-mode-rail" data-testid="analysis-mode-rail" aria-label="로그 분석 모드">
      <div className="analysis-mode-rail__head">
        <span>분석 보드</span>
      </div>
      <div className="analysis-mode-rail__items">
        {LOG_ANALYSIS_MODES.map((mode) => {
          const Icon = mode.icon;
          return (
            <button
              key={mode.id}
              type="button"
              className={activeMode === mode.id ? "active" : ""}
              aria-current={activeMode === mode.id ? "page" : undefined}
              onClick={() => onModeChange(mode.id)}
            >
              <Icon size={16} aria-hidden="true" />
              <span>
                <strong>{mode.label}</strong>
                <small>{mode.description}</small>
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
