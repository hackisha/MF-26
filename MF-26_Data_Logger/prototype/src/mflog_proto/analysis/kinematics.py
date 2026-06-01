"""Kinematic path estimation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class IdealPathResult:
    latitude: list[float | None]
    longitude: list[float | None]
    status: str

    @property
    def valid_count(self) -> int:
        return sum(
            _is_valid_latitude(latitude_value) and _is_valid_longitude(longitude_value)
            for latitude_value, longitude_value in zip(self.latitude, self.longitude)
        )


def compute_ideal_path(
    *,
    timestamps: Sequence[float],
    speed_kph: Sequence[float | None],
    steering_angle_deg: Sequence[float | None],
    latitude: Sequence[float | None],
    longitude: Sequence[float | None],
    wheelbase_m: float,
    steering_ratio: float,
) -> IdealPathResult:
    if not timestamps:
        return IdealPathResult([], [], "waiting for time")
    if not speed_kph:
        return IdealPathResult([], [], "waiting for speed")
    if not steering_angle_deg:
        return IdealPathResult([], [], "waiting for steering")
    if wheelbase_m <= 0:
        return IdealPathResult([], [], "invalid wheelbase")
    if steering_ratio <= 0:
        return IdealPathResult([], [], "invalid steering ratio")

    start_index = _first_valid_gps_index(latitude, longitude)
    if start_index is None:
        return IdealPathResult([], [], "waiting for GPS")

    sample_count = len(timestamps)
    latitudes: list[float | None] = [None for _index in range(sample_count)]
    longitudes: list[float | None] = [None for _index in range(sample_count)]

    origin_latitude = float(latitude[start_index])
    origin_longitude = float(longitude[start_index])
    meters_per_degree_latitude = 111_320.0
    meters_per_degree_longitude = max(
        1e-6,
        meters_per_degree_latitude * math.cos(math.radians(origin_latitude)),
    )
    yaw = _initial_heading_radians(
        latitude=latitude,
        longitude=longitude,
        start_index=start_index,
        meters_per_degree_latitude=meters_per_degree_latitude,
        meters_per_degree_longitude=meters_per_degree_longitude,
    )
    x_m = 0.0
    y_m = 0.0

    latitudes[start_index] = origin_latitude
    longitudes[start_index] = origin_longitude

    for index in range(start_index, sample_count - 1):
        dt = max(0.0, float(timestamps[index + 1]) - float(timestamps[index]))
        speed_mps = max(0.0, _safe_float(_sequence_value(speed_kph, index)) / 3.6)
        road_wheel_angle = math.radians(
            _safe_float(_sequence_value(steering_angle_deg, index)) / steering_ratio
        )
        yaw_rate = speed_mps * math.tan(road_wheel_angle) / wheelbase_m

        x_m += speed_mps * math.cos(yaw) * dt
        y_m += speed_mps * math.sin(yaw) * dt
        yaw += yaw_rate * dt

        latitudes[index + 1] = origin_latitude + y_m / meters_per_degree_latitude
        longitudes[index + 1] = origin_longitude + x_m / meters_per_degree_longitude

    return IdealPathResult(latitudes, longitudes, "ready")


def _first_valid_gps_index(
    latitude: Sequence[float | None],
    longitude: Sequence[float | None],
) -> int | None:
    for index, (latitude_value, longitude_value) in enumerate(zip(latitude, longitude)):
        if _is_valid_latitude(latitude_value) and _is_valid_longitude(longitude_value):
            return index
    return None


def _initial_heading_radians(
    *,
    latitude: Sequence[float | None],
    longitude: Sequence[float | None],
    start_index: int,
    meters_per_degree_latitude: float,
    meters_per_degree_longitude: float,
) -> float:
    origin_latitude = float(latitude[start_index])
    origin_longitude = float(longitude[start_index])
    for index in range(start_index + 1, min(len(latitude), len(longitude))):
        if not _is_valid_latitude(latitude[index]) or not _is_valid_longitude(longitude[index]):
            continue
        dx = (float(longitude[index]) - origin_longitude) * meters_per_degree_longitude
        dy = (float(latitude[index]) - origin_latitude) * meters_per_degree_latitude
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            return math.atan2(dy, dx)
    return 0.0


def _sequence_value(values: Sequence[float | None], index: int) -> float | None:
    if index < len(values):
        return values[index]
    return values[-1]


def _safe_float(value: float | None) -> float:
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def _is_valid_latitude(value: float | None) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and -90.0 <= numeric <= 90.0 and abs(numeric) > 1e-12


def _is_valid_longitude(value: float | None) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and -180.0 <= numeric <= 180.0 and abs(numeric) > 1e-12
