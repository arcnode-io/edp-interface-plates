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
    edge2: str | None = None,
):
    """Create a dimension, add to page, then set position.

    Reason: addView resets X/Y to defaults. Must set position after.
    Pass edge2 to make a 2-reference dim (e.g. DistanceX between a circle
    and a vertical edge → ordinate position from datum).
    """
    dim = doc.addObject("TechDraw::DrawViewDimension", name)
    dim.Type = dim_type
    refs = [(view, edge)]
    if edge2 is not None:
        refs.append((view, edge2))
    dim.References2D = refs
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


def add_plate_dimensions(
    doc,
    page,
    face_view,
    spec: dict,
    params: dict,
    *,
    view_cx: float = 220.0,
    view_cy: float = 320.0,
) -> list[str]:
    """Add face-view dimensions: outer width + height + penetrations + bolts.

    Args:
        view_cx, view_cy: TOP view center in page mm; used to place dim text
            in the empty regions around each feature.
    """
    added: list[str] = []
    ctx = spec["deployment_contexts"][params["deployment_context"]]
    long_dim = spec["outer_dims_mm"]["L"]
    wide_dim = spec["outer_dims_mm"]["W"]

    # Reason: dim X/Y are page-absolute mm; defaulting to 0,0 lets TechDraw
    # auto-place near the dimensioned edge. Override only when auto-placement
    # produces overlap (refined in visual review iterations).
    scale = _view_scale(face_view)

    def page_xy(model_x: float, model_y: float) -> tuple[float, float]:
        """Convert plate-local mm to page-absolute mm via view scale + offset."""
        return (view_cx + model_x * scale, view_cy + model_y * scale)

    # Reason: dim.X/Y is OFFSET from default placement, not absolute. Leaving
    # at default (0,0) lets TechDraw auto-place near the dim line. Visual
    # review iterations override with small (~10mm) bumps when overlaps occur.
    # Position outer dims outside plate body so they don't pile on view center.
    half_w = wide_dim / 2 * scale
    half_h = long_dim / 2 * scale
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
            y=-half_h - 25.0,
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
            x=half_w + 25.0,
            y=0.0,
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
        # Reason: text is center-anchored. Bump = radius + 8mm pad + half-text-width
        # so even the leading edge of the text clears the hole.
        arrow_bump_mm = max(30.0, radius * scale + 30.0)
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
        # Reason: TechDraw default-places dim text at VIEW CENTER. dim.X/Y is
        # offset from that center. To get short arrows + non-piling text:
        # bump OUTWARD from feature center (away from plate center). For
        # mirrored pen pairs (e.g. BG-AC power_conduit_left/_right) outward
        # bump diverges them. Ground_stud overrides to NE so text clears the
        # BL corner bolt that always sits near it.
        feat_x = pen["x_mm"] * scale
        feat_y = pen["y_mm"] * scale
        if pen["id"] == "ground_stud":
            # NE override: ground typically at BL → bump NE clears the BL
            # corner bolt that sits ~60mm away.
            sx, sy = 1.0, 1.0
        else:
            # X outward (sign matches feat_x) so mirrored pairs diverge.
            # Y toward horizontal center (opposite sign of feat_y) so text
            # sits inside plate body, not in narrow top/bottom margin.
            sx = 1.0 if feat_x >= 0 else -1.0
            sy = -1.0 if feat_y > 0 else (1.0 if feat_y < 0 else -1.0)
        x = feat_x + sx * arrow_bump_mm
        y = feat_y + sy * arrow_bump_mm
        _add_dim(
            doc,
            page,
            f"DimPen{i}Diam",
            "Diameter",
            face_view,
            longest,
            fmt,
            x=x,
            y=y,
            over_tol=over_tol,
            under_tol=0.0 if over_tol is not None else None,
        )
        added.append(f"DimPen{i}Diam")

        # Reason: per-pen position labels overlap diameter dim text. Consolidate
        # into a single position block near the bolt block (built after loop).

    bolts = spec["mounting_bolts"]
    bolt_radius_local = bolts["diameter_mm"] / 2
    bolt_circles = _find_circles_by_radius(face_view, bolt_radius_local)
    if bolt_circles:
        edges = face_view.getVisibleEdges()
        longest = max(bolt_circles, key=lambda e: edges[int(e[4:])].Length)
        # Reason: anchor at the matched bolt's actual view position so arrow
        # stays short. Edge curve centers are in render-space (already scaled).
        matched_edge = edges[int(longest[4:])]
        center = matched_edge.Curve.Center
        bump = bolt_radius_local * scale + 25.0
        x, y = center.x + bump, center.y + bump
        _add_dim(
            doc,
            page,
            "DimBolt",
            "Diameter",
            face_view,
            longest,
            f"{bolts['count']}X ⌀%.1f H9",
            x=x,
            y=y,
            over_tol=0.036,  # H9 for 6-30mm range
            under_tol=0.0,
        )
        added.append("DimBolt")

        # Reason: per-bolt annotations clutter / overlap features. Consolidated
        # position block (penetrations + bolts) built below.
        x_outer = wide_dim / 2 - bolts["inset_mm"]
        y_outer = long_dim / 2 - bolts["inset_mm"]
        pos_block = doc.addObject("TechDraw::DrawViewAnnotation", "PositionBlock")
        lines = ["POSITIONS (FROM DATUM B/C, mm):", "  PENETRATIONS:"]
        lines.extend(
            f"    {pen['id']:<22}X={pen['x_mm']:+.0f}  Y={pen['y_mm']:+.0f}"
            for pen in spec["penetration_schedule"]
        )
        lines += [
            "  BOLTS:",
            f"    CORNERS (4):           X=±{int(x_outer)}  Y=±{int(y_outer)}",
            f"    LONG-AXIS MID (2):     X=0     Y=±{int(y_outer)}",
            f"    SHORT-AXIS MID (2):    X=±{int(x_outer)}  Y=0",
        ]
        pos_block.Text = lines
        pos_block.TextSize = 2.8
        page.addView(pos_block)
        # Reason: position block belongs in margin, not on plate body. Place
        # in bottom-center strip between DETAIL view (X≈100-340) and title
        # block (X>590), above the page footer. Clear of all plate features.
        pos_block.X = 470.0
        pos_block.Y = 70.0
        added.append("PositionBlock")

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
    # A1 landscape (841×594). Notes block top-left of usable area. Text is
    # CENTERED on X — anchor at X=120 so 80mm-wide content fits within sheet.
    notes.X = 120.0
    notes.Y = 480.0
    doc.recompute()
    return "Notes"


