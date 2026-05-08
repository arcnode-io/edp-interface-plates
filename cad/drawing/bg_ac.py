"""BG-AC plate drawing pipeline — wraps generic _drawing module."""

import logging
from pathlib import Path
from typing import Final

from cad.drawing._drawing import (
    build_drawing_metadata,
    export_dxf,
    export_metadata,
)
from cad.model.bg_ac import V1_COMMERCIAL_PARAMS, build_bg_ac_plate, load_bg_ac_spec

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_DXF: Final[Path] = REPO_ROOT / "cad" / "specs" / "BG-AC" / "plate.dxf"
DEFAULT_META: Final[Path] = REPO_ROOT / "cad" / "specs" / "BG-AC" / "drawing_meta.json"


def main() -> None:
    """CLI entry: build v1 commercial BG-AC plate, emit DXF + metadata sidecar."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    spec = load_bg_ac_spec()
    plate = build_bg_ac_plate(V1_COMMERCIAL_PARAMS, spec)

    dxf_path = export_dxf(plate, DEFAULT_DXF)
    meta_path = export_metadata(
        build_drawing_metadata("BG-AC", V1_COMMERCIAL_PARAMS, spec), DEFAULT_META
    )

    logger.info(f"  → {dxf_path.relative_to(REPO_ROOT)}")
    logger.info(f"  → {meta_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
