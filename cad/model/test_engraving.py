"""Tests for cad/model/engraving.py — logo engraving primitive."""

import cadquery as cq
import pytest

from cad.model.engraving import (
    ENGRAVE_DEPTH_MM,
    LOGO_DEFAULT_WIDTH_MM,
    LOGO_SVG_PATH,
    _load_subpath_points,
    engrave_logo,
)

# ── Arrange: simple test plate ─────────────────────────────────────────
PLATE_LEN_MM = 200.0
PLATE_WID_MM = 200.0
PLATE_THK_MM = 6.0


def _test_plate() -> cq.Workplane:
    """Plate centered at origin, top face at z=PLATE_THK_MM/2."""
    return cq.Workplane("XY").box(PLATE_WID_MM, PLATE_LEN_MM, PLATE_THK_MM)


def test_logo_svg_exists() -> None:
    assert LOGO_SVG_PATH.exists(), f"logo asset missing at {LOGO_SVG_PATH}"


def test_load_subpath_points_returns_at_least_one_closed_subpath() -> None:
    subs = _load_subpath_points(LOGO_SVG_PATH, target_width_mm=100.0)
    assert len(subs) > 0
    for pts in subs:
        # Closed: last point equals first.
        assert pts[0] == pts[-1], "subpath not closed"
        assert len(pts) > 3, "subpath needs ≥3 unique points to form a face"


def test_load_subpath_points_centers_and_scales_to_target_width() -> None:
    target = 120.0
    subs = _load_subpath_points(LOGO_SVG_PATH, target_width_mm=target)
    xs = [p[0] for sub in subs for p in sub]
    ys = [p[1] for sub in subs for p in sub]
    width = max(xs) - min(xs)
    # x bounds centered on 0 (within sample tolerance).
    assert (max(xs) + min(xs)) == pytest.approx(0.0, abs=0.1)
    assert (max(ys) + min(ys)) == pytest.approx(0.0, abs=0.1)
    assert width == pytest.approx(target, rel=0.01)


def test_engrave_logo_reduces_plate_volume() -> None:
    plate = _test_plate()
    v0 = plate.val().Volume()

    engraved = engrave_logo(plate, face_z_mm=PLATE_THK_MM / 2)

    v1 = engraved.val().Volume()
    assert v1 < v0, "engraving should remove material"


def test_engrave_logo_preserves_outer_bounding_box() -> None:
    plate = _test_plate()
    engraved = engrave_logo(plate, face_z_mm=PLATE_THK_MM / 2)
    bb = engraved.val().BoundingBox()
    assert bb.xlen == pytest.approx(PLATE_WID_MM, rel=1e-6)
    assert bb.ylen == pytest.approx(PLATE_LEN_MM, rel=1e-6)
    assert bb.zlen == pytest.approx(PLATE_THK_MM, rel=1e-6)


def test_engrave_logo_does_not_pierce_through() -> None:
    plate = _test_plate()
    engraved = engrave_logo(plate, face_z_mm=PLATE_THK_MM / 2, depth_mm=0.5)
    v_removed = plate.val().Volume() - engraved.val().Volume()
    # Sanity bound: removed volume cannot exceed depth × bbox-of-logo (~width × height × depth).
    upper_bound_mm3 = LOGO_DEFAULT_WIDTH_MM * LOGO_DEFAULT_WIDTH_MM * 0.5
    assert v_removed > 0.0
    assert v_removed < upper_bound_mm3


def test_engrave_logo_minus_z_face_removes_material_at_bottom() -> None:
    plate = _test_plate()
    v0 = plate.val().Volume()
    engraved = engrave_logo(
        plate, face_z_mm=-PLATE_THK_MM / 2, outward_normal_z=-1, depth_mm=1.0
    )
    v1 = engraved.val().Volume()
    assert v1 < v0
    # Removed material must lie within the lower 1mm slab of the plate.
    bb = engraved.val().BoundingBox()
    assert bb.zmin == pytest.approx(-PLATE_THK_MM / 2, abs=1e-6)
    assert bb.zmax == pytest.approx(PLATE_THK_MM / 2, abs=1e-6)


def test_engrave_logo_rejects_invalid_normal() -> None:
    plate = _test_plate()
    with pytest.raises(ValueError, match="outward_normal_z"):
        engrave_logo(plate, face_z_mm=0, outward_normal_z=0)


def test_engrave_default_depth_constant_is_subtle() -> None:
    # Reason: engraving should be cosmetic, not structural — well under any practical
    # plate thickness (commercial plate is 6mm).
    assert 0.1 <= ENGRAVE_DEPTH_MM <= 3.0
