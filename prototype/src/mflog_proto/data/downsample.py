from __future__ import annotations

from dataclasses import dataclass
import hashlib
from math import ceil
from typing import Literal


@dataclass(frozen=True)
class DownsampledSeries:
    x: list[float]
    y: list[float | None]
    strategy: str
    source_count: int


def fixed_stride(x: list[float], y: list[float | None], max_points: int) -> DownsampledSeries:
    _validate_inputs(x, y, max_points)
    source_count = len(x)
    if source_count <= max_points:
        return DownsampledSeries(list(x), list(y), "fixed_stride", source_count)

    last_index = source_count - 1
    step = last_index / (max_points - 1)
    indices = [round(i * step) for i in range(max_points)]
    indices[0] = 0
    indices[-1] = last_index

    return DownsampledSeries(
        [x[index] for index in indices],
        [y[index] for index in indices],
        "fixed_stride",
        source_count,
    )


def min_max_bucket(x: list[float], y: list[float | None], max_points: int) -> DownsampledSeries:
    _validate_inputs(x, y, max_points)
    source_count = len(x)
    if source_count <= max_points:
        return DownsampledSeries(list(x), list(y), "min_max_bucket", source_count)

    if max_points == 2:
        indices = [0, source_count - 1]
    else:
        indices = _protected_indices(y, max_points)
        protected = set(indices)
        interior_indices = [
            index for index in range(1, source_count - 1) if index not in protected
        ]
        interior_capacity = max_points - len(indices)
        bucket_count = max(1, ceil(interior_capacity / 2)) if interior_capacity > 0 else 0

        for bucket_number in range(bucket_count):
            start = bucket_number * len(interior_indices) // bucket_count
            end = (bucket_number + 1) * len(interior_indices) // bucket_count
            bucket = interior_indices[start:end]
            remaining = max_points - len(set(indices))
            if remaining <= 0:
                break
            indices.extend(_bucket_representatives(bucket, y, remaining))

    unique_indices = sorted(dict.fromkeys(indices))
    return DownsampledSeries(
        [x[index] for index in unique_indices],
        [y[index] for index in unique_indices],
        "min_max_bucket",
        source_count,
    )


class GraphCache:
    def __init__(self) -> None:
        self._cache: dict[
            tuple[str, tuple[float | None, float | None], int, str, int, str, str],
            DownsampledSeries,
        ] = {}

    def get(
        self,
        channel_id: str,
        x: list[float],
        y: list[float | None],
        pixel_width: int,
        strategy: Literal["fixed_stride", "min_max_bucket"] | str,
    ) -> DownsampledSeries:
        key = (
            channel_id,
            _visible_range(x),
            pixel_width,
            strategy,
            len(x),
            _series_digest(x),
            _series_digest(y),
        )
        if key not in self._cache:
            if strategy == "fixed_stride":
                self._cache[key] = fixed_stride(x, y, pixel_width)
            elif strategy == "min_max_bucket":
                self._cache[key] = min_max_bucket(x, y, pixel_width)
            else:
                raise ValueError(f"unknown downsampling strategy: {strategy}")
        return self._cache[key]


def _validate_inputs(x: list[float], y: list[float | None], max_points: int) -> None:
    if max_points < 2:
        raise ValueError("max_points must be at least 2")
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")


def _bucket_representatives(
    bucket: list[int], y: list[float | None], limit: int
) -> list[int]:
    valued = [index for index in bucket if y[index] is not None]
    if not valued:
        return bucket[:1]

    min_index = min(valued, key=lambda index: y[index])
    max_index = max(valued, key=lambda index: y[index])
    if limit == 1 or min_index == max_index:
        return [min_index]
    return sorted([min_index, max_index])


def _protected_indices(y: list[float | None], max_points: int) -> list[int]:
    first = 0
    last = len(y) - 1
    indices = [first, last]
    valued = [index for index, value in enumerate(y) if value is not None]
    if not valued or max_points <= 2:
        return indices

    max_index = max(valued, key=lambda index: y[index])
    min_index = min(valued, key=lambda index: y[index])
    for index in (max_index, min_index):
        if index not in indices and len(indices) < max_points:
            indices.append(index)
    return indices


def _visible_range(x: list[float]) -> tuple[float | None, float | None]:
    if not x:
        return (None, None)
    return (x[0], x[-1])


def _series_digest(values: list[float | None]) -> str:
    digest = hashlib.blake2b(digest_size=12)
    for value in values:
        if value is None:
            digest.update(b"N;")
        else:
            digest.update(repr(float(value)).encode("ascii"))
            digest.update(b";")
    return digest.hexdigest()
