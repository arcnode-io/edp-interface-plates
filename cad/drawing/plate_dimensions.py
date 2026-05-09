"""Add manufacturing dimensions to plate TechDraw views.

Plate geometry: rectangular outer outline + 8 perimeter bolt positions
(2 round, 6 slotted at 13×Ø11 per ADR-015) + N penetrations from
spec.yaml. Edges matched by curve type + length.
Tolerances per spec.yaml's deployment_context. Per-context drawings
emit separately (commercial vs defense; no alt-note hedging).

Operates on plain dicts (loaded from spec.yaml YAML) — does NOT depend on
the cadquery-bound model module so it can run inside FreeCAD's bundled
python which has no cadquery.
"""

EDGE_MATCH_TOL = 0.5  # mm

GROUND_STUD_TAP_DRILL_MM = {"M10": 8.5, "M12": 10.2}

# Reason: ISO 286-2 H10 over-tolerance per nominal-diameter range, used for
# penetration clearance fits. H9 for bolt holes is hardcoded at 0.036 below.
H10_OVER_TOL_MM = {
    (6, 10): 0.058,
    (10, 18): 0.070,
    (18, 30): 0.084,
    (30, 50): 0.100,
    (50, 80): 0.120,
    (80, 120): 0.140,
}


def _h10_tol(diameter_mm: float) -> float:
    """ISO 286-2 H10 over-tolerance for a given nominal diameter."""
    for (lo, hi), tol in H10_OVER_TOL_MM.items():
        if lo < diameter_mm <= hi:
            return tol
    return 0.140  # fallback for >120mm


def _view_scale(view) -> float:
    """Read view's render scale. ScaleType=Custom uses view.Scale directly."""
    scale = getattr(view, "Scale", 1.0)
    return float(scale) if scale else 1.0


def _find_edge_by_length(view, target_length: float) -> str | None:
    """Match visible Line edge by length. Edges in render-space (scaled);
    target is model-space mm — scale target before compare."""
    scale = _view_scale(view)
    target_scaled = target_length * scale
    edges = view.getVisibleEdges()
    for i, edge in enumerate(edges):
        if type(edge.Curve).__name__ != "Line":
            continue
        if abs(edge.Length - target_scaled) < EDGE_MATCH_TOL:
            return f"Edge{i}"
    return None


def _find_circles_by_radius(view, target_radius: float) -> list[str]:
    """Find Circle/BSpline edges matching a model-space radius (scaled internally)."""
    scale = _view_scale(view)
    target_scaled = target_radius * scale
    edges = view.getVisibleEdges()
    matches = []
    for i, edge in enumerate(edges):
        ctype = type(edge.Curve).__name__
        if ctype not in ("Circle", "BSplineCurve"):
            continue
        if (
            hasattr(edge.Curve, "Radius")
            and abs(edge.Curve.Radius - target_scaled) < EDGE_MATCH_TOL
        ):
            matches.append(f"Edge{i}")
    return matches


