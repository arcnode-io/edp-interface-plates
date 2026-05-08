"""EX-G (External Services, Grid Container) parametric plate."""

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
SPEC_PATH: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-G" / "spec.yaml"
DEFAULT_OUTPUT: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-G" / "plate.step"

# Reason: v1 commercial — station-service LV (~30A 240V) -> 3/4" rigid
# conduit hub OD ~28mm; SCADA fiber/copper -> 1¼" EMT ~35mm OD.
V1_COMMERCIAL_PARAMS: Final[PlateBuildParams] = PlateBuildParams(
    power_conduit_od_mm=28.0,
    data_conduit_od_mm=35.0,
    data_conduit_count=1,
    deployment_context="commercial",
    revision="001",
)


def load_ex_g_spec() -> PlateSpec:
    """Load EX-G spec.yaml."""
    return load_spec(SPEC_PATH)


def build_ex_g_plate(
    params: PlateBuildParams, spec: PlateSpec | None = None
) -> cq.Workplane:
    """Build the EX-G plate."""
    if spec is None:
        spec = load_ex_g_spec()
    return build_plate(params, spec)


def main() -> None:
    """CLI entry: build v1 commercial EX-G plate, export to cad/specs/EX-G/plate.step."""
    plate = build_ex_g_plate(V1_COMMERCIAL_PARAMS)
    cq.exporters.export(plate, str(DEFAULT_OUTPUT))
    print(f"Exported EX-G plate to {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
