"""Prototype channel mapping rules for known MF log channels."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class MappingState(str, Enum):
    MATCHED = "Matched"
    AUTO_MATCHED = "Auto-matched"
    NEEDS_REVIEW = "Needs review"
    MISSING = "Missing"
    IGNORED = "Ignored"
    DERIVED = "Derived"


@dataclass(frozen=True)
class ChannelMapping:
    channel_id: str
    state: MappingState
    source_column: str | None = None
    confidence: float = 0.0


KNOWN_ALIASES: dict[str, tuple[str, ...]] = {
    "TIME": ("Timestamp",),
    "RPM": ("RPM",),
    "TPS_PERCENT": ("TPS_percent", "TPS"),
    "GPS_LATITUDE_DEG": ("Latitude",),
    "GPS_LONGITUDE_DEG": ("Longitude",),
    "GPS_SPEED_KPH": ("GPS_Speed_KPH",),
    "GPS_SATELLITES": ("Satellites",),
    "GPS_ALTITUDE_M": ("Altitude_m",),
    "GPS_HEADING_DEG": ("Heading_deg",),
    "VSS_KMH": ("VSS_kmh",),
    "BATTERY_V": ("Batt_V",),
    "MAP_KPA": ("MAP_kPa",),
    "IAT_C": ("IAT_C",),
    "CLT_C": ("CLT_C",),
    "OIL_PRESSURE_BAR": ("OilPressure_bar",),
    "FUEL_PRESSURE_BAR": ("FuelPressure_bar",),
    "GEAR": ("Gear",),
    "GYRO_X_DPS": ("gx_dps",),
    "GYRO_Y_DPS": ("gy_dps",),
    "GYRO_Z_DPS": ("gz_dps",),
    "ADU_AX_G": ("ADU_ax_g",),
    "ADU_AY_G": ("ADU_ay_g",),
    "ADU_AZ_G": ("ADU_az_g",),
    "SUSP_FL_MM": ("Susp_FL_mm",),
    "SUSP_FR_MM": ("Susp_FR_mm",),
    "SUSP_RL_MM": ("Susp_RL_mm",),
    "SUSP_RR_MM": ("Susp_RR_mm",),
    "PITOT_DP_PA": ("Pitot_dP_Pa",),
    "PITOT_AIRSPEED_KPH": ("Pitot_AirSpeed_KPH",),
    "STEERING_ANGLE_DEG": ("SteeringAngle_deg",),
    "EOT_IN": ("EOT_IN", "OilTemp_C"),
    "EOT_OUT": ("EOT_OUT",),
    "AX_RAW_G": ("AX_RAW_G", "ax_g"),
    "AY_RAW_G": ("AY_RAW_G", "ay_g"),
    "AZ_RAW_G": ("AZ_RAW_G", "az_g"),
    "DBW_ACTUAL_PERCENT": (
        "DBW_ACTUAL_PERCENT",
        "DBW_Actual_percent",
        "DBW_Pos_percent",
    ),
    "DBW_TARGET_PERCENT": ("DBW_TARGET_PERCENT", "DBW_Target_percent"),
}

DERIVED_INPUTS: dict[str, tuple[str, ...]] = {
    "AX_CORRECTED_G": ("AX_RAW_G",),
    "AY_CORRECTED_G": ("AY_RAW_G",),
    "AZ_CORRECTED_G": ("AZ_RAW_G",),
    "EOT_DELTA": ("EOT_IN", "EOT_OUT"),
    "DBW_ERROR": ("DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT"),
}


def map_columns(raw_columns: Sequence[str]) -> dict[str, ChannelMapping]:
    raw_set = set(raw_columns)
    mapping: dict[str, ChannelMapping] = {}

    for channel_id, aliases in KNOWN_ALIASES.items():
        source = next((alias for alias in aliases if alias in raw_set), None)
        if source is None:
            mapping[channel_id] = ChannelMapping(channel_id, MappingState.MISSING)
        else:
            state = MappingState.MATCHED if source == channel_id or channel_id == "TIME" else MappingState.AUTO_MATCHED
            if channel_id == "EOT_IN" and source == "OilTemp_C":
                state = MappingState.MATCHED
            mapping[channel_id] = ChannelMapping(
                channel_id=channel_id,
                state=state,
                source_column=source,
                confidence=1.0,
            )

    for channel_id, input_channels in DERIVED_INPUTS.items():
        if all(mapping.get(input_id, ChannelMapping(input_id, MappingState.MISSING)).state is not MappingState.MISSING for input_id in input_channels):
            mapping[channel_id] = ChannelMapping(channel_id, MappingState.DERIVED, confidence=1.0)
        else:
            mapping[channel_id] = ChannelMapping(channel_id, MappingState.MISSING)

    return mapping


def resolve_standard_sources(raw_columns: Sequence[str]) -> dict[str, str]:
    mapping = map_columns(raw_columns)
    return {
        channel_id: channel_mapping.source_column
        for channel_id, channel_mapping in mapping.items()
        if channel_mapping.source_column is not None
    }
