"""Tests for cad/drawing/build.py — minimal v1 drawing pipeline (DXF + meta)."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from cad.drawing._drawing import (
    build_drawing_metadata,
    export_dxf,
    export_metadata,
)
from cad.model._plate import default_params_for
from cad.model.build import PLATE_IDS, build_for, load_plate_spec


@pytest.fixture(params=PLATE_IDS)
def plate_id(request: pytest.FixtureRequest) -> str:
    return request.param


def test_metadata_part_number_for_commercial(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    params = default_params_for(spec)
    # act
    actual = build_drawing_metadata(plate_id, params, spec)
    # assert
    expected_pn = f"ARC-PLT-{plate_id}-001"
    assert actual["part_number"] == expected_pn


def test_metadata_part_number_for_defense_appends_d(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    defense_params = replace(
        default_params_for(spec), deployment_context="defense_forward"
    )
    # act
    actual = build_drawing_metadata(plate_id, defense_params, spec)
    # assert
    expected_pn = f"ARC-PLT-{plate_id}-001-D"
    assert actual["part_number"] == expected_pn


def test_metadata_carries_deployment_context_material(plate_id: str) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    defense_params = replace(
        default_params_for(spec), deployment_context="defense_forward"
    )
    # act
    actual = build_drawing_metadata(plate_id, defense_params, spec)
    # assert — defense uses 5083 marine grade across every plate
    assert "5083" in actual["material"]


def test_export_dxf_creates_file(plate_id: str, tmp_path: Path) -> None:
    # arrange
    plate = build_for(plate_id)
    out = tmp_path / f"test_{plate_id}.dxf"
    # act
    actual = export_dxf(plate, out)
    # assert
    assert actual.exists()
    assert actual.stat().st_size > 0


def test_export_metadata_creates_json(plate_id: str, tmp_path: Path) -> None:
    # arrange
    spec = load_plate_spec(plate_id)
    metadata = build_drawing_metadata(plate_id, default_params_for(spec), spec)
    out = tmp_path / f"test_{plate_id}_meta.json"
    # act
    actual = export_metadata(metadata, out)
    # assert
    assert actual.exists()
    loaded = json.loads(actual.read_text())
    assert loaded["part_number"] == f"ARC-PLT-{plate_id}-001"
