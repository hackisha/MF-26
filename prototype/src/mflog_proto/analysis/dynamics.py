"""Vehicle dynamics summary metrics for log sessions."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class DynamicsSummary:
    sample_count: int
    peak_lateral_g: float | None
    peak_longitudinal_g: float | None
    peak_combined_g: float | None
    g_limit_radius: float
    g_limit_exceedance_count: int
    g_utilization_percent: float | None
    max_abs_yaw_rate_dps: float | None
    yaw_response_ratio: float | None
    balance_label: str


def compute_dynamics_summary(
    *,
    timestamps_seconds: Sequence[float],
    sensors: Mapping[str, Sequence[float | None]],
    g_limit_radius: float = 1.0,
    wheelbase_m: float = 1.6,
    steering_ratio: float = 1.0,
    steering_channel: str = "Auto",
) -> DynamicsSummary:
    sample_count = len(timestamps_seconds)
    ax = _series(sensors, ("AX_CORRECTED_G", "ax"), sample_count)
    ay = _series(sensors, ("AY_CORRECTED_G", "ay"), sample_count)
    yaw_rate = _series(sensors, ("yaw rate", "gz_dps", "GZ_RAW_DPS"), sample_count)
    speed_kph = _series(sensors, ("VSS / GPS speed", "GPS speed", "VSS", "VSS_kmh"), sample_count)
    steering = _steering_series(sensors, steering_channel, sample_count)

    combined = np.sqrt(np.square(_nan_to_zero(ax)) + np.square(_nan_to_zero(ay)))
    finite_combined = combined[np.isfinite(combined)]
    peak_combined = _max_or_none(finite_combined)
    limit = max(float(g_limit_radius), 0.1)
    exceedance_count = int(np.count_nonzero(finite_combined > limit))

    yaw_response_ratio = _yaw_response_ratio(
        measured_yaw_rate_dps=yaw_rate,
        speed_kph=speed_kph,
        steering_angle_deg=steering,
        wheelbase_m=wheelbase_m,
        steering_ratio=steering_ratio,
    )

    return DynamicsSummary(
        sample_count=sample_count,
        peak_lateral_g=_max_abs_or_none(ay),
        peak_longitudinal_g=_max_abs_or_none(ax),
        peak_combined_g=peak_combined,
        g_limit_radius=limit,
        g_limit_exceedance_count=exceedance_count,
        g_utilization_percent=(
            None if peak_combined is None else peak_combined / limit * 100.0
        ),
        max_abs_yaw_rate_dps=_max_abs_or_none(yaw_rate),
        yaw_response_ratio=yaw_response_ratio,
        balance_label=_balance_label(yaw_response_ratio),
    )


def _series(
    sensors: Mapping[str, Sequence[float | None]],
    names: tuple[str, ...],
    sample_count: int,
) -> np.ndarray:
    for name in names:
        if name in sensors:
            return _as_float_array(sensors[name], sample_count)
    return np.full(sample_count, np.nan)


def _steering_series(
    sensors: Mapping[str, Sequence[float | None]],
    steering_channel: str,
    sample_count: int,
) -> np.ndarray:
    if steering_channel != "Auto" and steering_channel in sensors:
        return _as_float_array(sensors[steering_channel], sample_count)

    direct_names = (
        "steering angle",
        "Steering angle",
        "STEERING_ANGLE",
        "STR_ANGLE",
        "SAS_Angle",
    )
    for name in direct_names:
        if name in sensors:
            return _as_float_array(sensors[name], sample_count)

    for name, values in sensors.items():
        lowered = name.lower()
        if "steer" in lowered or "str_angle" in lowered:
            return _as_float_array(values, sample_count)
    return np.full(sample_count, np.nan)


def _as_float_array(values: Sequence[float | None], sample_count: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.size == sample_count:
        return array
    resized = np.full(sample_count, np.nan)
    limit = min(sample_count, array.size)
    if limit:
        resized[:limit] = array[:limit]
    return resized


def _nan_to_zero(values: np.ndarray) -> np.ndarray:
    return np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


def _max_abs_or_none(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return float(np.max(np.abs(finite)))


def _max_or_none(values: np.ndarray) -> float | None:
    if values.size == 0:
        return None
    return float(np.max(values))


def _yaw_response_ratio(
    *,
    measured_yaw_rate_dps: np.ndarray,
    speed_kph: np.ndarray,
    steering_angle_deg: np.ndarray,
    wheelbase_m: float,
    steering_ratio: float,
) -> float | None:
    if wheelbase_m <= 0 or steering_ratio <= 0:
        return None

    speed_mps = speed_kph / 3.6
    road_wheel_angle_rad = np.radians(steering_angle_deg / steering_ratio)
    ideal_yaw_rate_dps = (
        speed_mps * np.tan(road_wheel_angle_rad) / wheelbase_m * 180.0 / math.pi
    )
    mask = (
        np.isfinite(measured_yaw_rate_dps)
        & np.isfinite(ideal_yaw_rate_dps)
        & (np.abs(ideal_yaw_rate_dps) > 1.0)
    )
    if not np.any(mask):
        return None

    ratios = measured_yaw_rate_dps[mask] / ideal_yaw_rate_dps[mask]
    finite = ratios[np.isfinite(ratios)]
    if finite.size == 0:
        return None
    return float(np.median(finite))


def _balance_label(yaw_response_ratio: float | None) -> str:
    if yaw_response_ratio is None:
        return "steering data unavailable"
    if yaw_response_ratio < 0.75:
        return "understeer tendency"
    if yaw_response_ratio > 1.25:
        return "oversteer tendency"
    return "neutral yaw response"
