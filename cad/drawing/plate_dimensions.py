"""Add manufacturing dimensions to plate face-view TechDraw views.

Plate geometry: rectangular outer outline + 8 perimeter bolt holes +
N penetrations from spec.yaml. Edges matched by curve type + length.
Tolerances per plate spec.yaml's deployment_context (ISO 2768-m default).

Operates on plain dicts (loaded from spec.yaml YAML) — does NOT depend on
the cadquery-bound model module so it can run inside FreeCAD's bundled
python which has no cadquery.
"""

EDGE_MATCH_TOL = 0.5  # mm

GROUND_STUD_TAP_DRILL_MM = {"M8": 6.8, "M10": 8.5, "M12": 10.2}


def _find_edge_by_length(view, target_length: float) -> str | None:
    """Match a visible Line edge by length within tolerance."""
    edges = view.getVisibleEdges()
    for i, edge in enumerate(edges):
        if type(edge.Curve).__name__ != "Line":
            continue
        if abs(edge.Length - target_length) < EDGE_MATCH_TOL:
            return f"Edge{i}"
    return None


def _find_circles_by_radius(view, target_radius: float) -> list[str]:
    """Find all Circle/BSpline edges matching a radius."""
    edges = view.getVisibleEdges()
    matches = []
    for i, edge in enumerate(edges):
        ctype = type(edge.Curve).__name__
        if ctype not in ("Circle", "BSplineCurve"):
            continue
        if (
            hasattr(edge.Curve, "Radius")
            and abs(edge.Curve.Radius - target_radius) < EDGE_MATCH_TOL
        ):
            matches.append(f"Edge{i}")
    return matches


def _add_dim(
    doc, page, name, dim_type, view, edge, fmt, x: float = 0.0, y: float = 0.0
):
    """Create a dimension, add to page, then set position.

    Reason: addView resets X/Y to defaults. Must set position after.
    """
    dim = doc.addObject("TechDraw::DrawViewDimension", name)
    dim.Type = dim_type
    dim.References2D = [(view, edge)]
    dim.FormatSpec = fmt
    page.addView(dim)
    dim.X = x
    dim.Y = y
    return dim


def _resolve_diameter(pen: dict, params: dict, ctx: dict) -> float:
    """Resolve a penetration's size_driver to actual diameter in mm."""
    driver = pen["size_driver"]
    if driver == "param.power_conduit_od_mm":
        return params["power_conduit_od_mm"]
    if driver == "param.data_conduit_od_mm":
        return params["data_conduit_od_mm"]
    if driver == "context.ground_stud":
        return GROUND_STUD_TAP_DRILL_MM[ctx["ground_stud"]]
    return 0.0


def add_plate_dimensions(doc, page, face_view, spec: dict, params: dict) -> list[str]:
    """Add face-view dimensions: outer width + height + penetrations + bolts."""
    added: list[str] = []
    ctx = spec["deployment_contexts"][params["deployment_context"]]
    long_dim = spec["outer_dims_mm"]["L"]
    wide_dim = spec["outer_dims_mm"]["W"]

    edge = _find_edge_by_length(face_view, wide_dim)
    if edge:
        _add_dim(
            doc,
            page,
            "DimWidth",
            "DistanceX",
            face_view,
            edge,
            "%.0f",
            x=0.0,
            y=-long_dim / 2 - 30,
        )
        added.append("DimWidth")

    edge = _find_edge_by_length(face_view, long_dim)
    if edge:
        _add_dim(
            doc,
            page,
            "DimHeight",
            "DistanceY",
            face_view,
            edge,
            "%.0f",
            x=-wide_dim / 2 - 30,
            y=0.0,
        )
        added.append("DimHeight")

    for i, pen in enumerate(spec["penetration_schedule"]):
        diameter = _resolve_diameter(pen, params, ctx)
        radius = diameter / 2
        circles = _find_circles_by_radius(face_view, radius)
        if not circles:
            continue
        edges = face_view.getVisibleEdges()
        longest = max(circles, key=lambda e: edges[int(e[4:])].Length)
        # Reason: TechDraw needs a %-format token in FormatSpec to render the
        # measured value. Use %.1f and append note text after.
        if pen["id"] == "ground_stud":
            fmt = f"⌀%.1f (M{ctx['ground_stud'][1:]} tap drill)"
        else:
            fmt = f"⌀%.1f ({pen['id']})"
        _add_dim(
            doc,
            page,
            f"DimPen{i}",
            "Diameter",
            face_view,
            longest,
            fmt,
            x=pen["x_mm"] + 60,
            y=pen["y_mm"] + 30,
        )
        added.append(f"DimPen{i}")

    bolts = spec["mounting_bolts"]
    bolt_radius = bolts["diameter_mm"] / 2
    bolt_circles = _find_circles_by_radius(face_view, bolt_radius)
    if bolt_circles:
        edges = face_view.getVisibleEdges()
        longest = max(bolt_circles, key=lambda e: edges[int(e[4:])].Length)
        _add_dim(
            doc,
            page,
            "DimBolt",
            "Diameter",
            face_view,
            longest,
            f"{bolts['count']}X ⌀%.1f H9",
            x=-wide_dim / 2 - 30,
            y=long_dim / 2 - 60,
        )
        added.append("DimBolt")

    doc.recompute()
    return added


def add_view_labels(doc, page, positions: dict[str, tuple[float, float]]) -> list[str]:
    """Add view labels via DrawViewAnnotation (must position AFTER addView)."""
    added = []
    for name, (x, y) in positions.items():
        anno = doc.addObject("TechDraw::DrawViewAnnotation", f"Label{name}")
        anno.Text = [name]
        anno.TextSize = 5.0
        page.addView(anno)
        anno.X = x
        anno.Y = y
        added.append(f"Label{name}")
    doc.recompute()
    return added
