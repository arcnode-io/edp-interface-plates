"""Geometry validation for the L-bracket solid.

Checks BRep validity, bounding box vs constants, and positive volume.
"""

import pytest

from cad.model.model import build_bracket
from sim.constants import (
    BRACKET_THICKNESS,
    BRACKET_WIDTH,
    HORIZONTAL_LEG_LENGTH,
    VERTICAL_LEG_HEIGHT,
    ureg,
)


def validate() -> None:
    """Run all geometry checks on the L-bracket solid."""
    solid = build_bracket().val()

    # BRep validity (OCC BRepCheck_Analyzer)
    assert solid.isValid(), "BRep defects detected"

    # Bounding box vs constants
    bb = solid.BoundingBox()
    expected_x = (HORIZONTAL_LEG_LENGTH + BRACKET_THICKNESS).to(ureg.mm).magnitude
    expected_y = BRACKET_WIDTH.to(ureg.mm).magnitude
    expected_z = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    assert bb.xlen == pytest.approx(expected_x, rel=0.01)
    assert bb.ylen == pytest.approx(expected_y, rel=0.01)
    assert bb.zlen == pytest.approx(expected_z, rel=0.01)

    # Volume sanity
    assert solid.Volume() > 0


if __name__ == "__main__":
    validate()
    print("All geometry checks passed")
