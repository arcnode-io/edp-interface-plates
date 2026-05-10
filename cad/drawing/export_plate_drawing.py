"""Export plate engineering drawing as PDF via FreeCAD TechDraw.

Plate-aware variant of export_drawing.py — takes a plate_id (CG, BG-AC, ...)
and produces a per-plate A3 PDF + DXF + SVG with face-view + edge-view
+ dimensions per plate spec.yaml.

Usage:
    xvfb-run -a python3 cad/drawing/export_plate_drawing.py --plate-id CG
"""

import argparse
import subprocess
import time
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

Gui.showMainWindow()

import Part  # noqa: E402
import TechDraw  # noqa: E402
import TechDrawGui  # noqa: E402
import yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "cad" / "model" / "templates"
SPECS_DIR = REPO_ROOT / "cad" / "specs"
DRAWINGS_DIR = REPO_ROOT / "output" / "drawings"

# Reason: v1 build params are read from spec.yaml's default_params block —
# single source of truth for every plate. No more per-plate hardcoded dict.
GROUND_STUD_TAP_DRILL_MM = {"M8": 6.8, "M10": 8.5, "M12": 10.2}


def _plate_scale(plate_w_mm: float, plate_h_mm: float) -> float:
    """Pick a scale that makes the TOP face view fit ~half of A1 sheet."""
    # Reason: A1 = 841x594. Left half ~420x520 usable after margins.
    # Aim for plate face ~340x440 (room around for dims).
    target_w_mm = 340.0
    target_h_mm = 440.0
    return min(target_w_mm / plate_w_mm, target_h_mm / plate_h_mm)


# View directions for the face-view + edge-view layout.
# Plate is built in XY plane with thickness extruded along +Z; face view
# looks down +Z (or -Z) to see the outer rectangle + holes.
_FACE_VIEW_DIR = (0, 0, 1)
_EDGE_VIEW_DIR = (1, 0, 0)


def _wait_for_gui(iterations: int = 10) -> None:
    """Wait for FreeCAD HLR + GUI to settle."""
    for _ in range(iterations):
        Gui.updateGui()
        time.sleep(0.3)


def _load_plate_spec(plate_id: str) -> dict:
    """Read cad/specs/{plate_id}/spec.yaml as a plain dict (no Pydantic, no cadquery)."""
    path = SPECS_DIR / plate_id / "spec.yaml"
    return yaml.safe_load(path.read_text())


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


