import { evaluateFormula } from "./formulaEngine";
import type { LogReplaySettings, SensorConfig } from "./logSettingsTypes";
import type { LogSample, LogSession, SensorDefinition, SensorValue } from "./logReplayTypes";

function numeric(value: SensorValue): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function applySensorValue(value: SensorValue, config: SensorConfig): SensorValue {
  const number = numeric(value);
  if (number === undefined) return value;
  return number * config.scale + config.offset;
}

function sensorFromConfig(config: SensorConfig): SensorDefinition {
  return {
    key: config.id,
    label: config.label,
    unit: config.unit,
    type: "number",
    recommendedCard: config.showInDashboard,
    recommendedOverlay: config.showInOverlay,
  };
}

export function applyLogReplaySettings(session: LogSession, settings: LogReplaySettings): LogSession {
  const sensorMap = new Map(settings.sensors.map((config) => [config.sourceKey, config]));
  const outputSensors = session.sensors.map((sensor) => {
    const config = sensorMap.get(sensor.key);
    return config ? sensorFromConfig(config) : sensor;
  });
  const outputColumns = [...session.columns];
  const previousDerivedValues: Record<string, SensorValue> = {};

  const samples: LogSample[] = session.samples.map((sample) => {
    const values: Record<string, SensorValue> = { ...sample.values };
    settings.sensors.forEach((config) => {
      if (config.sourceKey in values) values[config.id] = applySensorValue(values[config.sourceKey], config);
      config.aliases.forEach((alias) => {
        if (!(config.id in values) && alias in values) values[config.id] = applySensorValue(values[alias], config);
      });
    });

    settings.derivedSensors
      .filter((derived) => derived.enabled)
      .forEach((derived) => {
        try {
          values[derived.id] = evaluateFormula(derived.expression, values);
        } catch {
          if (derived.fallback === "zero") values[derived.id] = 0;
          else if (derived.fallback === "previous") values[derived.id] = previousDerivedValues[derived.id] ?? null;
          else values[derived.id] = null;
        }
        previousDerivedValues[derived.id] = values[derived.id];
      });

    return { ...sample, values };
  });

  settings.derivedSensors
    .filter((derived) => derived.enabled)
    .forEach((derived) => {
      if (!outputColumns.includes(derived.id)) outputColumns.push(derived.id);
      if (!outputSensors.some((sensor) => sensor.key === derived.id)) {
        outputSensors.push({
          key: derived.id,
          label: derived.label,
          unit: derived.unit,
          type: "number",
          recommendedOverlay: true,
        });
      }
    });

  return {
    ...session,
    columns: outputColumns,
    sensors: outputSensors,
    samples,
  };
}