def _add_dim(
    doc,
    page,
    name,
    dim_type,
    view,
    edge,
    fmt,
    x: float = 0.0,
    y: float = 0.0,
    over_tol: float | None = None,
    under_tol: float | None = None,
):
    """Create a dimension, add to page, then set position.

    Reason: addView resets X/Y to defaults. Must set position after.
    """
    dim = doc.addObject("TechDraw::DrawViewDimension", name)
    dim.Type = dim_type
    dim.References2D = [(view, edge)]
    dim.FormatSpec = fmt
    if over_tol is not None:
        dim.OverTolerance = over_tol
    if under_tol is not None:
        dim.UnderTolerance = under_tol
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

    # Reason: dim X/Y are page-absolute mm; defaulting to 0,0 lets TechDraw
    # auto-place near the dimensioned edge. Override only when auto-placement
    # produces overlap (refined in visual review iterations).
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
        )
        added.append("DimHeight")

    # Reason: dump curve types + radii once for diagnostic visibility on
    # which penetrations got matched.
    scale = _view_scale(face_view)
    visible = face_view.getVisibleEdges()
    hidden = []
    if hasattr(face_view, "getHiddenEdges"):
        try:
            hidden = face_view.getHiddenEdges()
        except Exception:
            hidden = []
    print(
        f"[plate_dimensions] view scale={scale:.4f}; "
        f"{len(visible)} visible + {len(hidden)} hidden edges"
    )
    for i, e in enumerate(visible):
        ctype = type(e.Curve).__name__
        r = getattr(e.Curve, "Radius", None)
        if r is not None:
            print(f"  Edge{i}: {ctype} r={r:.3f} " f"(model r={r / scale:.2f})")
        else:
            print(f"  Edge{i}: {ctype} L={e.Length:.2f}")
    for i, e in enumerate(hidden):
        ctype = type(e.Curve).__name__
        r = getattr(e.Curve, "Radius", None)
        if r is not None:
            print(f"  Hidden{i}: {ctype} r={r:.3f} " f"(model r={r / scale:.2f})")
        else:
            print(f"  Hidden{i}: {ctype} L={e.Length:.2f}")

    for i, pen in enumerate(spec["penetration_schedule"]):
        diameter = _resolve_diameter(pen, params, ctx)
        radius = diameter / 2
        circles = _find_circles_by_radius(face_view, radius)
        if not circles:
            print(
                f"[plate_dimensions] no match for {pen['id']} "
                f"(r={radius:.2f} model, scaled={radius * scale:.3f})"
            )
            continue
        edges = face_view.getVisibleEdges()
        longest = max(circles, key=lambda e: edges[int(e[4:])].Length)
        # Reason: TechDraw needs a %-format token in FormatSpec to render the
        # measured value. ground_stud is tap-drill (no fit class); other
        # penetrations are H10 clearance fit per ADR-015 (H10 doesn't bias
        # seal toward leakage like H11 would).
        if pen["id"] == "ground_stud":
            stud_size = ctx["ground_stud"]  # "M10" or "M12"
            fmt = f"⌀%.1f TAP {stud_size} THRU"
            over_tol = None
        else:
            fmt = f"⌀%.1f H10 ({pen['id']})"
            over_tol = _h10_tol(diameter)
        _add_dim(
            doc,
            page,
            f"DimPen{i}Diam",
            "Diameter",
            face_view,
            longest,
            fmt,
            over_tol=over_tol,
            under_tol=0.0 if over_tol is not None else None,
        )
        added.append(f"DimPen{i}Diam")

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
            over_tol=0.036,  # H9 for 6-30mm range
            under_tol=0.0,
        )
        added.append("DimBolt")

    # Slot callout text annotation (no edge match). Detail view (later iter)
    # carries the formal slot dims; this is the TOP-view summary.
    # Position: page-absolute mm. Place between TOP view (left half) and
    # ISO/FRONT views (right half), above title block.
    slot_length_mm = bolts.get("slot_length_mm")
    if slot_length_mm is not None:
        slot_note = doc.addObject("TechDraw::DrawViewAnnotation", "SlotNote")
        slot_note.Text = [
            f"SLOT {int(slot_length_mm)}x⌀{int(bolts['diameter_mm'])} H9",
            "RADIAL TOWARD PATTERN CENTER",
            "TYP 6 PLACES",
            "(4 corners + 2 long-axis midpoints)",
        ]
        slot_note.TextSize = 3.0
        page.addView(slot_note)
        # A1 landscape (841×594). Place between TOP (left) and FRONT/ISO (right),
        # above title block.
        slot_note.X = 460.0
        slot_note.Y = 150.0
        added.append("SlotNote")

    doc.recompute()
    return added


def add_thickness_dimension(
    doc, page, front_view, spec: dict, params: dict
) -> str | None:
    """Add plate thickness dim on FRONT view (edge-thickness sliver)."""
    ctx = spec["deployment_contexts"][params["deployment_context"]]
    thickness_mm = ctx["thickness_mm"]
    edge = _find_edge_by_length(front_view, thickness_mm)
    if not edge:
        return None
    _add_dim(
        doc,
        page,
        "DimThickness",
        "DistanceY",
        front_view,
        edge,
        "%.0f",
        x=30.0,
        y=0.0,
    )
    doc.recompute()
    return "DimThickness"


def add_notes_block(doc, page, params: dict) -> str:
    """Add fab notes block (left of title block).

    Notes 1-5 commercial; +6 defense (EPDM secondary seal).
    Note 6 references MIL-DTL-XXXX placeholder — flag for spec lookup
    before drawing release.
    """
    notes_text = [
        "NOTES:",
        "1. MATERIAL PER TITLE BLOCK",
        "2. ANODIZE PER TITLE BLOCK (AFTER MACHINING)",
        "3. DEBURR ALL EDGES; BREAK SHARP CORNERS 0.3mm x 45 deg",
        "4. GENERAL TOLERANCE PER TITLE BLOCK",
        "5. GROUND STUD: TAP PER TITLE BLOCK (M10 COMMERCIAL / M12 DEFENSE)",
    ]
    if params["deployment_context"] != "commercial":
        # Reason: PM 2026-05-09 noted MIL-DTL-XXXX is a placeholder to be
        # resolved before drawing release. Flag visually in the note text.
        notes_text.append("6. APPLY EPDM SECONDARY SEAL PER MIL-DTL-XXXX [SPEC TBD]")
    notes = doc.addObject("TechDraw::DrawViewAnnotation", "Notes")
    notes.Text = notes_text
    notes.TextSize = 3.0
    page.addView(notes)
    # Page-absolute mm. Notes top-left corner; A3 sheet is 420x297. Drawing
    # space frame at x>=20, y>=10. Title block at bottom-right.
    # A1 landscape (841×594). Notes block top-left of usable area.
    notes.X = 50.0
    notes.Y = 480.0
    doc.recompute()
    return "Notes"


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
