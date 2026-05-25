"""Derived-channel calculations shared by prototype views and reports."""

from __future__ import annotations

from collections.abc import Sequence

from mflog_proto.data.column_store import ColumnStore


DerivedColumns = dict[str, list[float | None]]


def compute_basic_derived_channels(store: ColumnStore) -> DerivedColumns:
    derived: DerivedColumns = {}

    _add_scaled(derived, "AX_CORRECTED_G", store, ("AX_RAW_G", "ax_g"), scale=1 / 8)
    _add_scaled(derived, "AY_CORRECTED_G", store, ("AY_RAW_G", "ay_g"), scale=1 / 8)
    _add_scaled(derived, "AZ_CORRECTED_G", store, ("AZ_RAW_G", "az_g"), scale=1 / 8)
    _add_difference(derived, "EOT_DELTA", store, "EOT_OUT", "EOT_IN")
    _add_difference(
        derived,
        "DBW_ERROR",
        store,
        "DBW_TARGET_PERCENT",
        "DBW_ACTUAL_PERCENT",
    )

    return derived


def _add_scaled(
    derived: DerivedColumns,
    output_channel: str,
    store: ColumnStore,
    source_channels: tuple[str, ...],
    scale: float,
) -> None:
    try:
        values = _values_first(store, source_channels)
    except KeyError:
        return
    output: list[float | None] = []
    for value in values:
        numeric = _to_float(value)
        output.append(None if numeric is None else numeric * scale)
    derived[output_channel] = output


def _add_difference(
    derived: DerivedColumns,
    output_channel: str,
    store: ColumnStore,
    left_channel: str,
    right_channel: str,
) -> None:
    try:
        left_values = _values_first(store, (left_channel,))
        right_values = _values_first(store, (right_channel,))
    except KeyError:
        return
    derived[output_channel] = _subtract(left_values, right_values)


def _values_first(store: ColumnStore, channel_ids: tuple[str, ...]) -> Sequence[str]:
    for channel_id in channel_ids:
        try:
            return store.values(channel_id)
        except KeyError:
            continue
    raise KeyError(channel_ids[0])


def _subtract(
    left_values: Sequence[str],
    right_values: Sequence[str],
) -> list[float | None]:
    output: list[float | None] = []
    for left_raw, right_raw in zip(left_values, right_values, strict=True):
        left = _to_float(left_raw)
        right = _to_float(right_raw)
        output.append(None if left is None or right is None else left - right)
    return output


def _to_float(value: str) -> float | None:
    if value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None
