"""Tests for cad/model/build.py — single dispatcher across all plates."""

from dataclasses import replace

import pytest

from cad.model._plate import PlateBuildParams, default_params_for
from cad.model.build import (
    PLATE_IDS,
    build_for,
    load_plate_spec,
    spec_path_for,
    step_path_for,
)


@pytest.fixture(params=PLATE_IDS)
def plate_id(request: pytest.FixtureRequest) -> str:
    return request.param


def test_spec_loads_for_every_plate(plate_id: str) -> None:
    # arrange / act
    spec = load_plate_spec(plate_id)
    # assert
    assert spec.plate_id == plate_id


def test_every_plate_has_three_deployment_contexts(plate_id: str) -> None:
    # arrange / act
    spec = load_plate_spec(plate_id)
    # assert
    expected_contexts = {"commercial", "defense_forward", "sovereign_government"}
    assert set(spec.deployment_contexts.keys()) == expected_contexts


def test_every_plate_has_default_params(plate_id: str) -> None:
    # arrange / act
    spec = load_plate_spec(plate_id)
    # assert — design contract: every spec pins its v1 build params
    assert spec.default_params.deployment_context == "commercial"
    assert spec.default_params.data_conduit_count == 1
    assert spec.default_params.revision == "001"


def test_default_params_resolves_to_dataclass(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    # act
    params = default_params_for(spec)
    # assert
    assert isinstance(params, PlateBuildParams)
    assert params.deployment_context == "commercial"


def test_build_commercial_bbox_matches_outer_dims(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    expected_w_mm = spec.outer_dims_mm.W
    expected_l_mm = spec.outer_dims_mm.L
    expected_t_mm = spec.deployment_contexts["commercial"].thickness_mm
    # act
    plate = build_for(plate_id, spec=spec)
    bbox = plate.val().BoundingBox()
    # assert
    assert abs(bbox.xlen - expected_w_mm) < 0.01
    assert abs(bbox.ylen - expected_l_mm) < 0.01
    assert abs(bbox.zlen - expected_t_mm) < 0.01


def test_build_defense_uses_thicker_plate(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    defense_params = replace(
        default_params_for(spec), deployment_context="defense_forward"
    )
    expected_t_mm = spec.deployment_contexts["defense_forward"].thickness_mm
    # act
    plate = build_for(plate_id, params=defense_params, spec=spec)
    bbox = plate.val().BoundingBox()
    # assert
    assert abs(bbox.zlen - expected_t_mm) < 0.01
    assert expected_t_mm > spec.deployment_contexts["commercial"].thickness_mm


def test_build_rejects_multi_data_conduit(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    multi_params = replace(default_params_for(spec), data_conduit_count=2)
    # act / assert
    with pytest.raises(NotImplementedError, match="data_conduit_count=2"):
        build_for(plate_id, params=multi_params, spec=spec)


def test_build_volume_decreases_with_penetrations(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    ctx = spec.deployment_contexts["commercial"]
    full_volume_mm3 = spec.outer_dims_mm.L * spec.outer_dims_mm.W * ctx.thickness_mm
    # act
    plate = build_for(plate_id, spec=spec)
    actual_volume = plate.val().Volume()
    # assert — penetrations + 8 bolt holes remove material
    assert actual_volume < full_volume_mm3


def test_spec_path_resolves_to_existing_file(plate_id: str) -> None:
    # arrange / act / assert
    assert spec_path_for(plate_id).exists()


def test_step_path_returns_inside_specs_dir(plate_id: str) -> None:
    # arrange / act
    path = step_path_for(plate_id)
    # assert
    assert path.name == "plate.step"
    assert path.parent.name == plate_id


def test_step_path_for_defense_uses_suffixed_filename(plate_id: str) -> None:
    # arrange / act
    commercial = step_path_for(plate_id, "commercial")
    defense = step_path_for(plate_id, "defense_forward")
    sovereign = step_path_for(plate_id, "sovereign_government")
    # assert — defense + sovereign share the -defense suffix; commercial unchanged
    assert commercial.name == "plate.step"
    assert defense.name == "plate-defense.step"
    assert sovereign.name == "plate-defense.step"
    assert defense.parent == commercial.parent


# --- Plate-specific invariants (one per plate) ---


def test_cg_has_three_penetrations() -> None:
    # arrange / act
    spec = load_plate_spec("CG")
    # assert
    expected_count = 3
    assert len(spec.penetration_schedule) == expected_count


def test_bg_ac_has_four_penetrations() -> None:
    # arrange / act — 2x power feeders + 1x data + 1x ground
    spec = load_plate_spec("BG-AC")
    expected_count = 4
    # assert
    assert len(spec.penetration_schedule) == expected_count


def test_bg_ac_commercial_uses_m12_ground_stud() -> None:
    # arrange / act — BESS fault current path mandates M12 even commercial
    spec = load_plate_spec("BG-AC")
    actual = spec.deployment_contexts["commercial"].ground_stud
    # assert
    assert actual == "M12"


def test_bg_ac_v1_power_conduit_larger_than_cg() -> None:
    # arrange / act — BESS feeders carry MW; bigger than CG's 80kW feeder
    bg_ac_power_od = load_plate_spec("BG-AC").default_params.power_conduit_od_mm
    cg_power_od = load_plate_spec("CG").default_params.power_conduit_od_mm
    # assert
    assert bg_ac_power_od > cg_power_od


def test_cd_v1_power_conduit_sized_for_2_inch_qd() -> None:
    # arrange / act — cooling QD body OD ~75mm per theory.ipynb derivation
    cd_power_od = load_plate_spec("CD").default_params.power_conduit_od_mm
    # assert
    assert cd_power_od == pytest.approx(75.0, abs=0.5)
