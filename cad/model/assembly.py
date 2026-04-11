"""L-bracket assembly: bracket + wall plate + 2 simplified bolts.

Generates a CadQuery Assembly and exports to STEP for visualization.
"""

import cadquery as cq

from sim.constants import (
    BOLT_DIAMETER,
    BOLT_SPACING,
    BRACKET_THICKNESS,
    BRACKET_WIDTH,
    VERTICAL_LEG_HEIGHT,
    ureg,
)

ASSY_STEP_PATH = "cad/l_bracket_assy.step"


def build_wall_plate() -> cq.Workplane:
    """Build wall plate that the bracket bolts to."""
    h = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    w = BRACKET_WIDTH.to(ureg.mm).magnitude
    plate_t = 10.0  # mm, typical wall plate thickness

    return (
        cq.Workplane("XZ").box(plate_t, w, h).translate((-plate_t / 2, -w / 2, h / 2))
    )


def build_bolt() -> cq.Workplane:
    """Build simplified bolt: cylinder shank + hex head."""
    d = BOLT_DIAMETER.to(ureg.mm).magnitude
    t = BRACKET_THICKNESS.to(ureg.mm).magnitude
    shank_length = t + 15.0  # mm, through bracket + plate + nut
    head_height = 5.5  # mm, M8 hex head height
    head_af = 13.0  # mm, M8 across-flats

    shank = cq.Workplane("XY").circle(d / 2).extrude(shank_length)
    head = cq.Workplane("XY").polygon(6, head_af / (3**0.5 / 2)).extrude(-head_height)

    return shank.union(head)


def build_assembly() -> cq.Assembly:
    """Assemble bracket, wall plate, and 2 bolts."""
    from cad.model.model import build_bracket

    h = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    w = BRACKET_WIDTH.to(ureg.mm).magnitude
    t = BRACKET_THICKNESS.to(ureg.mm).magnitude
    bolt_sp = BOLT_SPACING.to(ureg.mm).magnitude

    assy = cq.Assembly(name="l_bracket_assy")

    # Bracket at origin (as built)
    assy.add(build_bracket(), name="bracket", color=cq.Color("steelblue"))

    # Wall plate behind vertical leg
    assy.add(build_wall_plate(), name="wall_plate", color=cq.Color("gray"))

    # Bolts through vertical leg holes
    bolt_x = t / 2
    bolt_y = -w / 2
    for i, z_pos in enumerate([h / 2 - bolt_sp / 2, h / 2 + bolt_sp / 2]):
        assy.add(
            build_bolt(),
            name=f"bolt_{i + 1}",
            loc=cq.Location((bolt_x, bolt_y, z_pos), (0, 90, 0)),
            color=cq.Color(0.4, 0.4, 0.4),
        )

    return assy


if __name__ == "__main__":
    assy = build_assembly()
    assy.export(ASSY_STEP_PATH)
    print(f"Exported assembly to {ASSY_STEP_PATH}")
