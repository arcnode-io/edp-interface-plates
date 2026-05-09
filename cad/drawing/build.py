"""Single drawing dispatcher — emits DXF + JSON metadata sidecar per plate.

Replaces per-plate wrapper modules (cg.py, bg_ac.py, ex_g.py, ex_c.py).
Reads default_params from cad/specs/{plate_id}/spec.yaml.

Usage:
    python cad/drawing/build.py --plate-id CG
    python cad/drawing/build.py --all
"""

import argparse
import logging
from dataclasses import replace
from pathlib import Path
from typing import Final

from cad.drawing._drawing import (
    build_drawing_metadata,
    export_dxf,
    export_metadata,
)
from cad.model.build import (
    PLATE_IDS,
    build_for,
    load_plate_spec,
)
from cad.model._plate import default_params_for

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPECS_DIR: Final[Path] = REPO_ROOT / "cad" / "specs"


def _artifact_paths(plate_id: str, deployment_context: str) -> tuple[Path, Path]:
    """Resolve (dxf, meta_json) paths keyed by deployment context."""
    suffix = "" if deployment_context == "commercial" else "-defense"
    plate_dir = SPECS_DIR / plate_id
    return plate_dir / f"plate{suffix}.dxf", plate_dir / f"drawing_meta{suffix}.json"


def emit_plate_drawing(
    plate_id: str, deployment_context: str = "commercial"
) -> tuple[Path, Path]:
    """Build plate, export DXF + JSON metadata sidecar.

    Returns:
        (dxf_path, metadata_json_path).
    """
    spec = load_plate_spec(plate_id)
    params = default_params_for(spec)
    if deployment_context != params.deployment_context:
        params = replace(params, deployment_context=deployment_context)  # type: ignore[arg-type]
    plate = build_for(plate_id, params=params, spec=spec)

    dxf_target, meta_target = _artifact_paths(plate_id, deployment_context)
    dxf_path = export_dxf(plate, dxf_target)
    meta_path = export_metadata(
        build_drawing_metadata(plate_id, params, spec), meta_target
    )
    return dxf_path, meta_path


def main() -> None:
    """CLI entry: emit DXF + metadata for one or all plates."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plate-id", choices=PLATE_IDS, help="One plate")
    group.add_argument("--all", action="store_true", help="All plates")
    parser.add_argument(
        "--deployment-context",
        choices=("commercial", "defense_forward", "sovereign_government"),
        default="commercial",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    targets = PLATE_IDS if args.all else (args.plate_id,)
    for pid in targets:
        dxf, meta = emit_plate_drawing(pid, deployment_context=args.deployment_context)
        logger.info(
            f"  → {pid} ({args.deployment_context}): {dxf.relative_to(REPO_ROOT)}"
        )
        logger.info(
            f"  → {pid} ({args.deployment_context}): {meta.relative_to(REPO_ROOT)}"
        )


if __name__ == "__main__":
    main()
