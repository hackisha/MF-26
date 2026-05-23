import type { GpsConfig } from "./logSettingsTypes";
import type { LogSample } from "./logReplayTypes";

export interface ProjectedGpsPoint {
  sample: LogSample;
  xMeters: number;
  yMeters: number;
  speed: number;
}

export interface ProjectedGpsTrack {
  points: ProjectedGpsPoint[];
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
    widthMeters: number;
    heightMeters: number;
  };
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function haversineMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6_371_000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function projectGpsTrack(samples: LogSample[], config: GpsConfig): ProjectedGpsTrack {
  const raw = samples
    .map((sample) => ({
      sample,
      lat: numberValue(sample.values[config.latitudeKey]),
      lon: numberValue(sample.values[config.longitudeKey]),
      speed: numberValue(sample.values[config.speedKey]) ?? numberValue(sample.values.VSS_kmh) ?? Number.NaN,
    }))
    .filter((point): point is { sample: LogSample; lat: number; lon: number; speed: number } => point.lat !== undefined && point.lon !== undefined);

  if (raw.length === 0) {
    return { points: [], bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0, widthMeters: 0, heightMeters: 0 } };
  }

  const origin = raw[0];
  const projected: ProjectedGpsPoint[] = [];
  let lastAccepted = origin;

  raw.forEach((point, index) => {
    if (index > 0) {
      const jump = haversineMeters(lastAccepted.lat, lastAccepted.lon, point.lat, point.lon);
      if (jump > config.jumpThresholdMeters) return;
      lastAccepted = point;
    }
    const yMeters = (point.lat - origin.lat) * 111_320;
    const xMeters = (point.lon - origin.lon) * 111_320 * Math.cos((origin.lat * Math.PI) / 180);
    projected.push({ sample: point.sample, xMeters, yMeters, speed: point.speed });
  });

  const xs = projected.map((point) => point.xMeters);
  const ys = projected.map((point) => point.yMeters);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    points: projected,
    bounds: {
      minX,
      maxX,
      minY,
      maxY,
      widthMeters: Math.max(1, maxX - minX),
      heightMeters: Math.max(1, maxY - minY),
    },
  };
}
