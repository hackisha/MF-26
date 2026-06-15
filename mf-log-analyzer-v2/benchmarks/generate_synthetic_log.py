from __future__ import annotations

import csv
import math
from pathlib import Path

BASE_HEADERS = [
    "Timestamp",
    "RPM",
    "TPS_percent",
    "OilTemp_C",
    "EOT_OUT",
    "Batt_V",
    "ax_g",
    "ay_g",
    "DBW_Target_percent",
    "DBW_Pos_percent",
]


def generate_synthetic_log(output: Path, rows: int = 300_000, extra_channels: int = 120) -> None:
    headers = [*BASE_HEADERS, *(f"Extra_{index:03d}" for index in range(extra_channels))]
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for row_index in range(rows):
            timestamp = row_index * 0.01
            phase = row_index * 0.015
            base_values = [
                f"{timestamp:.2f}",
                f"{4500.0 + 1800.0 * math.sin(phase):.3f}",
                f"{50.0 + 45.0 * math.sin(phase * 0.5):.3f}",
                f"{95.0 + 8.0 * math.cos(phase * 0.2):.3f}",
                f"{92.0 + 7.0 * math.sin(phase * 0.18):.3f}",
                f"{13.2 + 0.4 * math.cos(phase * 0.3):.3f}",
                f"{0.7 * math.sin(phase * 1.7):.6f}",
                f"{0.8 * math.cos(phase * 1.3):.6f}",
                f"{48.0 + 40.0 * math.sin(phase * 0.45):.3f}",
                f"{47.0 + 39.0 * math.sin((phase * 0.45) - 0.04):.3f}",
            ]
            extra_values = [
                f"{math.sin((row_index + channel_index) * 0.01) + math.cos(channel_index * 0.03):.6f}"
                for channel_index in range(extra_channels)
            ]
            writer.writerow([*base_values, *extra_values])
