"""EX-G plate drawing pipeline — wraps generic _drawing module."""

import logging
from pathlib import Path
from typing import Final

from cad.drawing._drawing import (
    build_drawing_metadata,
    export_dxf,
    export_metadata,
)
from cad.model.ex_g import V1_COMMERCIAL_PARAMS, build_ex_g_plate, load_ex_g_spec

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_DXF: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-G" / "plate.dxf"
DEFAULT_META: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-G" / "drawing_meta.json"


def main() -> None:
    """CLI entry: build v1 commercial EX-G plate, emit DXF + metadata sidecar."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    spec = load_ex_g_spec()
    plate = build_ex_g_plate(V1_COMMERCIAL_PARAMS, spec)

    dxf_path = export_dxf(plate, DEFAULT_DXF)
    meta_path = export_metadata(
        build_drawing_metadata("EX-G", V1_COMMERCIAL_PARAMS, spec), DEFAULT_META
    )

    logger.info(f"  → {dxf_path.relative_to(REPO_ROOT)}")
    logger.info(f"  → {meta_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
