"""CG plate drawing pipeline — minimal cadquery-native DXF + title block sidecar.

V1 scope: emits a face-view DXF + a `cg_drawing_meta.json` sidecar holding
title-block fields (part_number, material, finish, revision, tolerances).
Full GD&T tolerance callouts + integrated PDF deferred — those need
explicit GD&T scheme decisions (datum refs, surface finish symbols,
tolerance bands) which an autonomous run shouldn't make.

Downstream consumer (drawing-generator service or fab vendor):
  - Reads `cg.dxf` for geometry
  - Reads `cg_drawing_meta.json` for title block + general tolerance
  - Composes into A3/A1 sheet with title block template
"""

import json
import logging
from pathlib import Path
from typing import Final

import cadquery as cq

from cad.model.cg import (
    V1_COMMERCIAL_PARAMS,
    CGBuildParams,
    CGSpec,
    build_cg_plate,
    load_spec,
)

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_DXF: Final[Path] = REPO_ROOT / "cad" / "CG.dxf"
DEFAULT_META: Final[Path] = REPO_ROOT / "cad" / "CG_drawing_meta.json"

# Reason: ISO 2768-m general tolerance is the cad/layout_spec.yaml default
# (carried over from L-bracket template). Tighter callouts on penetration
# positions land when GD&T scheme is explicitly specified by user.
GENERAL_TOLERANCE: Final[str] = "ISO 2768-m"


def _project_face_view(plate: cq.Workplane) -> cq.Workplane:
    """Extract the >Z face for DXF export (face-view fab drawing)."""
    # Reason: section the plate at mid-thickness so penetrations show through;
    # cadquery DXF export needs a 2D wire profile, not a 3D solid.
    return plate.faces(">Z").workplane().section()


def export_dxf(plate: cq.Workplane, out_path: Path = DEFAULT_DXF) -> Path:
    """Export plate face view to DXF.

    Args:
        plate: Built CG plate solid.
        out_path: DXF output path.

    Returns:
        Absolute path to the emitted DXF.
    """
    face_view = _project_face_view(plate)
    cq.exporters.export(face_view, str(out_path))
    return out_path


def build_drawing_metadata(params: CGBuildParams, spec: CGSpec) -> dict:
    """Assemble title-block + tolerance metadata for the CG plate drawing.

    Schema is consumed by downstream PDF composition (drawing-generator
    service or fab vendor) — fields chosen to populate ARCNODE title block.
    """
    ctx = spec.deployment_contexts[params.deployment_context]
    part_number = f"ARC-PLT-CG-{params.revision}"
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
        "deferred": [
            "GD&T tolerance callouts on penetration positions",
            "Datum reference frame + ASME Y14.5 symbols",
            "Surface finish callouts",
            "Integrated PDF composition with title block template",
        ],
    }


def export_metadata(metadata: dict, out_path: Path = DEFAULT_META) -> Path:
    """Write drawing metadata JSON sidecar."""
    out_path.write_text(json.dumps(metadata, indent=2))
    return out_path


def main() -> None:
    """CLI entry: build v1 commercial CG plate, emit DXF + metadata sidecar."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    spec = load_spec()
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS, spec)

    dxf_path = export_dxf(plate)
    meta_path = export_metadata(build_drawing_metadata(V1_COMMERCIAL_PARAMS, spec))

    logger.info(f"  → {dxf_path.relative_to(REPO_ROOT)}")
    logger.info(f"  → {meta_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
