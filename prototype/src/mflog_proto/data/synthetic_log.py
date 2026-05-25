"""Deterministic synthetic CSV generator for MF log analyzer prototypes."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence


CORE_CHANNELS: tuple[str, ...] = (
    "Timestamp",
    "Latitude",
    "Longitude",
    "GPS_Speed_KPH",
    "RPM",
    "TPS_percent",
    "MAP_kPa",
    "OilTemp_C",
    "EOT_OUT",
    "CLT_C",
    "Batt_V",
    "DBW_Pos_percent",
    "DBW_Target_percent",
    "ax_g",
    "ay_g",
    "az_g",
    "Susp_FL_mm",
    "Susp_FR_mm",
    "Susp_RL_mm",
    "Susp_RR_mm",
    "Pitot_dP_Pa",
    "Pitot_AirSpeed_KPH",
    "SteeringAngle_deg",
)


@dataclass(frozen=True)
class SyntheticCsvSummary:
    path: Path
    rows: int
    channels: int
    defects_enabled: bool
    file_size_bytes: int


def build_channel_names(total_channels: int) -> list[str]:
    if total_channels < len(CORE_CHANNELS):
        raise ValueError("total_channels must be greater than or equal to core channel count")

    names = list(CORE_CHANNELS)
    for sensor_index in range(1, total_channels - len(CORE_CHANNELS) + 1):
        names.append(f"Sensor_{sensor_index:03d}")
    return names


def iter_synthetic_rows(
    rows: int,
    channels: Sequence[str],
    defects: bool = False,
) -> Iterator[list[str]]:
    for row_index in range(rows):
        yield [
            _format_value(channel, row_index, defects=defects)
            for channel in channels
        ]


def write_synthetic_csv(
    path: Path,
    rows: int,
    channels: int,
    defects: bool = False,
) -> SyntheticCsvSummary:
    channel_names = build_channel_names(channels)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(channel_names)
        writer.writerows(iter_synthetic_rows(rows, channel_names, defects=defects))

    return SyntheticCsvSummary(
        path=path,
        rows=rows,
        channels=channels,
        defects_enabled=defects,
        file_size_bytes=path.stat().st_size,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic MF synthetic log CSV data.")
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--channels", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--defects", action="store_true")
    args = parser.parse_args(argv)

    summary = write_synthetic_csv(
        path=args.output,
        rows=args.rows,
        channels=args.channels,
        defects=args.defects,
    )
    print(
        f"wrote {summary.rows} rows x {summary.channels} channels to "
        f"{summary.path} ({summary.file_size_bytes} bytes)"
    )
    return 0


def _format_value(channel: str, row_index: int, defects: bool) -> str:
    if defects:
        defective = _defective_value(channel, row_index)
        if defective is not None:
            return defective

    return f"{_base_value(channel, row_index):.3f}"


def _defective_value(channel: str, row_index: int) -> str | None:
    if channel == "Timestamp":
        if row_index == 4:
            return f"{_base_value(channel, 3):.3f}"
        if row_index == 9:
            return f"{_base_value(channel, 8) - 0.050:.3f}"
    if channel == "RPM" and row_index == 5:
        return "INVALID"
    if channel == "TPS_percent" and row_index in {7, 8}:
        return f"{_base_value(channel, 6):.3f}"
    if channel == "MAP_kPa" and row_index == 12:
        return ""
    return None


def _base_value(channel: str, row_index: int) -> float:
    if channel == "Timestamp":
        return row_index * 0.1
    if channel == "Latitude":
        return 37.500000 + row_index * 0.00001
    if channel == "Longitude":
        return 127.000000 + row_index * 0.00001
    if channel == "GPS_Speed_KPH":
        return 40.0 + (row_index % 50) * 1.7
    if channel == "RPM":
        return 2200.0 + row_index * 37.0
    if channel == "TPS_percent":
        return 20.0 + (row_index % 20) * 3.0
    if channel == "MAP_kPa":
        return 95.0 + (row_index % 12) * 1.5
    if channel == "OilTemp_C":
        return 82.0 + (row_index % 30) * 0.08
    if channel == "EOT_OUT":
        return 84.0 + (row_index % 30) * 0.07
    if channel == "CLT_C":
        return 78.0 + (row_index % 24) * 0.1
    if channel == "Batt_V":
        return 13.8 + (row_index % 5) * 0.01
    if channel == "DBW_Pos_percent":
        return 18.0 + (row_index % 18) * 2.5
    if channel == "DBW_Target_percent":
        return 19.0 + (row_index % 18) * 2.5
    if channel == "ax_g":
        return ((row_index % 9) - 4) * 0.04
    if channel == "ay_g":
        return ((row_index % 11) - 5) * 0.03
    if channel == "az_g":
        return 1.0 + ((row_index % 7) - 3) * 0.01
    if channel == "Susp_FL_mm":
        return 30.0 + (row_index % 10) * 0.4
    if channel == "Susp_FR_mm":
        return 30.5 + (row_index % 10) * 0.4
    if channel == "Susp_RL_mm":
        return 28.0 + (row_index % 10) * 0.3
    if channel == "Susp_RR_mm":
        return 28.5 + (row_index % 10) * 0.3
    if channel == "Pitot_dP_Pa":
        return 120.0 + (row_index % 40) * 6.0
    if channel == "Pitot_AirSpeed_KPH":
        return 35.0 + (row_index % 40) * 1.2
    if channel == "SteeringAngle_deg":
        return ((row_index % 17) - 8) * 2.0
    if channel.startswith("Sensor_"):
        try:
            sensor_offset = int(channel.removeprefix("Sensor_")) - 1
        except ValueError:
            sensor_offset = 0
        return float(row_index + sensor_offset)
    return float(row_index)


if __name__ == "__main__":
    raise SystemExit(main())
