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

# v1 build params hardcoded per plate — match cad/model/{plate}.py V1_COMMERCIAL_PARAMS.
# These drive penetration diameter resolution. Future: pass via CLI or read from sidecar.
_V1_PARAMS_BY_PLATE = {
    "CG": {
        "power_conduit_od_mm": 73.0,
        "data_conduit_od_mm": 35.0,
        "deployment_context": "commercial",
        "revision": "001",
    },
    "BG-AC": {
        "power_conduit_od_mm": 100.0,
        "data_conduit_od_mm": 35.0,
        "deployment_context": "commercial",
        "revision": "001",
    },
}

GROUND_STUD_TAP_DRILL_MM = {"M8": 6.8, "M10": 8.5, "M12": 10.2}


def _plate_scale(plate_w_mm: float, plate_h_mm: float) -> float:
    """Pick a scale that makes the face view fit ~half of A3 with margins."""
    # Reason: A3 = 420x297, title block 58mm. Left half usable ~190x230.
    # Allow 10mm margin on each side.
    target_w_mm = 170.0
    target_h_mm = 220.0
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


def export_plate_drawing(plate_id: str) -> Path:
    """Build TechDraw page for the named plate and export as PDF.

    Args:
        plate_id: Plate variant code, e.g. "CG", "BG-AC".

    Returns:
        Path to emitted PDF.
    """
    spec = _load_plate_spec(plate_id)
    params = _V1_PARAMS_BY_PLATE[plate_id]

    DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
    step_path = REPO_ROOT / "cad" / f"{plate_id}.step"
    if not step_path.exists():
        raise FileNotFoundError(
            f"plate STEP not found at {step_path}; run cad/model/{plate_id.lower()}.py first"
        )

    template_path = TEMPLATES_DIR / "A3_Landscape_EWAI.svg"
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
            "drawing_number": pn,
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
    face_cx, face_cy = 110, 180  # TOP view = face, left half
    edge_cx, edge_cy = 320, 235  # FRONT view = edge thickness sliver, right top
    iso_cx, iso_cy = 320, 130  # ISOMETRIC for context, right bottom

    view_specs = [
        ("TOP", (0, 0, 1), face_cx, face_cy),
        ("FRONT", (0, -1, 0), edge_cx, edge_cy),
        ("ISOMETRIC", (1, -1, 1), iso_cx, iso_cy),
    ]
    view_objects = {}
    for name, direction, cx, cy in view_specs:
        v = doc.addObject("TechDraw::DrawViewPart", name)
        page.addView(v)
        v.Source = [part_obj]
        v.Direction = App.Vector(*direction)
        v.Scale = scale
        v.X = cx
        v.Y = cy
        view_objects[name] = v
    texts["scale"] = f"1 : {round(1 / scale)}"
    tmpl.EditableTexts = texts
    doc.recompute()
    face = view_objects["TOP"]

    _wait_for_gui(10)

    from cad.drawing.plate_dimensions import add_plate_dimensions, add_view_labels

    dim_names = add_plate_dimensions(doc, page, face, spec, params)
    label_positions = {name: (cx, cy - 50) for name, _direction, cx, cy in view_specs}
    label_names = add_view_labels(doc, page, label_positions)
    print(f"Added: {dim_names + label_names}")

    page.ViewObject.ForceUpdate = True
    page.ViewObject.doubleClicked()
    _wait_for_gui(15)

    svg_path = Path(f"/tmp/{plate_id}_sheet.svg")
    pdf_path = DRAWINGS_DIR / f"{plate_id}_drawing.pdf"
    dxf_path = DRAWINGS_DIR / f"{plate_id}.dxf"

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
    args = parser.parse_args()
    export_plate_drawing(args.plate_id)


if __name__ == "__main__":
    main()
