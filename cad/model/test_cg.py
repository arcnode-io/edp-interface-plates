"""Tests for cad/model/cg.py — parametric CG plate."""

from dataclasses import replace

import pytest

from cad.model.cg import (
    V1_COMMERCIAL_PARAMS,
    build_cg_plate,
    load_spec,
)


def test_load_spec_returns_cg() -> None:
    # arrange / act
    actual = load_spec()
    # assert
    expected_id = "CG"
    assert actual.plate_id == expected_id


def test_load_spec_has_commercial_and_defense_contexts() -> None:
    # arrange / act
    spec = load_spec()
    # assert
    expected_contexts = {"commercial", "defense_forward", "sovereign_government"}
    assert set(spec.deployment_contexts.keys()) == expected_contexts


def test_load_spec_penetration_schedule_has_three_entries() -> None:
    # arrange / act
    spec = load_spec()
    # assert
    expected_count = 3
    assert len(spec.penetration_schedule) == expected_count


def test_build_cg_plate_v1_commercial_bbox_matches_outer_dims() -> None:
    # arrange
    spec = load_spec()
    expected_w_mm = spec.outer_dims_mm.W
    expected_l_mm = spec.outer_dims_mm.L
    expected_t_mm = spec.deployment_contexts["commercial"].thickness_mm
    # act
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS, spec)
    bbox = plate.val().BoundingBox()
    # assert
    assert abs(bbox.xlen - expected_w_mm) < 0.01
    assert abs(bbox.ylen - expected_l_mm) < 0.01
    assert abs(bbox.zlen - expected_t_mm) < 0.01


def test_build_cg_plate_defense_uses_thicker_plate() -> None:
    # arrange
    spec = load_spec()
    defense_params = replace(V1_COMMERCIAL_PARAMS, deployment_context="defense_forward")
    expected_t_mm = spec.deployment_contexts["defense_forward"].thickness_mm
    # act
    plate = build_cg_plate(defense_params, spec)
    bbox = plate.val().BoundingBox()
    # assert
    assert abs(bbox.zlen - expected_t_mm) < 0.01
    assert expected_t_mm > spec.deployment_contexts["commercial"].thickness_mm


def test_build_cg_plate_rejects_multi_data_conduit() -> None:
    # arrange
    multi_params = replace(V1_COMMERCIAL_PARAMS, data_conduit_count=2)
    # act / assert
    with pytest.raises(NotImplementedError, match="data_conduit_count=2"):
        build_cg_plate(multi_params)


def test_build_cg_plate_solid_volume_decreases_with_penetrations() -> None:
    # arrange
    spec = load_spec()
    ctx = spec.deployment_contexts["commercial"]
    full_volume_mm3 = spec.outer_dims_mm.L * spec.outer_dims_mm.W * ctx.thickness_mm
    # act
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS, spec)
    actual_volume = plate.val().Volume()
    # assert — penetrations + 8 bolt holes should remove material
    assert actual_volume < full_volume_mm3
