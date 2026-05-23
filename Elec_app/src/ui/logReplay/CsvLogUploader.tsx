import type { ChangeEvent } from "react";
import { DEFAULT_CARD_KEYS } from "../../domain/logReplayColumns";
import type { LogSession } from "../../domain/logReplayTypes";

interface CsvLogUploaderProps {
  session: LogSession | null;
  error: string | null;
  onFileText: (fileName: string, text: string) => void;
  onClear?: () => void;
}

export function CsvLogUploader({ session, error, onFileText, onClear }: CsvLogUploaderProps) {
  const missingRecommended = session ? DEFAULT_CARD_KEYS.filter((key) => !session.columns.includes(key)) : [];
  const invalidEntries = session ? Object.entries(session.summary.invalidCounts).filter(([, count]) => count > 0) : [];
  const recognizedSensors = session
    ? session.sensors.filter((sensor) => sensor.key !== "Timestamp" && (sensor.type === "number" || sensor.type === "state"))
    : [];

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      onFileText(file.name, "");
      return;
    }

    onFileText(file.name, await file.text());
    input.value = "";
  }

  return (
    <section className="panel log-uploader" data-testid="log-uploader">
      <div className="log-uploader__intro">
        <div>
          <h2>EMU 로그 재생</h2>
          <p>EMU-LOGGER CSV를 업로드하면 주행 데이터를 시간축에 맞춰 재생합니다. 마지막 업로드는 브라우저에 저장됩니다.</p>
        </div>
        <div className="log-uploader__actions">
          {session && onClear ? (
            <button type="button" onClick={onClear}>
              저장 로그 지우기
            </button>
          ) : null}
          <label className="file-picker">
            <input aria-label="CSV 로그 파일" type="file" accept=".csv,text/csv" onChange={handleChange} />
            CSV 업로드
          </label>
        </div>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      {session ? (
        <>
          <div className="log-summary-grid">
            <span>파일: {session.fileName}</span>
            <span>행: {session.summary.rowCount.toLocaleString()}</span>
            <span>길이: {(session.summary.durationMs / 1000).toFixed(1)}s</span>
            <span>추정 주기: {session.summary.estimatedSampleRateHz?.toFixed(1) ?? "-"}Hz</span>
            <span>시작: {session.summary.startLabel || "-"}</span>
            <span>종료: {session.summary.endLabel || "-"}</span>
            <span>인식 센서: {recognizedSensors.length.toLocaleString()}개</span>
            <span>누락 권장: {missingRecommended.length ? missingRecommended.join(", ") : "없음"}</span>
          </div>
          <div className="log-detail-list">
            <div>
              <strong>센서 컬럼</strong>
              <p>{recognizedSensors.map((sensor) => sensor.key).join(", ") || "-"}</p>
            </div>
            <div>
              <strong>빈 값 오류</strong>
              <p>{invalidEntries.map(([key, count]) => `${key} ${count}`).join(", ") || "없음"}</p>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
