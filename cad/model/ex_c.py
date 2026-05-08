"""EX-C (External Services, Compute Container) parametric plate."""

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
SPEC_PATH: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-C" / "spec.yaml"
DEFAULT_OUTPUT: Final[Path] = REPO_ROOT / "cad" / "specs" / "EX-C" / "plate.step"

# Reason: v1 commercial — fiber uplink in 2" EMT ~63mm OD (data_conduit_*),
# OOB mgmt in 1¼" EMT ~35mm OD (power_conduit_* — names generic, see spec).
V1_COMMERCIAL_PARAMS: Final[PlateBuildParams] = PlateBuildParams(
    power_conduit_od_mm=35.0,  # OOB mgmt conduit (named "power_*" generically)
    data_conduit_od_mm=63.0,  # fiber uplink conduit
    data_conduit_count=1,
    deployment_context="commercial",
    revision="001",
)


def load_ex_c_spec() -> PlateSpec:
    """Load EX-C spec.yaml."""
    return load_spec(SPEC_PATH)


def build_ex_c_plate(
    params: PlateBuildParams, spec: PlateSpec | None = None
) -> cq.Workplane:
    """Build the EX-C plate."""
    if spec is None:
        spec = load_ex_c_spec()
    return build_plate(params, spec)


def main() -> None:
    """CLI entry: build v1 commercial EX-C plate, export to cad/specs/EX-C/plate.step."""
    plate = build_ex_c_plate(V1_COMMERCIAL_PARAMS)
    cq.exporters.export(plate, str(DEFAULT_OUTPUT))
    print(f"Exported EX-C plate to {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
