"""Parametric CG (Compute-to-Grid) interface plate.

Reads `cad/specs/CG/spec.yaml` for design constants (penetration positions,
deployment_context-keyed material/thickness, mounting bolt pattern).
Build params (conduit OD, deployment_context, revision) come from CLI
or from edp-api sizing engine Module F (per ADR-011).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import cadquery as cq
import yaml
from pydantic import BaseModel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEC_PATH: Final[Path] = REPO_ROOT / "cad" / "specs" / "CG" / "spec.yaml"
DEFAULT_OUTPUT: Final[Path] = REPO_ROOT / "cad" / "CG.step"

DeploymentContext = Literal["commercial", "defense_forward", "sovereign_government"]


class OuterDims(BaseModel):
    """Plate outer dimensions in millimeters (long axis L, wide axis W)."""

    L: float
    W: float


class DeploymentContextSpec(BaseModel):
    """Material/finish/IP/fastener set for one deployment_context."""

    material: str
    finish: str
    thickness_mm: float
    ip_rating: str
    fasteners: str
    secondary_seal: str | None
    ground_stud: str


class Penetration(BaseModel):
    """One cutout in the plate — position + size driver + fitting spec."""

    id: str
    x_mm: float
    y_mm: float
    size_driver: str
    fitting_spec: str

    model_config = {"extra": "ignore"}


class MountingBolts(BaseModel):
    """Mounting bolt pattern on the plate perimeter."""

    count: int
    inset_mm: float
    diameter_mm: float
    pattern: str


class CGSpec(BaseModel):
    """Top-level CG plate spec — drives model + drawing + BOM generators."""

    plate_id: str
    description: str
    outer_dims_mm: OuterDims
    deployment_contexts: dict[str, DeploymentContextSpec]
    penetration_schedule: list[Penetration]
    mounting_bolts: MountingBolts

    model_config = {"extra": "ignore"}


@dataclass(frozen=True)
class CGBuildParams:
    """Per-deployment build params for a CG plate.

    Sizing values come from edp-api sizing engine Module F (per ADR-011);
    v1 uses hand-computed values for commercial AC compute container.
    """

    power_conduit_od_mm: float
    data_conduit_od_mm: float
    data_conduit_count: int
    deployment_context: DeploymentContext
    revision: str


# Reason: v1 commercial — 7x HGX nodes @ 10.5 kW + ~7 kW overhead = ~80 kW
# at 415Y/240V 3ph → ~111A → 2.5" rigid conduit hub OD ≈ 73mm.
# Data: single fiber+copper bundle in 1¼" EMT → ~35mm OD.
V1_COMMERCIAL_PARAMS: Final[CGBuildParams] = CGBuildParams(
    power_conduit_od_mm=73.0,
    data_conduit_od_mm=35.0,
    data_conduit_count=1,
    deployment_context="commercial",
    revision="001",
)


# Reason: M-thread tap drill diameters per ISO 965; minor Ø for tapping.
GROUND_STUD_TAP_DRILL_MM: Final[dict[str, float]] = {
    "M8": 6.8,
    "M10": 8.5,
    "M12": 10.2,
}


def load_spec() -> CGSpec:
    """Load and validate cad/specs/CG/spec.yaml."""
    return CGSpec.model_validate(yaml.safe_load(SPEC_PATH.read_text()))


def build_cg_plate(params: CGBuildParams, spec: CGSpec | None = None) -> cq.Workplane:
    """Build the CG plate as a parametric CadQuery solid.

    Args:
        params: Per-deployment build inputs.
        spec: Loaded CG spec; loaded from disk if None.

    Returns:
        CadQuery Workplane with plate solid + penetrations + bolt holes.

    Raises:
        NotImplementedError: For data_conduit_count != 1 (v1 limitation).
    """
    if spec is None:
        spec = load_spec()

    if params.data_conduit_count != 1:
        raise NotImplementedError(
            f"data_conduit_count={params.data_conduit_count} not yet supported; "
            "v1 commercial uses count=1. Multi-conduit derivation lands "
            "when defense variants need it."
        )

    ctx = spec.deployment_contexts[params.deployment_context]
    long_dim = spec.outer_dims_mm.L
    wide_dim = spec.outer_dims_mm.W
    thickness = ctx.thickness_mm

    # Plate body — origin at face center, thickness extruded in +Z
    plate = cq.Workplane("XY").box(wide_dim, long_dim, thickness)

    # Penetrations — through-holes from spec.yaml positions
    for pen in spec.penetration_schedule:
        diameter = _resolve_penetration_diameter(pen, params, ctx)
        plate = plate.faces(">Z").workplane().center(pen.x_mm, pen.y_mm).hole(diameter)

    # Mounting bolt holes
    plate = _cut_mounting_bolts(plate, spec.mounting_bolts, long_dim, wide_dim)

    return plate


def _resolve_penetration_diameter(
    pen: Penetration, params: CGBuildParams, ctx: DeploymentContextSpec
) -> float:
    """Resolve size_driver to actual diameter in mm."""
    match pen.size_driver:
        case "param.power_conduit_od_mm":
            return params.power_conduit_od_mm
        case "param.data_conduit_od_mm":
            return params.data_conduit_od_mm
        case "context.ground_stud":
            return GROUND_STUD_TAP_DRILL_MM[ctx.ground_stud]
        case _:
            raise ValueError(f"Unknown size_driver: {pen.size_driver}")


def _cut_mounting_bolts(
    plate: cq.Workplane, bolts: MountingBolts, long_dim: float, wide_dim: float
) -> cq.Workplane:
    """Cut bolt holes per mounting_bolts.pattern."""
    if bolts.pattern != "corners_and_edge_midpoints":
        raise ValueError(f"Unsupported mounting pattern: {bolts.pattern}")

    x_outer = wide_dim / 2 - bolts.inset_mm
    y_outer = long_dim / 2 - bolts.inset_mm

    positions = [
        (-x_outer, -y_outer),
        (x_outer, -y_outer),
        (-x_outer, y_outer),
        (x_outer, y_outer),
        (0, -y_outer),
        (0, y_outer),
        (-x_outer, 0),
        (x_outer, 0),
    ]

    for x, y in positions:
        plate = plate.faces(">Z").workplane().center(x, y).hole(bolts.diameter_mm)

    return plate


def main() -> None:
    """CLI entry: build v1 commercial CG plate, export to cad/CG.step."""
    plate = build_cg_plate(V1_COMMERCIAL_PARAMS)
    cq.exporters.export(plate, str(DEFAULT_OUTPUT))
    print(f"Exported CG plate to {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
