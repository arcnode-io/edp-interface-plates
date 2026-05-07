"""Tests for cad/model/bg_ac.py — parametric BG-AC plate."""

from dataclasses import replace

import pytest

from cad.model.bg_ac import (
    V1_COMMERCIAL_PARAMS,
    build_bg_ac_plate,
    load_bg_ac_spec,
)


def test_load_spec_returns_bg_ac() -> None:
    actual = load_bg_ac_spec()
    expected_id = "BG-AC"
    assert actual.plate_id == expected_id


def test_load_spec_has_4_penetrations() -> None:
    # arrange / act — BG-AC has 2x power + 1x data + 1x ground (vs CG's 3)
    spec = load_bg_ac_spec()
    expected_count = 4
    # assert
    assert len(spec.penetration_schedule) == expected_count


def test_commercial_uses_m12_ground_stud() -> None:
    # arrange / act — BESS fault current path mandates M12 even commercial
    spec = load_bg_ac_spec()
    actual = spec.deployment_contexts["commercial"].ground_stud
    # assert — different from CG which uses M10 commercial
    assert actual == "M12"


def test_build_bg_ac_plate_v1_commercial_bbox() -> None:
    # arrange
    spec = load_bg_ac_spec()
    expected_w_mm = spec.outer_dims_mm.W
    expected_l_mm = spec.outer_dims_mm.L
    expected_t_mm = spec.deployment_contexts["commercial"].thickness_mm
    # act
    plate = build_bg_ac_plate(V1_COMMERCIAL_PARAMS, spec)
    bbox = plate.val().BoundingBox()
    # assert
    assert abs(bbox.xlen - expected_w_mm) < 0.01
    assert abs(bbox.ylen - expected_l_mm) < 0.01
    assert abs(bbox.zlen - expected_t_mm) < 0.01


def test_v1_power_conduit_larger_than_cg() -> None:
    # arrange / act — BESS feeders carry MW; bigger than CG's 80kW feeder
    cg_power_od = 73.0
    # assert
    assert V1_COMMERCIAL_PARAMS.power_conduit_od_mm > cg_power_od


def test_build_bg_ac_plate_rejects_multi_data_conduit() -> None:
    # arrange
    multi_params = replace(V1_COMMERCIAL_PARAMS, data_conduit_count=2)
    # act / assert
    with pytest.raises(NotImplementedError, match="data_conduit_count=2"):
        build_bg_ac_plate(multi_params)
