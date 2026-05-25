"""Prototype log health checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from mflog_proto.data.column_store import ColumnStore


class HealthSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class HealthIssue:
    code: str
    severity: HealthSeverity
    message: str
    channel_id: str | None = None
    sample_index: int | None = None


@dataclass(frozen=True)
class HealthReport:
    issues: tuple[HealthIssue, ...]

    @property
    def status(self) -> HealthSeverity:
        if any(issue.severity is HealthSeverity.CRITICAL for issue in self.issues):
            return HealthSeverity.CRITICAL
        if any(issue.severity is HealthSeverity.WARNING for issue in self.issues):
            return HealthSeverity.WARNING
        return HealthSeverity.INFO

    def has_issue(self, code: str) -> bool:
        return any(issue.code == code for issue in self.issues)

    def count_by_severity(self, severity: HealthSeverity) -> int:
        return sum(1 for issue in self.issues if issue.severity is severity)


def run_health_checks(
    store: ColumnStore,
    *,
    required_channels: Sequence[str] = (),
    valid_ranges: dict[str, tuple[float, float]] | None = None,
    stuck_window: int = 8,
    dbw_error_threshold: float = 10.0,
) -> HealthReport:
    issues: list[HealthIssue] = []
    valid_ranges = valid_ranges or {}

    _check_missing_required(store, required_channels, issues)
    _check_timestamps(store, issues)
    _check_numeric_quality(store, valid_ranges, stuck_window, issues)
    _check_adxl_status(store, issues)
    _check_dbw_error(store, dbw_error_threshold, issues)

    return HealthReport(tuple(issues))


def _check_missing_required(
    store: ColumnStore,
    required_channels: Sequence[str],
    issues: list[HealthIssue],
) -> None:
    for channel_id in required_channels:
        try:
            store.source_for(channel_id)
        except KeyError:
            issues.append(
                HealthIssue(
                    code="missing_channel",
                    severity=HealthSeverity.CRITICAL,
                    channel_id=channel_id,
                    message=f"Required channel is missing: {channel_id}",
                )
            )


def _check_timestamps(store: ColumnStore, issues: list[HealthIssue]) -> None:
    values = _optional_values(store, ("TIME", "Timestamp"))
    if values is None:
        return
    numeric = [_to_float(value) for value in values]
    deltas: list[float] = []
    for index in range(1, len(numeric)):
        previous = numeric[index - 1]
        current = numeric[index]
        if previous is None or current is None:
            continue
        delta = current - previous
        if delta == 0:
            issues.append(
                HealthIssue(
                    code="timestamp_duplicate",
                    severity=HealthSeverity.WARNING,
                    channel_id="TIME",
                    sample_index=index,
                    message="Timestamp is duplicated.",
                )
            )
        elif delta < 0:
            issues.append(
                HealthIssue(
                    code="timestamp_backward",
                    severity=HealthSeverity.CRITICAL,
                    channel_id="TIME",
                    sample_index=index,
                    message="Timestamp moved backward.",
                )
            )
        else:
            deltas.append(delta)

    if len(deltas) >= 2:
        normal_delta = min(deltas)
        if normal_delta > 0:
            for index in range(1, len(numeric)):
                previous = numeric[index - 1]
                current = numeric[index]
                if previous is None or current is None:
                    continue
                if current - previous > normal_delta * 5:
                    issues.append(
                        HealthIssue(
                            code="timestamp_gap",
                            severity=HealthSeverity.WARNING,
                            channel_id="TIME",
                            sample_index=index,
                            message="Timestamp gap is much larger than the baseline sample interval.",
                        )
                    )
                    break


def _check_numeric_quality(
    store: ColumnStore,
    valid_ranges: dict[str, tuple[float, float]],
    stuck_window: int,
    issues: list[HealthIssue],
) -> None:
    for channel_id in store.raw_column_names:
        values = store.values(channel_id)
        numeric = [_to_float(value) for value in values]
        for index, (raw_value, numeric_value) in enumerate(zip(values, numeric, strict=True)):
            if raw_value.strip() == "":
                issues.append(
                    HealthIssue(
                        code="dropout",
                        severity=HealthSeverity.WARNING,
                        channel_id=channel_id,
                        sample_index=index,
                        message="Empty value detected.",
                    )
                )
            elif numeric_value is None:
                issues.append(
                    HealthIssue(
                        code="invalid_numeric",
                        severity=HealthSeverity.WARNING,
                        channel_id=channel_id,
                        sample_index=index,
                        message=f"Invalid numeric value: {raw_value}",
                    )
                )

            if numeric_value is not None and channel_id in valid_ranges:
                low, high = valid_ranges[channel_id]
                if numeric_value < low or numeric_value > high:
                    issues.append(
                        HealthIssue(
                            code="out_of_range",
                            severity=HealthSeverity.WARNING,
                            channel_id=channel_id,
                            sample_index=index,
                            message=f"Value outside valid range {low}..{high}: {numeric_value}",
                        )
                    )

            if channel_id == "Batt_V" and numeric_value is not None and numeric_value < 10.0:
                issues.append(
                    HealthIssue(
                        code="low_voltage",
                        severity=HealthSeverity.CRITICAL,
                        channel_id=channel_id,
                        sample_index=index,
                        message=f"Battery voltage is low: {numeric_value}",
                    )
                )

        if _has_stuck_window(numeric, stuck_window):
            issues.append(
                HealthIssue(
                    code="stuck_sensor",
                    severity=HealthSeverity.WARNING,
                    channel_id=channel_id,
                    message=f"Sensor value did not change for at least {stuck_window} samples.",
                )
            )


def _check_adxl_status(store: ColumnStore, issues: list[HealthIssue]) -> None:
    for channel_id in ("AX_CORRECTED_G", "AY_CORRECTED_G", "AZ_CORRECTED_G"):
        try:
            store.source_for(channel_id)
        except KeyError:
            continue
        issues.append(
            HealthIssue(
                code="adxl_correction_applied",
                severity=HealthSeverity.INFO,
                channel_id=channel_id,
                message="ADXL345 corrected acceleration channel is present.",
            )
        )
        return

    for channel_id in ("AX_RAW_G", "AY_RAW_G", "AZ_RAW_G", "ax_g", "ay_g", "az_g"):
        try:
            store.source_for(channel_id)
        except KeyError:
            continue
        issues.append(
            HealthIssue(
                code="adxl_correction_available",
                severity=HealthSeverity.INFO,
                channel_id=channel_id,
                message="ADXL345 raw acceleration is available; corrected /8 channels can be derived.",
            )
        )
        return

    issues.append(
        HealthIssue(
            code="adxl_correction_missing",
            severity=HealthSeverity.INFO,
            message="No ADXL345 raw or corrected acceleration channel was found.",
        )
    )


def _check_dbw_error(
    store: ColumnStore,
    threshold: float,
    issues: list[HealthIssue],
) -> None:
    target_values = _optional_values(store, ("DBW_TARGET_PERCENT", "DBW_Target_percent"))
    actual_values = _optional_values(
        store,
        ("DBW_ACTUAL_PERCENT", "DBW_Actual_percent", "DBW_Pos_percent"),
    )
    if target_values is None or actual_values is None:
        return
    for index, (target_raw, actual_raw) in enumerate(zip(target_values, actual_values, strict=True)):
        target = _to_float(target_raw)
        actual = _to_float(actual_raw)
        if target is None or actual is None:
            continue
        error = abs(target - actual)
        if error > threshold:
            issues.append(
                HealthIssue(
                    code="dbw_tracking_error",
                    severity=HealthSeverity.WARNING,
                    channel_id="DBW_ERROR",
                    sample_index=index,
                    message=f"DBW tracking error exceeds threshold {threshold}: {error}",
                )
            )
            return


def _optional_values(store: ColumnStore, channel_ids: tuple[str, ...]) -> Sequence[str] | None:
    for channel_id in channel_ids:
        try:
            return store.values(channel_id)
        except KeyError:
            continue
    return None


def _has_stuck_window(values: Sequence[float | None], window: int) -> bool:
    if window < 2:
        return False
    run_value: float | None = None
    run_length = 0
    for value in values:
        if value is None:
            run_value = None
            run_length = 0
            continue
        if value == run_value:
            run_length += 1
        else:
            run_value = value
            run_length = 1
        if run_length >= window:
            return True
    return False


def _to_float(value: str) -> float | None:
    if value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None
