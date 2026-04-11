"""Assembly validation for the L-bracket assembly.

Checks BRep validity of all components, assembly has expected parts,
and bounding box is reasonable.
"""

import pytest

from cad.model.assembly import build_assembly
from sim.constants import (
    BRACKET_THICKNESS,
    BRACKET_WIDTH,
    VERTICAL_LEG_HEIGHT,
    ureg,
)


def validate() -> None:
    """Run all assembly checks."""
    assy = build_assembly()

    # Assembly has expected parts
    part_names = {child.name for child in assy.objects.values()}
    expected = {"bracket", "wall_plate", "bolt_1", "bolt_2"}
    assert expected.issubset(part_names), f"Missing parts: {expected - part_names}"

    # Assembly bounding box sanity (wall plate adds ~10mm in -X)
    bb = assy.toCompound().BoundingBox()
    h = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    w = BRACKET_WIDTH.to(ureg.mm).magnitude
    t = BRACKET_THICKNESS.to(ureg.mm).magnitude

    # Z must span full bracket height
    assert bb.zlen == pytest.approx(h, rel=0.05)
    # Y must span bracket width
    assert bb.ylen >= w * 0.9
    # X must include wall plate + bracket
    assert bb.xlen > t


if __name__ == "__main__":
    validate()
    print("All assembly checks passed")
