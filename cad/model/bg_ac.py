"""BG-AC (BESS-to-Grid AC) parametric plate — wraps generic _plate module."""

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
SPEC_PATH: Final[Path] = REPO_ROOT / "cad" / "specs" / "BG-AC" / "spec.yaml"
DEFAULT_OUTPUT: Final[Path] = REPO_ROOT / "cad" / "BG-AC.step"

# Reason: v1 commercial — Tesla Megapack 2 XL, 1 MW @ 480V = 1200A peak,
# split across 2 parallel feeders @ 600A each. 600A AC -> ~3.5" rigid
# conduit hub OD ~100mm. Data conduit same as CG (35mm).
V1_COMMERCIAL_PARAMS: Final[PlateBuildParams] = PlateBuildParams(
    power_conduit_od_mm=100.0,
    data_conduit_od_mm=35.0,
    data_conduit_count=1,
    deployment_context="commercial",
    revision="001",
)


def load_bg_ac_spec() -> PlateSpec:
    """Load BG-AC spec.yaml."""
    return load_spec(SPEC_PATH)


def build_bg_ac_plate(
    params: PlateBuildParams, spec: PlateSpec | None = None
) -> cq.Workplane:
    """Build the BG-AC plate."""
    if spec is None:
        spec = load_bg_ac_spec()
    return build_plate(params, spec)


def main() -> None:
    """CLI entry: build v1 commercial BG-AC plate, export to cad/BG-AC.step."""
    plate = build_bg_ac_plate(V1_COMMERCIAL_PARAMS)
    cq.exporters.export(plate, str(DEFAULT_OUTPUT))
    print(f"Exported BG-AC plate to {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
