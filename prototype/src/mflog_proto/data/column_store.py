"""Column-oriented in-memory representation for prototype log data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class ColumnStore:
    row_count: int
    raw_columns: dict[str, Sequence[str]]
    standard_sources: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        bad_columns = [
            name for name, values in self.raw_columns.items() if len(values) != self.row_count
        ]
        if bad_columns:
            joined = ", ".join(bad_columns)
            raise ValueError(f"columns do not match row_count={self.row_count}: {joined}")

    @property
    def raw_column_names(self) -> list[str]:
        return list(self.raw_columns.keys())

    def source_for(self, channel_id: str) -> str:
        if channel_id in self.standard_sources:
            return self.standard_sources[channel_id]
        if channel_id in self.raw_columns:
            return channel_id
        raise KeyError(channel_id)

    def values(self, channel_id: str) -> Sequence[str]:
        source = self.source_for(channel_id)
        return self.raw_columns[source]

