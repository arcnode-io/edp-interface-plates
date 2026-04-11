"""Parametric L-bracket geometry via CadQuery.

Generates an L-bracket with fillet and bolt holes, exports to STEP.
"""

import cadquery as cq

from sim.constants import (
    BOLT_SPACING,
    BRACKET_THICKNESS,
    BRACKET_WIDTH,
    FILLET_RADIUS,
    HOLE_DIAMETER,
    HORIZONTAL_LEG_LENGTH,
    VERTICAL_LEG_HEIGHT,
    ureg,
)

STEP_PATH = "cad/l_bracket.step"


def build_bracket() -> cq.Workplane:
    """Build L-bracket: XZ profile sketch, extrude Y, fillet inner bend, cut bolt holes."""
    h = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    l = HORIZONTAL_LEG_LENGTH.to(ureg.mm).magnitude
    t = BRACKET_THICKNESS.to(ureg.mm).magnitude
    w = BRACKET_WIDTH.to(ureg.mm).magnitude
    r = FILLET_RADIUS.to(ureg.mm).magnitude
    d_hole = HOLE_DIAMETER.to(ureg.mm).magnitude
    bolt_sp = BOLT_SPACING.to(ureg.mm).magnitude

    # Reason: L-profile in XZ plane, origin at outer corner of bend
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(l + t, 0)
        .lineTo(l + t, t)
        .lineTo(t, t)
        .lineTo(t, h)
        .lineTo(0, h)
        .close()
    )

    bracket = profile.extrude(w)

    # Reason: fillet only the inner bend edge at position (t, t)
    bracket = (
        bracket.edges("|Y").filter(lambda edge: _is_inner_bend_edge(edge, t)).fillet(r)
    )

    # Reason: cut bolt holes through vertical leg using explicit 3D positions.
    # Bracket extrudes in -Y, so Y center = -w/2.
    # Bolt holes centered on vertical leg, spaced vertically about h/2.
    hole_center_x = t / 2
    hole_center_y = -w / 2
    hole_z_lower = h / 2 - bolt_sp / 2
    hole_z_upper = h / 2 + bolt_sp / 2

    for z_pos in [hole_z_lower, hole_z_upper]:
        hole_cyl = (
            cq.Workplane("YZ")
            .workplane(offset=hole_center_x)
            .center(hole_center_y, z_pos)
            .circle(d_hole / 2)
            .extrude(t + 1, both=True)
        )
        bracket = bracket.cut(hole_cyl)

    return bracket


def _is_inner_bend_edge(edge, thickness: float) -> bool:
    """Check if edge is at the inner bend corner position (t, t)."""
    bb = edge.BoundingBox()
    tol = 0.1
    x_match = abs(bb.xmin - thickness) < tol and abs(bb.xmax - thickness) < tol
    z_match = abs(bb.zmin - thickness) < tol and abs(bb.zmax - thickness) < tol
    return x_match and z_match


if __name__ == "__main__":
    bracket = build_bracket()
    bracket.export(STEP_PATH)
    print(f"Exported bracket to {STEP_PATH}")
