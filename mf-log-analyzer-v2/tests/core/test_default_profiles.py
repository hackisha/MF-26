from typing import get_args, get_type_hints

from mf_log_analyzer_v2.core.default_profiles import channel, mf_default_profile
from mf_log_analyzer_v2.core.models import ChannelGroup


def test_default_profile_maps_eot_in_from_oil_temp():
    profile = mf_default_profile()
    assert profile.source_for("EOT_IN", ["Timestamp", "OilTemp_C"]) == "OilTemp_C"


def test_default_profile_defines_adxl_correction():
    profile = mf_default_profile()
    assert profile.channels["AX_CORRECTED_G"].source_columns == ("ax_g",)
    assert profile.channels["AX_CORRECTED_G"].calibration.scale == 0.125


def test_default_profile_contains_dbw_and_suspension_channels():
    profile = mf_default_profile()
    assert "DBW_TARGET_PERCENT" in profile.channels
    assert "DBW_ACTUAL_PERCENT" in profile.channels
    assert "SUSP_FL_MM" in profile.channels
    assert "SUSP_RR_MM" in profile.channels


def test_default_profile_channel_groups_are_valid():
    assert get_type_hints(channel)["group"] == ChannelGroup

    valid_groups = set(get_args(ChannelGroup))
    profile = mf_default_profile()
    assert {definition.group for definition in profile.channels.values()} <= valid_groups
