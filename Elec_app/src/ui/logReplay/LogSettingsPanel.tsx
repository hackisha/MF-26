import { useState } from "react";
import type { LogReplaySettings } from "../../domain/logSettingsTypes";

interface LogSettingsPanelProps {
  settings: LogReplaySettings;
  onSettingsChange: (settings: LogReplaySettings) => void;
}

function numberOrFallback(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function LogSettingsPanel({ settings, onSettingsChange }: LogSettingsPanelProps) {
  const [derivedLabel, setDerivedLabel] = useState("");
  const [derivedExpression, setDerivedExpression] = useState("");

  function updateSensorScale(sourceKey: string, value: string) {
    onSettingsChange({
      ...settings,
      sensors: settings.sensors.map((sensor) =>
        sensor.sourceKey === sourceKey ? { ...sensor, scale: numberOrFallback(value, sensor.scale) } : sensor,
      ),
    });
  }

  function updateGps(key: "latitudeKey" | "longitudeKey" | "speedKey" | "jumpThresholdMeters", value: string) {
    onSettingsChange({
      ...settings,
      gps: {
        ...settings.gps,
        [key]: key === "jumpThresholdMeters" ? numberOrFallback(value, settings.gps.jumpThresholdMeters) : value,
      },
    });
  }

  function addDerivedSensor() {
    const label = derivedLabel.trim();
    const expression = derivedExpression.trim();
    if (!label || !expression) return;
    onSettingsChange({
      ...settings,
      derivedSensors: [
        ...settings.derivedSensors,
        {
          id: label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `derived-${settings.derivedSensors.length + 1}`,
          label,
          expression,
          unit: "",
          group: "custom",
          precision: 2,
          color: "#ffc300",
          fallback: "empty",
          enabled: true,
        },
      ],
    });
    setDerivedLabel("");
    setDerivedExpression("");
  }

  return (
    <section className="panel log-settings-panel">
      <div className="section-heading">
        <h3>로그 해석 설정</h3>
        <span>배율, GPS, 자유수식</span>
      </div>
      <div className="settings-grid">
        <div className="settings-box">
          <h4>센서 배율</h4>
          {settings.sensors.slice(0, 12).map((sensor) => (
            <label key={sensor.id} className="field">
              {sensor.label} 배율
              <input
                aria-label={`${sensor.label} 배율`}
                type="number"
                step="0.001"
                value={sensor.scale}
                onChange={(event) => updateSensorScale(sensor.sourceKey, event.target.value)}
              />
            </label>
          ))}
        </div>
        <div className="settings-box">
          <h4>GPS</h4>
          <label className="field">
            위도 컬럼
            <input value={settings.gps.latitudeKey} onChange={(event) => updateGps("latitudeKey", event.target.value)} />
          </label>
          <label className="field">
            경도 컬럼
            <input value={settings.gps.longitudeKey} onChange={(event) => updateGps("longitudeKey", event.target.value)} />
          </label>
          <label className="field">
            속도 컬럼
            <input value={settings.gps.speedKey} onChange={(event) => updateGps("speedKey", event.target.value)} />
          </label>
          <label className="field">
            GPS 점프 필터(m)
            <input
              type="number"
              value={settings.gps.jumpThresholdMeters}
              onChange={(event) => updateGps("jumpThresholdMeters", event.target.value)}
            />
          </label>
        </div>
        <div className="settings-box">
          <h4>자유수식 센서</h4>
          <label className="field">
            새 센서 이름
            <input aria-label="새 센서 이름" value={derivedLabel} onChange={(event) => setDerivedLabel(event.target.value)} />
          </label>
          <label className="field">
            새 센서 수식
            <input
              aria-label="새 센서 수식"
              value={derivedExpression}
              onChange={(event) => setDerivedExpression(event.target.value)}
              placeholder="RPM / 1000"
            />
          </label>
          <button type="button" onClick={addDerivedSensor}>
            수식 센서 추가
          </button>
          <div className="derived-list">
            {settings.derivedSensors.map((sensor) => (
              <span key={sensor.id}>
                {sensor.label}: {sensor.expression}
              </span>
            ))}
          </div>
        </div>
        <div className="settings-box">
          <h4>ADXL / ADU</h4>
          <p>ADXL 계열은 선형 가속도 G-G 분석에 사용하고, adu_x/y/z는 각가속도 센서로 분리합니다.</p>
          <code>
            linear: {settings.accel.linear.xKey}, {settings.accel.linear.yKey}, {settings.accel.linear.zKey}
          </code>
          <code>
            angular: {settings.accel.angular.xKey}, {settings.accel.angular.yKey}, {settings.accel.angular.zKey}
          </code>
        </div>
      </div>
    </section>
  );
}
