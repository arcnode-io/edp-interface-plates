"""ARCNODE logo engraving on plate +Z faces — reusable across plate types.

Single SVG path → discretized closed subpaths → CadQuery sketch face → extrusion
subtracted from the plate. Even-odd fill rule means nested SVG subpaths read as
holes in the engraving naturally — no manual outer/inner bookkeeping.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Final

import cadquery as cq
from svgpathtools import parse_path

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
LOGO_SVG_PATH: Final[Path] = REPO_ROOT / "assets" / "arcnode-logo.svg"

ENGRAVE_DEPTH_MM: Final[float] = 2.5
LOGO_DEFAULT_WIDTH_MM: Final[float] = 150.0
SAMPLES_PER_SUBPATH: Final[int] = 220

_SVG_NS: Final[dict[str, str]] = {"svg": "http://www.w3.org/2000/svg"}


def _load_subpath_points(
    svg_path: Path, target_width_mm: float
) -> list[list[tuple[float, float]]]:
    """Parse SVG → list of closed subpaths as (x,y) point lists.

    Coords centered on (0,0), y-axis flipped (SVG +Y down → CadQuery +Y up),
    scaled so total width matches `target_width_mm`.
    """
    tree = ET.parse(svg_path)
    p_elem = tree.getroot().find(".//svg:path", _SVG_NS)
    if p_elem is None:
        raise ValueError(f"no <path> element in {svg_path}")
    path = parse_path(p_elem.attrib["d"])
    subs = path.continuous_subpaths()
    if not subs:
        raise ValueError(f"path in {svg_path} has no continuous subpaths")

    boxes = [s.bbox() for s in subs]
    xmin = min(b[0] for b in boxes)
    xmax = max(b[1] for b in boxes)
    ymin = min(b[2] for b in boxes)
    ymax = max(b[3] for b in boxes)
    cx = (xmin + xmax) / 2.0
    cy = (ymin + ymax) / 2.0
    raw_width = xmax - xmin
    if raw_width == 0:
        raise ValueError(f"degenerate path width in {svg_path}")
    scale = target_width_mm / raw_width

    out: list[list[tuple[float, float]]] = []
    for sub in subs:
        pts: list[tuple[float, float]] = []
        for i in range(SAMPLES_PER_SUBPATH + 1):
            p = sub.point(i / SAMPLES_PER_SUBPATH)
            x = (p.real - cx) * scale
            y = -(p.imag - cy) * scale  # Reason: SVG y is down-positive; flip to cq up-positive.
            pts.append((x, y))
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        out.append(pts)
    return out


def engrave_logo(
    plate: cq.Workplane,
    face_z_mm: float,
    *,
    depth_mm: float = ENGRAVE_DEPTH_MM,
    width_mm: float = LOGO_DEFAULT_WIDTH_MM,
    center_xy_mm: tuple[float, float] = (0.0, 0.0),
    outward_normal_z: int = 1,
    svg_path: Path = LOGO_SVG_PATH,
) -> cq.Workplane:
    """Engrave the ARCNODE logo into one face of `plate`.

    Builds a sketch from the SVG's closed subpaths (even-odd fill), extrudes by
    `depth_mm` into the plate from the chosen face, then cuts that solid from
    the plate.

    Args:
        plate: source plate Workplane.
        face_z_mm: world-Z of the face being engraved.
        depth_mm: engrave depth (always positive — direction follows outward_normal_z).
        width_mm: target logo width on the face. Height scales to preserve aspect.
        center_xy_mm: (x, y) where the logo centers on the face.
        outward_normal_z: +1 if the face's outward normal is +Z (engrave top face);
            -1 if outward normal is -Z (engrave bottom face). The sketch is mirrored
            on x when engraving the -Z face so the logo reads correctly from outside.
        svg_path: source SVG.

    Returns:
        Plate Workplane with the logo subtracted.
    """
    if outward_normal_z not in (1, -1):
        raise ValueError(f"outward_normal_z must be +1 or -1; got {outward_normal_z}")
    subs = _load_subpath_points(svg_path, width_mm)
    cx, cy = center_xy_mm
    if outward_normal_z == -1:
        # Mirror x so the logo reads correctly when viewed from the -Z side.
        subs = [[(-x, y) for x, y in pts] for pts in subs]

    sketch = cq.Sketch()
    for pts in subs:
        sketch = sketch.polygon(pts, mode="a")
    sketch = sketch.reset()

    # Cut from face_z inward by depth_mm (sign of inward direction = -outward_normal_z).
    base_z = face_z_mm if outward_normal_z == -1 else face_z_mm - depth_mm
    extrusion = (
        cq.Workplane("XY")
        .placeSketch(sketch)
        .extrude(depth_mm)
        .translate((cx, cy, base_z))
    )
    return plate.cut(extrusion)
