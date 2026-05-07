"""Tests for cad/drawing/cg.py — minimal v1 drawing pipeline."""

from dataclasses import replace
from pathlib import Path

from cad.drawing.cg import build_drawing_metadata, export_dxf, export_metadata
from cad.model.cg import V1_COMMERCIAL_PARAMS, build_cg_plate, load_spec


def test_metadata_part_number_for_commercial() -> None:
    # arrange
    spec = load_spec()
    # act
    actual = build_drawing_metadata(V1_COMMERCIAL_PARAMS, spec)
    # assert
    expected_pn = "ARC-PLT-CG-001"
    assert actual["part_number"] == expected_pn


def test_metadata_part_number_for_defense_appends_d() -> None:
    # arrange
    spec = load_spec()
    defense_params = replace(V1_COMMERCIAL_PARAMS, deployment_context="defense_forward")
    # act
    actual = build_drawing_metadata(defense_params, spec)
    # assert
    expected_pn = "ARC-PLT-CG-001-D"
    assert actual["part_number"] == expected_pn


def test_metadata_carries_deployment_context_material() -> None:
    # arrange
    spec = load_spec()
    defense_params = replace(V1_COMMERCIAL_PARAMS, deployment_context="defense_forward")
    # act
    actual = build_drawing_metadata(defense_params, spec)
    # assert — defense uses 5083 marine grade, not commercial 6061
    assert "5083" in actual["material"]


def test_export_dxf_creates_file(tmp_path: Path) -> None:
    # arrange
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS)
    out = tmp_path / "test_cg.dxf"
    # act
    actual = export_dxf(plate, out)
    # assert
    assert actual.exists()
    assert actual.stat().st_size > 0


def test_export_metadata_creates_json(tmp_path: Path) -> None:
    # arrange
    spec = load_spec()
    metadata = build_drawing_metadata(V1_COMMERCIAL_PARAMS, spec)
    out = tmp_path / "test_meta.json"
    # act
    actual = export_metadata(metadata, out)
    # assert
    assert actual.exists()
    import json

    loaded = json.loads(actual.read_text())
    assert loaded["part_number"] == "ARC-PLT-CG-001"
