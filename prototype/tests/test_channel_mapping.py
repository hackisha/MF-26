from mflog_proto.data.channel_mapping import (
    MappingState,
    map_columns,
    resolve_standard_sources,
)


def test_map_columns_recognizes_known_aliases_and_derived_channels():
    mapping = map_columns(["Timestamp", "OilTemp_C", "EOT_OUT", "ax_g", "ay_g", "az_g"])

    assert mapping["EOT_IN"].source_column == "OilTemp_C"
    assert mapping["EOT_IN"].state is MappingState.MATCHED
    assert mapping["AX_CORRECTED_G"].state is MappingState.DERIVED
    assert mapping["AY_CORRECTED_G"].state is MappingState.DERIVED
    assert mapping["AZ_CORRECTED_G"].state is MappingState.DERIVED
    assert mapping["EOT_DELTA"].state is MappingState.DERIVED


def test_map_columns_marks_missing_required_channels():
    mapping = map_columns(["Timestamp", "RPM"])

    assert mapping["EOT_IN"].state is MappingState.MISSING
    assert mapping["DBW_ERROR"].state is MappingState.MISSING


def test_map_columns_accepts_standard_channel_ids_as_direct_sources():
    mapping = map_columns(["AX_RAW_G", "DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT"])
    sources = resolve_standard_sources(
        ["AX_RAW_G", "DBW_TARGET_PERCENT", "DBW_ACTUAL_PERCENT"]
    )

    assert mapping["AX_RAW_G"].state is MappingState.MATCHED
    assert mapping["AX_CORRECTED_G"].state is MappingState.DERIVED
    assert mapping["DBW_ERROR"].state is MappingState.DERIVED
    assert sources["AX_RAW_G"] == "AX_RAW_G"
    assert sources["DBW_TARGET_PERCENT"] == "DBW_TARGET_PERCENT"
    assert sources["DBW_ACTUAL_PERCENT"] == "DBW_ACTUAL_PERCENT"
