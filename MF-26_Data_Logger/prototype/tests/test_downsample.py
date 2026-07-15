import pytest

import numpy as np

from mflog_proto.data.downsample import (
    GraphCache,
    fixed_stride,
    min_max_bucket,
    min_max_bucket_arrays,
)


def test_fixed_stride_preserves_original_when_source_fits_limit():
    x = [0.0, 1.0, 2.0]
    y = [10.0, None, 12.0]

    result = fixed_stride(x, y, max_points=5)

    assert result.x == x
    assert result.y == y
    assert result.strategy == "fixed_stride"
    assert result.source_count == 3


def test_fixed_stride_keeps_first_and_last_within_max_points():
    result = fixed_stride(
        x=[0.0, 1.0, 2.0, 3.0, 4.0],
        y=[10.0, 11.0, 12.0, 13.0, 14.0],
        max_points=3,
    )

    assert result.x == [0.0, 2.0, 4.0]
    assert result.y == [10.0, 12.0, 14.0]
    assert len(result.x) <= 3


def test_downsampling_rejects_limits_smaller_than_two_points():
    with pytest.raises(ValueError, match="max_points"):
        fixed_stride([0.0, 1.0], [1.0, 2.0], max_points=1)

    with pytest.raises(ValueError, match="max_points"):
        min_max_bucket([0.0, 1.0], [1.0, 2.0], max_points=0)


def test_min_max_bucket_preserves_extreme_y_values():
    result = min_max_bucket(
        x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        y=[0.0, 100.0, 1.0, -50.0, 2.0, 3.0],
        max_points=4,
    )

    assert 100.0 in result.y
    assert -50.0 in result.y
    assert result.x[0] == 0.0
    assert result.x[-1] == 5.0
    assert len(result.x) <= 4
    assert result.strategy == "min_max_bucket"
    assert result.source_count == 6


def test_min_max_bucket_preserves_global_extreme_when_capacity_is_odd():
    result = min_max_bucket(
        x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        y=[0.0, 1.0, 2.0, 3.0, 4.0, 100.0, 5.0, 0.0],
        max_points=5,
    )

    assert 100.0 in result.y
    assert result.x[0] == 0.0
    assert result.x[-1] == 7.0
    assert len(result.x) <= 5


def test_min_max_bucket_ignores_none_but_keeps_one_none_for_all_none_bucket():
    result = min_max_bucket(
        x=[0.0, 1.0, 2.0, 3.0, 4.0],
        y=[None, None, 8.0, 2.0, None],
        max_points=4,
    )

    assert result.x == [0.0, 2.0, 3.0, 4.0]
    assert result.y == [None, 8.0, 2.0, None]


def test_graph_cache_reuses_result_for_same_visible_range_key():
    cache = GraphCache()
    x = [0.0, 1.0, 2.0, 3.0]
    y = [0.0, 10.0, 20.0, 30.0]

    first = cache.get("rpm", x, y, pixel_width=2, strategy="fixed_stride")
    second = cache.get("rpm", list(x), list(y), pixel_width=2, strategy="fixed_stride")

    assert second is first


def test_graph_cache_uses_channel_range_width_strategy_and_count_in_key():
    cache = GraphCache()
    base_x = [0.0, 1.0, 2.0, 3.0]
    base_y = [0.0, 10.0, 20.0, 30.0]

    base = cache.get("rpm", base_x, base_y, pixel_width=2, strategy="fixed_stride")

    assert cache.get("temp", base_x, base_y, pixel_width=2, strategy="fixed_stride") is not base
    assert cache.get("rpm", [1.0, 2.0, 3.0], base_y[1:], pixel_width=2, strategy="fixed_stride") is not base
    assert cache.get("rpm", base_x, base_y, pixel_width=3, strategy="fixed_stride") is not base
    assert cache.get("rpm", base_x, base_y, pixel_width=2, strategy="min_max_bucket") is not base
    assert cache.get("rpm", base_x + [4.0], base_y + [40.0], pixel_width=2, strategy="fixed_stride") is not base


def test_graph_cache_does_not_reuse_when_series_content_changes_under_same_range():
    cache = GraphCache()
    x = [0.0, 1.0, 2.0, 3.0]

    first = cache.get("rpm", x, [0.0, 10.0, 20.0, 30.0], pixel_width=3, strategy="fixed_stride")
    changed_y = cache.get("rpm", x, [0.0, 10.0, 99.0, 30.0], pixel_width=3, strategy="fixed_stride")
    changed_x = cache.get("rpm", [0.0, 1.5, 2.0, 3.0], [0.0, 10.0, 20.0, 30.0], pixel_width=3, strategy="fixed_stride")

    assert changed_y is not first
    assert changed_x is not first


def test_min_max_bucket_uses_available_capacity_after_protected_extrema():
    result = min_max_bucket(
        x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        y=[0.0, 1.0, 2.0, 3.0, 4.0, 100.0, 5.0, 0.0],
        max_points=5,
    )

    assert len(result.x) == 5
    assert len(result.x) <= 5


def test_min_max_bucket_arrays_preserves_extrema_without_python_source_lists():
    result = min_max_bucket_arrays(
        x=np.asarray([0.0, 1.0, 2.0, 3.0, 4.0]),
        y=np.asarray([0.0, 100.0, np.nan, -20.0, 5.0]),
        max_points=4,
    )

    assert 100.0 in result.y
    assert -20.0 in result.y
    assert None not in (result.y[0], result.y[-1])
    assert result.x[0] == 0.0
    assert result.x[-1] == 4.0
    assert len(result.x) <= 4