def add_detail_view(
    doc, page, base_view, spec: dict, *, anchor_x: float, anchor_y: float
) -> tuple[str, list[str]]:
    """Add 2:1 DETAIL view at corner slot with slot dims + TYP annotation.

    Returns (detail_view_name, list_of_added_dim_names).
    """
    import time

    import FreeCAD as App
    import FreeCADGui as Gui

    bolts = spec["mounting_bolts"]
    slot_length_mm = bolts.get("slot_length_mm")
    if slot_length_mm is None:
        return "", []

    detail = doc.addObject("TechDraw::DrawViewDetail", "DetailSlot")
    detail.BaseView = base_view
    # AnchorPoint is in BASE-VIEW model coordinates (mm), not scaled.
    detail.AnchorPoint = App.Vector(anchor_x, anchor_y, 0)
    detail.Radius = 15.0  # capture slot 13×11 — tight crop to maximize visibility
    detail.ScaleType = "Custom"
    detail.Scale = 4.0  # 4:1 — at base 1:5, detail effectively 1:1.25 → highly readable
    page.addView(detail)
    # Place at bottom-left A1 area, with vertical headroom for label + dims.
    detail.X = 220.0
    detail.Y = 130.0
    doc.recompute()
    # Reason: HLR runs async; getVisibleEdges() returns empty until GUI ticks.
    for _ in range(10):
        Gui.updateGui()
        time.sleep(0.3)

    bolt_diam = bolts["diameter_mm"]
    added: list[str] = []

    # Reason: TechDraw Distance dim on slot side measures (length - diameter) =
    # 2mm, not the 13mm total. Slot total carried by slot_note + TYP annotation.

    # Slot width (end-cap circle, radius = bolt_diameter / 2).
    cap_circles = _find_circles_by_radius(detail, bolt_diam / 2)
    if cap_circles:
        # Slot width dim text RIGHT of detail content.
        _add_dim(
            doc,
            page,
            "DimSlotWidth",
            "Diameter",
            detail,
            cap_circles[0],
            "⌀%.1f H9",
            over_tol=0.036,
            under_tol=0.0,
            x=55.0,
            y=0.0,
        )
        added.append("DimSlotWidth")

    typ_anno = doc.addObject("TechDraw::DrawViewAnnotation", "DetailTyp")
    typ_anno.Text = [
        "TYP 6 PLACES",
        "(4 CORNERS + 2 LONG-AXIS MIDPOINTS)",
        "SLOT ORIENTED RADIALLY TOWARD PATTERN CENTER",
    ]
    typ_anno.TextSize = 2.8
    page.addView(typ_anno)
    # Place TYP block well below detail + slot dim text so no overlap.
    typ_anno.X = 220.0
    typ_anno.Y = 40.0
    added.append("DetailTyp")

    label = doc.addObject("TechDraw::DrawViewAnnotation", "LabelDETAIL")
    label.Text = ["DETAIL A  (4:1)"]
    label.TextSize = 5.0
    page.addView(label)
    # Label ABOVE detail content.
    label.X = 220.0
    label.Y = 195.0
    added.append("LabelDETAIL")

    doc.recompute()
    return "DetailSlot", added


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
