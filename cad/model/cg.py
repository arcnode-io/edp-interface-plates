"""CG (Compute-to-Grid) parametric plate — wraps generic _plate module."""

from pathlib import Path
from typing import Final

import cadquery as cq

from cad.model._plate import (
    PlateBuildParams,
    PlateSpec,
    build_plate,
    load_spec,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEC_PATH: Final[Path] = REPO_ROOT / "cad" / "specs" / "CG" / "spec.yaml"
DEFAULT_OUTPUT: Final[Path] = REPO_ROOT / "cad" / "CG.step"

# Reason: v1 commercial — 7x HGX nodes @ 10.5 kW + ~7 kW overhead = ~80 kW
# at 415Y/240V 3ph → ~111A → 2.5" rigid conduit hub OD ≈ 73mm.
# Data: single fiber+copper bundle in 1¼" EMT → ~35mm OD.
V1_COMMERCIAL_PARAMS: Final[PlateBuildParams] = PlateBuildParams(
    power_conduit_od_mm=73.0,
    data_conduit_od_mm=35.0,
    data_conduit_count=1,
    deployment_context="commercial",
    revision="001",
)


def load_cg_spec() -> PlateSpec:
    """Load CG spec.yaml."""
    return load_spec(SPEC_PATH)


def build_cg_plate(
    params: PlateBuildParams, spec: PlateSpec | None = None
) -> cq.Workplane:
    """Build the CG plate."""
    if spec is None:
        spec = load_cg_spec()
    return build_plate(params, spec)


def main() -> None:
    """CLI entry: build v1 commercial CG plate, export to cad/CG.step."""
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS)
    cq.exporters.export(plate, str(DEFAULT_OUTPUT))
    print(f"Exported CG plate to {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
