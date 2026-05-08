"""Single drawing dispatcher — emits DXF + JSON metadata sidecar per plate.

Replaces per-plate wrapper modules (cg.py, bg_ac.py, ex_g.py, ex_c.py).
Reads default_params from cad/specs/{plate_id}/spec.yaml.

Usage:
    python cad/drawing/build.py --plate-id CG
    python cad/drawing/build.py --all
"""

import argparse
import logging
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


def emit_plate_drawing(plate_id: str) -> tuple[Path, Path]:
    """Build plate, export DXF + JSON metadata sidecar.

    Returns:
        (dxf_path, metadata_json_path).
    """
    spec = load_plate_spec(plate_id)
    params = default_params_for(spec)
    plate = build_for(plate_id, params=params, spec=spec)

    plate_dir = SPECS_DIR / plate_id
    dxf_path = export_dxf(plate, plate_dir / "plate.dxf")
    meta_path = export_metadata(
        build_drawing_metadata(plate_id, params, spec), plate_dir / "drawing_meta.json"
    )
    return dxf_path, meta_path


def main() -> None:
    """CLI entry: emit DXF + metadata for one or all plates."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plate-id", choices=PLATE_IDS, help="One plate")
    group.add_argument("--all", action="store_true", help="All plates")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    targets = PLATE_IDS if args.all else (args.plate_id,)
    for pid in targets:
        dxf, meta = emit_plate_drawing(pid)
        logger.info(f"  → {pid}: {dxf.relative_to(REPO_ROOT)}")
        logger.info(f"  → {pid}: {meta.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
