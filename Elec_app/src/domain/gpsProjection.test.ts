import { describe, expect, test } from "vitest";
import { projectGpsTrack } from "./gpsProjection";
import type { LogSample } from "./logReplayTypes";

describe("projectGpsTrack", () => {
  test("projects latitude and longitude into local meter coordinates and filters jumps", () => {
    const samples: LogSample[] = [
      { rowIndex: 0, timeMs: 0, values: { Latitude: 37, Longitude: 127 } },
      { rowIndex: 1, timeMs: 100, values: { Latitude: 37.0001, Longitude: 127.0001 } },
      { rowIndex: 2, timeMs: 200, values: { Latitude: 38, Longitude: 128 } },
    ];

    const projected = projectGpsTrack(samples, {
      latitudeKey: "Latitude",
      longitudeKey: "Longitude",
      speedKey: "GPS_Speed_KPH",
      jumpThresholdMeters: 100,
      smoothing: "off",
    });

    expect(projected.points).toHaveLength(2);
    expect(projected.points[1].xMeters).toBeGreaterThan(0);
    expect(projected.points[1].yMeters).toBeGreaterThan(0);
    expect(projected.bounds.widthMeters).toBeGreaterThan(0);
  });
});