def export_plate_drawing(plate_id: str, deployment_context: str = "commercial") -> Path:
    """Build TechDraw page for the named plate and export as PDF.

    Args:
        plate_id: Plate variant code, e.g. "CG", "BG-AC".
        deployment_context: "commercial" or "defense_forward" / "sovereign_government";
            picks plate-defense.step + appends "-D" to part number + flips notes.

    Returns:
        Path to emitted PDF.
    """
    spec = _load_plate_spec(plate_id)
    params = dict(spec["default_params"])
    params["deployment_context"] = deployment_context

    DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
    step_suffix = "" if deployment_context == "commercial" else "-defense"
    step_path = REPO_ROOT / "cad" / "specs" / plate_id / f"plate{step_suffix}.step"
    if not step_path.exists():
        raise FileNotFoundError(
            f"plate STEP not found at {step_path}; "
            f"run `python cad/model/build.py --plate-id {plate_id} "
            f"--deployment-context {deployment_context}` first"
        )

    # Reason: A1 (841×594mm) gives ~2× the layout headroom of A3. Easier
    # to clear ISO from title block, dim text from views, notes from edges.
    template_path = TEMPLATES_DIR / "A1_Landscape_EWAI.svg"
    doc_name = plate_id.replace("-", "_").lower()
    doc = App.newDocument(doc_name)
    shape = Part.read(str(step_path))
    part_obj = doc.addObject("Part::Feature", plate_id.replace("-", ""))
    part_obj.Shape = shape
    doc.recompute()

    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.KeepUpdated = True
    tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    tmpl.Template = str(template_path)
    page.Template = tmpl

    ctx = spec["deployment_contexts"][params["deployment_context"]]
    pn = f"ARC-PLT-{plate_id}-{params['revision']}"
    if params["deployment_context"] != "commercial":
        pn += "-D"
    texts = tmpl.EditableTexts
    texts.update(
        {
            "title": spec["description"],
            "creator": "ARCNODE",
            "document_type": "Fab Drawing",
            "approval_person": "Joe Narvaez, EIT",
            "identification_number": pn,
            "part_material": ctx["material"],
            "revision_index": params["revision"],
            "legal_owner_1": "ARCNODE",
            "legal_owner_2": "Hardware",
            "scale": "1 : 5",
            "general_tolerance": "ISO 2768-m",
            "surface_finish": ctx["finish"],
        }
    )
    tmpl.EditableTexts = texts
    doc.recompute()

    bb = shape.BoundBox
    # Plate-specific layout for A3 landscape (420x297, title block 58mm at bottom).
    # Plates are flat (thickness << face dims), so compute_layout's 3D-part
    # heuristic positions views off-page. Override with face-dominant layout.
    scale = _plate_scale(bb.XLength, bb.YLength)
    # A1 landscape = 841×594. Title block bottom-right.
    face_cx, face_cy = 220, 320  # TOP face on left half
    edge_cx, edge_cy = 600, 480  # FRONT thickness sliver top-right
    iso_cx, iso_cy = 620, 300  # ISO mid-right
    iso_scale_factor = 0.6

    view_specs = [
        ("TOP", (0, 0, 1), face_cx, face_cy),
        ("FRONT", (0, -1, 0), edge_cx, edge_cy),
        ("ISOMETRIC", (1, -1, 1), iso_cx, iso_cy),
    ]
    view_objects = {}
    for name, direction, cx, cy in view_specs:
        v = doc.addObject("TechDraw::DrawViewPart", name)
        # Reason: set Source + Direction + Scale BEFORE addView so HLR
        # initialization sees the right source. addView before configure
        # caused getVisibleEdges to return only ~13 edges (plate has ~30+).
        v.Source = [part_obj]
        v.Direction = App.Vector(*direction)
        v.ScaleType = "Custom"
        v.Scale = scale * iso_scale_factor if name == "ISOMETRIC" else scale
        page.addView(v)
        v.X = cx
        v.Y = cy
        view_objects[name] = v
    texts["scale"] = f"1 : {round(1 / scale)}"
    tmpl.EditableTexts = texts
    doc.recompute()
    face = view_objects["TOP"]

    _wait_for_gui(10)

    from cad.drawing.plate_dimensions import (
        add_detail_view,
        add_notes_block,
        add_plate_dimensions,
        add_thickness_dimension,
        add_view_labels,
    )

    dim_names = add_plate_dimensions(
        doc, page, face, spec, params, view_cx=face_cx, view_cy=face_cy
    )
    front_view = view_objects.get("FRONT")
    if front_view is not None:
        thick_name = add_thickness_dimension(doc, page, front_view, spec, params)
        if thick_name:
            dim_names.append(thick_name)
    # DETAIL view at top-right corner slot (model coords).
    bolts_spec = spec["mounting_bolts"]
    inset = bolts_spec["inset_mm"]
    detail_anchor_x = bb.XLength / 2 - inset
    detail_anchor_y = bb.YLength / 2 - inset
    _detail_view, detail_dims = add_detail_view(
        doc,
        page,
        face,
        spec,
        anchor_x=detail_anchor_x,
        anchor_y=detail_anchor_y,
    )
    dim_names.extend(detail_dims)
    notes_name = add_notes_block(doc, page, params)
    dim_names.append(notes_name)
    label_positions = {name: (cx, cy - 50) for name, _direction, cx, cy in view_specs}
    label_names = add_view_labels(doc, page, label_positions)
    print(f"Added: {dim_names + label_names}")

    page.ViewObject.ForceUpdate = True
    page.ViewObject.doubleClicked()
    _wait_for_gui(15)

    out_suffix = "" if deployment_context == "commercial" else "-defense"
    svg_path = Path(f"/tmp/{plate_id}{out_suffix}_sheet.svg")
    pdf_path = DRAWINGS_DIR / f"{plate_id}{out_suffix}_drawing.pdf"
    dxf_path = DRAWINGS_DIR / f"{plate_id}{out_suffix}.dxf"

    TechDrawGui.exportPageAsSvg(page, str(svg_path))
    subprocess.run(
        ["rsvg-convert", "-f", "pdf", str(svg_path), "-o", str(pdf_path)], check=True
    )
    TechDraw.writeDXFPage(page, str(dxf_path))

    print(f"Exported {pdf_path} ({pdf_path.stat().st_size} bytes)")
    print(f"Exported {dxf_path} ({dxf_path.stat().st_size} bytes)")
    App.closeDocument(doc_name)
    return pdf_path


def main() -> None:
    """CLI entry: export plate drawing for a given plate-id."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plate-id", required=True, help="Plate variant: CG, BG-AC, ..."
    )
    parser.add_argument(
        "--deployment-context",
        choices=("commercial", "defense_forward", "sovereign_government"),
        default="commercial",
        help="Pick STEP variant + per-context notes/title.",
    )
    args = parser.parse_args()
    export_plate_drawing(args.plate_id, deployment_context=args.deployment_context)


if __name__ == "__main__":
    main()
