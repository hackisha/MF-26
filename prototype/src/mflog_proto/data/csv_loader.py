"""CSV loading path for the prototype's first performance slice."""

from __future__ import annotations

from dataclasses import dataclass, field
import csv
from pathlib import Path
from typing import Callable, Sequence

from mflog_proto.data.channel_mapping import resolve_standard_sources
from mflog_proto.data.column_store import ColumnStore


@dataclass(frozen=True)
class CsvLoadOptions:
    selected_columns: Sequence[str] | None = None
    numeric_probe: bool = False


@dataclass(frozen=True)
class CsvLoadProgress:
    path: Path
    rows_loaded: int
    physical_line_number: int
    columns_loaded: int


@dataclass(frozen=True)
class CsvLoadRequest:
    path: str | Path
    options: CsvLoadOptions = field(default_factory=CsvLoadOptions)
    progress_interval_rows: int = 1000
    on_progress: Callable[[CsvLoadProgress], None] | None = None
    is_cancelled: Callable[[], bool] | None = None


class CsvLoadCancelled(Exception):
    def __init__(self, path: Path, rows_loaded: int) -> None:
        super().__init__(f"CSV load cancelled after {rows_loaded} rows: {path}")
        self.path = path
        self.rows_loaded = rows_loaded


@dataclass(frozen=True)
class NumericError:
    row_number: int
    column: str
    value: str


@dataclass(frozen=True)
class MalformedRow:
    row_number: int
    expected_columns: int
    actual_columns: int


@dataclass(frozen=True)
class CsvLoadResult:
    store: ColumnStore
    duplicate_columns: dict[str, list[str]] = field(default_factory=dict)
    numeric_errors: list[NumericError] = field(default_factory=list)
    malformed_rows: list[MalformedRow] = field(default_factory=list)


def load_csv(path: str | Path, options: CsvLoadOptions | None = None) -> CsvLoadResult:
    return load_csv_request(CsvLoadRequest(path=path, options=options or CsvLoadOptions()))


def load_csv_request(request: CsvLoadRequest) -> CsvLoadResult:
    options = request.options
    csv_path = Path(request.path)
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
        malformed_rows: list[MalformedRow] = []
        rows_loaded = 0
        last_progress_rows = 0
        last_physical_line_number = 1
        progress_interval_rows = max(1, request.progress_interval_rows)

        for physical_line_number, row in enumerate(reader, start=2):
            _raise_if_cancelled(request, csv_path, rows_loaded)
            last_physical_line_number = physical_line_number
            if _is_blank_row(row):
                continue
            if len(row) != len(header):
                malformed_rows.append(
                    MalformedRow(
                        row_number=physical_line_number,
                        expected_columns=len(header),
                        actual_columns=len(row),
                    )
                )
            padded = row + [""] * max(0, len(header) - len(row))
            for index in selected_indices:
                name = header[index]
                value = padded[index] if index < len(padded) else ""
                columns[name].append(value)
                if options.numeric_probe:
                    _record_numeric_error(numeric_errors, physical_line_number, name, value)
            rows_loaded += 1
            if rows_loaded % progress_interval_rows == 0:
                _emit_progress(request, csv_path, rows_loaded, physical_line_number, len(columns))
                last_progress_rows = rows_loaded
                _raise_if_cancelled(request, csv_path, rows_loaded)

        if rows_loaded != last_progress_rows:
            _emit_progress(
                request,
                csv_path,
                rows_loaded,
                last_physical_line_number,
                len(columns),
            )
            _raise_if_cancelled(request, csv_path, rows_loaded)

    standard_sources = resolve_standard_sources(list(columns))
    return CsvLoadResult(
        store=ColumnStore(
            row_count=rows_loaded,
            raw_columns=columns,
            standard_sources=standard_sources,
        ),
        duplicate_columns=duplicate_columns,
        numeric_errors=numeric_errors,
        malformed_rows=malformed_rows,
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


def _emit_progress(
    request: CsvLoadRequest,
    csv_path: Path,
    rows_loaded: int,
    physical_line_number: int,
    columns_loaded: int,
) -> None:
    if request.on_progress is None:
        return
    request.on_progress(
        CsvLoadProgress(
            path=csv_path,
            rows_loaded=rows_loaded,
            physical_line_number=physical_line_number,
            columns_loaded=columns_loaded,
        )
    )


def _raise_if_cancelled(request: CsvLoadRequest, csv_path: Path, rows_loaded: int) -> None:
    if request.is_cancelled is not None and request.is_cancelled():
        raise CsvLoadCancelled(csv_path, rows_loaded)

