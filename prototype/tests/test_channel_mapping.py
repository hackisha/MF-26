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


def test_map_columns_recognizes_real_sample_core_sensor_aliases():
    raw_columns = [
        "Timestamp",
        "Latitude",
        "Longitude",
        "GPS_Speed_KPH",
        "Satellites",
        "Altitude_m",
        "Heading_deg",
        "RPM",
        "TPS_percent",
        "MAP_kPa",
        "VSS_kmh",
        "Batt_V",
        "Gear",
        "gx_dps",
        "gy_dps",
        "gz_dps",
        "OilPressure_bar",
        "FuelPressure_bar",
        "CLT_C",
    ]

    mapping = map_columns(raw_columns)
    sources = resolve_standard_sources(raw_columns)

    assert mapping["RPM"].state is MappingState.MATCHED
    assert sources["GPS_LATITUDE_DEG"] == "Latitude"
    assert sources["GPS_LONGITUDE_DEG"] == "Longitude"
    assert sources["GPS_SPEED_KPH"] == "GPS_Speed_KPH"
    assert sources["TPS_PERCENT"] == "TPS_percent"
    assert sources["VSS_KMH"] == "VSS_kmh"
    assert sources["BATTERY_V"] == "Batt_V"
    assert sources["GEAR"] == "Gear"
    assert sources["GYRO_Z_DPS"] == "gz_dps"
    assert sources["OIL_PRESSURE_BAR"] == "OilPressure_bar"
    assert sources["FUEL_PRESSURE_BAR"] == "FuelPressure_bar"
    assert sources["CLT_C"] == "CLT_C"


def test_map_columns_declares_2026_sensor_family_aliases_even_when_missing():
    mapping = map_columns(
        [
            "Susp_FL_mm",
            "Susp_FR_mm",
            "Susp_RL_mm",
            "Susp_RR_mm",
            "Pitot_dP_Pa",
            "Pitot_AirSpeed_KPH",
            "SteeringAngle_deg",
        ]
    )

    assert mapping["SUSP_FL_MM"].source_column == "Susp_FL_mm"
    assert mapping["SUSP_FR_MM"].source_column == "Susp_FR_mm"
    assert mapping["SUSP_RL_MM"].source_column == "Susp_RL_mm"
    assert mapping["SUSP_RR_MM"].source_column == "Susp_RR_mm"
    assert mapping["PITOT_DP_PA"].source_column == "Pitot_dP_Pa"
    assert mapping["PITOT_AIRSPEED_KPH"].source_column == "Pitot_AirSpeed_KPH"
    assert mapping["STEERING_ANGLE_DEG"].source_column == "SteeringAngle_deg"
