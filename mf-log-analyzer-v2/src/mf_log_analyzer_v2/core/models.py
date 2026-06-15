from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import polars as pl

ChannelGroup = Literal[
    "Time",
    "GPS",
    "Engine",
    "CoolingOil",
    "Fuel",
    "Electrical",
    "DriverInput",
    "DBW",
    "IMU",
    "Suspension",
    "Aero",
    "Diagnostics",
    "UserDefined",
]


@dataclass(frozen=True)
class Calibration:
    scale: float = 1.0
    offset: float = 0.0
    invert: bool = False

    def apply(self, values: np.ndarray) -> np.ndarray:
        calibrated = values * self.scale + self.offset
        return -calibrated if self.invert else calibrated


@dataclass(frozen=True)
class ChannelDefinition:
    channel_id: str
    display_name: dict[str, str]
    source_columns: tuple[str, ...]
    unit: str
    group: ChannelGroup
    calibration: Calibration = field(default_factory=Calibration)
    color: str = "#4c78a8"
    required: bool = False


@dataclass(frozen=True)
class VehicleProfile:
    profile_id: str
    name: str
    channels: dict[str, ChannelDefinition]

    def source_for(self, channel_id: str, headers: list[str]) -> str | None:
        channel = self.channels[channel_id]
        header_lookup = {header.casefold(): header for header in headers}
        for source in channel.source_columns:
            if source.casefold() in header_lookup:
                return header_lookup[source.casefold()]
        return None


@dataclass(frozen=True)
class LogTable:
    file_name: str
    frame: pl.DataFrame
    time_channel: str

    @property
    def row_count(self) -> int:
        return self.frame.height

    @property
    def time_range(self) -> tuple[float, float]:
        if self.row_count == 0:
            return (0.0, 0.0)
        values = self.frame[self.time_channel]
        return (float(values[0]), float(values[-1]))

    def values(self, channel_id: str) -> np.ndarray:
        return self.frame[channel_id].to_numpy()


@dataclass(frozen=True)
class LoadProgress:
    stage: str
    processed_rows: int = 0
    total_rows: int | None = None
