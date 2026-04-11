"""Export engineering drawing as PDF via FreeCAD TechDraw.

Uses individual DrawViewPart objects for full position control.
Export path: TechDraw SVG -> rsvg-convert -> PDF (bypasses Qt's thick
stroke rendering in exportPageAsPdf).

Reads title block and projection config from layout_spec.yaml.
"""

import time
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

Gui.showMainWindow()

import Part  # noqa: E402
import subprocess  # noqa: E402
import TechDrawGui  # noqa: E402
import yaml  # noqa: E402

STEP_FILE = Path("cad/l_bracket.step")
TEMPLATES_DIR = Path("cad/model/templates")
LAYOUT_SPEC_PATH = Path("cad/layout_spec.yaml")
DRAWINGS_DIR = Path("output/drawings")


def _load_spec() -> dict:
    return yaml.safe_load(LAYOUT_SPEC_PATH.read_text())


def _resolve_template(sheet_size: str) -> Path:
    """Pick template SVG based on sheet_size from layout_spec."""
    template = TEMPLATES_DIR / f"{sheet_size}_Landscape_EWAI.svg"
    if not template.exists():
        raise FileNotFoundError(
            f"No template for sheet_size '{sheet_size}': {template}"
        )
    return template


def _export_web_svg(sheet_svg: Path, web_svg: Path) -> None:
    """Strip template (border + title block) from TechDraw SVG.

    Keeps only the DrawingContent group (views + dimensions) and fits
    the viewBox to the content bounding box.
    """
    import xml.etree.ElementTree as ET

    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(sheet_svg)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    page_g = root.find(".//svg:g[@id='Page']", ns)
    if page_g is None:
        return

    # Reason: remove the template group (first child), keep DrawingContent
    for child in list(page_g):
        child_id = child.get("id", "")
        if child_id != "DrawingContent":
            page_g.remove(child)

    # Reason: fit viewBox to content — DrawingContent uses absolute coords
    content = page_g.find("svg:g[@id='DrawingContent']", ns)
    if content is not None:
        root.set("viewBox", "0 0 4200 2970")

    tree.write(web_svg, xml_declaration=True, encoding="UTF-8")
    print(f"Exported {web_svg}")


def _export_dark_svg(web_svg: Path, dark_svg: Path) -> None:
    """Create dark-mode SVG (white lines on transparent background) from web SVG."""
    svg = web_svg.read_text()
    # Reason: swap black strokes/fills to white. Handles both XML attributes
    # (FreeCAD: stroke="black") and CSS properties (KiCad: stroke:#000000).
    # Reason: full black↔white inversion. Placeholder avoids double-swap.
    svg = svg.replace("#ffffff", "#__WHITE__")
    svg = svg.replace("#000000", "#ffffff")
    svg = svg.replace("#__WHITE__", "#000000")
    svg = svg.replace('"black"', '"__BLACK__"')
    svg = svg.replace('"white"', '"black"')
    svg = svg.replace('"__BLACK__"', '"white"')
    # Reason: insert black background rect. CSS background on <svg> is
    # unreliable across viewers, so use an explicit rect element.
    svg = svg.replace(
        '<g fill="none"',
        '<rect width="100%" height="100%" fill="black"/>\n<g fill="none"',
        1,
    )
    dark_svg.write_text(svg)
    print(f"Exported {dark_svg}")


def _wait_for_gui(iterations: int = 10):
    """Wait for FreeCAD HLR and GUI to settle."""
    for _ in range(iterations):
        Gui.updateGui()
        time.sleep(0.3)


def export_drawing() -> Path:
    """Build TechDraw page with auto-layout and export as PDF."""
    spec = _load_spec()
    title_block = spec["title_block"]
    td = spec["techdraw"]
    template_path = _resolve_template(spec["sheet_size"])
    DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)

    doc = App.newDocument("bracket")
    shape = Part.read(str(STEP_FILE))
    part_obj = doc.addObject("Part::Feature", "LBracket")
    part_obj.Shape = shape
    doc.recompute()

    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.KeepUpdated = True
    tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    tmpl.Template = str(template_path)
    page.Template = tmpl

    texts = tmpl.EditableTexts
    texts["title"] = spec["title"]
    texts.update(title_block)
    tmpl.EditableTexts = texts
    doc.recompute()

    # Reason: compute view positions from bounding box + sheet config
    from cad.drawing.layout import compute_layout

    bb = shape.BoundBox
    has_iso = "FrontTopRight" in td["projections"]
    view_defs, scale = compute_layout(
        bb.XLength,
        bb.YLength,
        bb.ZLength,
        spec["sheet_size"],
        td.get("scale", 1.0),
        td.get("padding", 15),
        td.get("gap", 20),
        has_iso,
    )

    if scale != td.get("scale", 1.0):
        print(f"Auto-scaled to {scale:.2f} to fit {spec['sheet_size']} sheet")

    view_objects = {}
    for name, (direction, cx, cy) in view_defs.items():
        v = doc.addObject("TechDraw::DrawViewPart", name)
        page.addView(v)
        v.Source = [part_obj]
        v.Direction = App.Vector(*direction)
        v.Scale = scale
        v.X = cx
        v.Y = cy
        view_objects[name] = v
    doc.recompute()

    # Reason: HLR runs asynchronously — wait for edges before dimensioning.
    _wait_for_gui(10)

    from cad.drawing.dimensions import add_dimensions

    dim_names = add_dimensions(doc, page, view_objects)
    print(f"Added dimensions: {dim_names}")

    # Update scale field in title block
    if scale >= 1:
        texts["scale"] = f"{scale:.0f} : 1"
    else:
        texts["scale"] = f"1 : {1 / scale:.0f}"
    tmpl.EditableTexts = texts
    doc.recompute()

    # Force Qt scene graph to render template border + title block
    page.ViewObject.ForceUpdate = True
    page.ViewObject.doubleClicked()
    _wait_for_gui(15)

    svg_path = Path("/tmp/l_bracket_sheet.svg")
    pdf_path = DRAWINGS_DIR / "l_bracket_drawing.pdf"
    dxf_path = DRAWINGS_DIR / "l_bracket.dxf"

    TechDrawGui.exportPageAsSvg(page, str(svg_path))

    # Reason: strip template (border + title block) for a clean web SVG.
    web_svg = DRAWINGS_DIR / "l_bracket_web.svg"
    _export_web_svg(svg_path, web_svg)
    _export_dark_svg(web_svg, DRAWINGS_DIR / "l_bracket_web_dark.svg")

    # Reason: exportPageAsPdf strokes template text incorrectly (FreeCAD #21096).
    # SVG→rsvg-convert renders title block text at correct weight.
    subprocess.run(
        ["rsvg-convert", "-f", "pdf", str(svg_path), "-o", str(pdf_path)],
        check=True,
    )

    import TechDraw

    TechDraw.writeDXFPage(page, str(dxf_path))

    print(f"Exported {pdf_path} ({pdf_path.stat().st_size} bytes)")
    print(f"Exported {dxf_path} ({dxf_path.stat().st_size} bytes)")
    return pdf_path


if __name__ == "__main__":
    export_drawing()
    App.closeDocument("bracket")
