import pytest

from mflog_proto.data.column_store import ColumnStore


def test_column_store_preserves_raw_columns_and_traceability():
    store = ColumnStore(
        row_count=3,
        raw_columns={
            "Timestamp": ["0.0", "0.1", "0.2"],
            "OilTemp_C": ["90", "91", "92"],
        },
        standard_sources={"EOT_IN": "OilTemp_C"},
    )

    assert store.row_count == 3
    assert store.raw_column_names == ["Timestamp", "OilTemp_C"]
    assert store.source_for("EOT_IN") == "OilTemp_C"
    assert store.values("EOT_IN") == ["90", "91", "92"]


def test_column_store_rejects_columns_with_wrong_length():
    with pytest.raises(ValueError, match="row_count"):
        ColumnStore(row_count=2, raw_columns={"RPM": ["1"]}, standard_sources={})


def test_column_store_raises_for_unknown_channel():
    store = ColumnStore(row_count=1, raw_columns={"RPM": ["900"]}, standard_sources={})

    with pytest.raises(KeyError, match="UNKNOWN"):
        store.values("UNKNOWN")

