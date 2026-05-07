"""Generic plate drawing pipeline — DXF + JSON metadata sidecar.

Shared across CG, BG-AC, EX-* variants. Per-variant wrappers under
`cad/drawing/{plate_id_lower}.py` supply the plate_id + paths.
Full GD&T deferred — needs explicit GD&T scheme (datum refs, tolerance
bands, surface finish symbols) which autonomous code shouldn't author.
"""

import json
from pathlib import Path
from typing import Final

import cadquery as cq

from cad.model._plate import PlateBuildParams, PlateSpec

# Reason: ISO 2768-m carried over from L-bracket template default.
GENERAL_TOLERANCE: Final[str] = "ISO 2768-m"

DEFERRED_DRAWING_FEATURES: Final[list[str]] = [
    "GD&T tolerance callouts on penetration positions",
    "Datum reference frame + ASME Y14.5 symbols",
    "Surface finish callouts",
    "Integrated PDF composition with title block template",
]


def _project_face_view(plate: cq.Workplane) -> cq.Workplane:
    """Extract the >Z face for DXF export (face-view fab drawing)."""
    # Reason: section the plate at mid-thickness so penetrations show through;
    # cadquery DXF export needs a 2D wire profile, not a 3D solid.
    return plate.faces(">Z").workplane().section()


def export_dxf(plate: cq.Workplane, out_path: Path) -> Path:
    """Export plate face view to DXF."""
    face_view = _project_face_view(plate)
    cq.exporters.export(face_view, str(out_path))
    return out_path


def build_drawing_metadata(
    plate_id: str, params: PlateBuildParams, spec: PlateSpec
) -> dict:
    """Assemble title-block + tolerance metadata for a plate drawing.

    Args:
        plate_id: Plate variant code (e.g. "CG", "BG-AC").
        params: Per-deployment build inputs.
        spec: Loaded plate spec.

    Returns:
        Dict consumed by downstream PDF composition.
    """
    ctx = spec.deployment_contexts[params.deployment_context]
    part_number = f"ARC-PLT-{plate_id}-{params.revision}"
    if params.deployment_context != "commercial":
        part_number += "-D"

    return {
        "part_number": part_number,
        "description": spec.description,
        "revision": params.revision,
        "deployment_context": params.deployment_context,
        "material": ctx.material,
        "finish": ctx.finish,
        "thickness_mm": ctx.thickness_mm,
        "ip_rating": ctx.ip_rating,
        "fasteners": ctx.fasteners,
        "ground_stud": ctx.ground_stud,
        "outer_dims_mm": {
            "L": spec.outer_dims_mm.L,
            "W": spec.outer_dims_mm.W,
        },
        "general_tolerance": GENERAL_TOLERANCE,
        "build_params": {
            "power_conduit_od_mm": params.power_conduit_od_mm,
            "data_conduit_od_mm": params.data_conduit_od_mm,
            "data_conduit_count": params.data_conduit_count,
        },
        "drawing_pipeline_status": "v1_minimal",
        "deferred": DEFERRED_DRAWING_FEATURES,
    }


def export_metadata(metadata: dict, out_path: Path) -> Path:
    """Write drawing metadata JSON sidecar."""
    out_path.write_text(json.dumps(metadata, indent=2))
    return out_path
