"""CSV loading path for the prototype's first performance slice."""

from __future__ import annotations

from dataclasses import dataclass, field
import csv
from pathlib import Path
from typing import Sequence

from mflog_proto.data.channel_mapping import resolve_standard_sources
from mflog_proto.data.column_store import ColumnStore


@dataclass(frozen=True)
class CsvLoadOptions:
    selected_columns: Sequence[str] | None = None
    numeric_probe: bool = False


@dataclass(frozen=True)
class NumericError:
    row_number: int
    column: str
    value: str


@dataclass(frozen=True)
class CsvLoadResult:
    store: ColumnStore
    duplicate_columns: dict[str, list[str]] = field(default_factory=dict)
    numeric_errors: list[NumericError] = field(default_factory=list)


def load_csv(path: str | Path, options: CsvLoadOptions | None = None) -> CsvLoadResult:
    options = options or CsvLoadOptions()
    csv_path = Path(path)
    selected = set(options.selected_columns or [])

    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration:
            return CsvLoadResult(store=ColumnStore(row_count=0, raw_columns={}))

        header, duplicate_columns = _deduplicate_header(raw_header)
        _validate_selected_columns(raw_header, header, selected)
        selected_indices = [
            index
            for index, raw_name in enumerate(raw_header)
            if not selected or raw_name in selected or header[index] in selected
        ]
        columns = {header[index]: [] for index in selected_indices}
        numeric_errors: list[NumericError] = []

        for physical_line_number, row in enumerate(reader, start=2):
            if _is_blank_row(row):
                continue
            padded = row + [""] * max(0, len(header) - len(row))
            for index in selected_indices:
                name = header[index]
                value = padded[index] if index < len(padded) else ""
                columns[name].append(value)
                if options.numeric_probe:
                    _record_numeric_error(numeric_errors, physical_line_number, name, value)

    row_count = len(next(iter(columns.values()), []))
    standard_sources = resolve_standard_sources(list(columns))
    return CsvLoadResult(
        store=ColumnStore(
            row_count=row_count,
            raw_columns=columns,
            standard_sources=standard_sources,
        ),
        duplicate_columns=duplicate_columns,
        numeric_errors=numeric_errors,
    )


def _deduplicate_header(raw_header: Sequence[str]) -> tuple[list[str], dict[str, list[str]]]:
    seen: dict[str, int] = {}
    header: list[str] = []
    duplicates: dict[str, list[str]] = {}

    for raw_name in raw_header:
        count = seen.get(raw_name, 0) + 1
        seen[raw_name] = count
        name = raw_name if count == 1 else f"{raw_name}__{count}"
        header.append(name)
        if count == 2:
            duplicates[raw_name] = [raw_name, name]
        elif count > 2:
            duplicates[raw_name].append(name)

    return header, duplicates


def _validate_selected_columns(
    raw_header: Sequence[str],
    header: Sequence[str],
    selected: set[str],
) -> None:
    if not selected:
        return
    available = set(raw_header) | set(header)
    missing = sorted(selected - available)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing selected columns: {joined}")


def _is_blank_row(row: Sequence[str]) -> bool:
    return not row or all(cell.strip() == "" for cell in row)


def _record_numeric_error(
    errors: list[NumericError], row_number: int, column: str, value: str
) -> None:
    if value.strip() == "":
        return
    try:
        float(value)
    except ValueError:
        errors.append(NumericError(row_number=row_number, column=column, value=value))


