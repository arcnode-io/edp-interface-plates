"""Generic parametric plate model — shared across all plate variants.

Each plate variant has its own `cad/specs/{plate_id}/spec.yaml` (same schema)
including a `default_params:` block. The single dispatcher in
`cad/model/build.py` loads the spec, resolves params, and builds the plate.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import cadquery as cq
import yaml
from pydantic import BaseModel

DeploymentContext = Literal["commercial", "defense_forward", "sovereign_government"]

# Reason: M-thread tap drill diameters per ISO 965; minor Ø for tapping.
GROUND_STUD_TAP_DRILL_MM: Final[dict[str, float]] = {
    "M8": 6.8,
    "M10": 8.5,
    "M12": 10.2,
}


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
    # Reason: Option 1 thermal mitigation. Slot length applies to bolts whose
    # radial distance from pattern center exceeds the round-hole margin
    # threshold — for the 8-bolt corners-and-edge-midpoints pattern on a
    # rectangular plate, that's 4 corners + 2 long-axis midpoints (6 of 8).
    # Short-axis midpoints stay round (smaller radial offset, ample clearance).
    # None means all 8 holes round (legacy). 13mm = 11mm hole + 2mm radial
    # extra per side, covering 0.449mm thermal + 0.1mm fab tol + 0.2mm safety.
    slot_length_mm: float | None = None


class DefaultParams(BaseModel):
    """v1 build params — pinned in spec.yaml as design contract."""

    power_conduit_od_mm: float
    data_conduit_od_mm: float
    data_conduit_count: int
    deployment_context: str
    revision: str


class PlateSpec(BaseModel):
    """Top-level plate spec — drives model + drawing + BOM generators."""

    plate_id: str
    description: str
    outer_dims_mm: OuterDims
    deployment_contexts: dict[str, DeploymentContextSpec]
    penetration_schedule: list[Penetration]
    mounting_bolts: MountingBolts
    default_params: DefaultParams

    model_config = {"extra": "ignore"}


@dataclass(frozen=True)
class PlateBuildParams:
    """Per-deployment build params. Conduit ODs come from sizing engine Module F."""

    power_conduit_od_mm: float
    data_conduit_od_mm: float
    data_conduit_count: int
    deployment_context: DeploymentContext
    revision: str


def load_spec(spec_path: Path) -> PlateSpec:
    """Load + validate a plate spec.yaml at the given path."""
    return PlateSpec.model_validate(yaml.safe_load(spec_path.read_text()))


def default_params_for(spec: PlateSpec) -> PlateBuildParams:
    """Build PlateBuildParams from spec's default_params block."""
    dp = spec.default_params
    return PlateBuildParams(
        power_conduit_od_mm=dp.power_conduit_od_mm,
        data_conduit_od_mm=dp.data_conduit_od_mm,
        data_conduit_count=dp.data_conduit_count,
        deployment_context=dp.deployment_context,  # type: ignore[arg-type]
        revision=dp.revision,
    )


def build_plate(params: PlateBuildParams, spec: PlateSpec) -> cq.Workplane:
    """Build a plate solid: outer box + penetrations + mounting bolt holes.

    Args:
        params: Per-deployment build inputs.
        spec: Loaded plate spec.

    Returns:
        CadQuery Workplane with plate solid.

    Raises:
        NotImplementedError: For data_conduit_count != 1 (v1 limitation).
    """
    if params.data_conduit_count != 1:
        raise NotImplementedError(
            f"data_conduit_count={params.data_conduit_count} not yet supported"
        )

    ctx = spec.deployment_contexts[params.deployment_context]
    long_dim = spec.outer_dims_mm.L
    wide_dim = spec.outer_dims_mm.W
    plate = cq.Workplane("XY").box(wide_dim, long_dim, ctx.thickness_mm)

    # Reason: cadquery's .center(x, y) is RELATIVE and accumulates across calls
    # in a chain. Use pushPoints() for absolute positioning on the workplane.
    for pen in spec.penetration_schedule:
        diameter = _resolve_penetration_diameter(pen, params, ctx)
        plate = (
            plate.faces(">Z")
            .workplane()
            .pushPoints([(pen.x_mm, pen.y_mm)])
            .hole(diameter)
        )

    return _cut_mounting_bolts(plate, spec.mounting_bolts, long_dim, wide_dim)


def _resolve_penetration_diameter(
    pen: Penetration, params: PlateBuildParams, ctx: DeploymentContextSpec
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
    """Cut bolt holes per mounting_bolts.pattern.

    For an 8-bolt corners-and-edge-midpoints pattern on a rectangular plate
    where the long side > short side (840 vs 640 mm here), thermal expansion
    pushes radial offset highest at the 4 corners (full half-diagonal) AND
    the 2 long-axis midpoints (long-side half). Short-axis midpoints sit on
    the short half, with the smallest offset and plenty of clearance.

    When slot_length_mm is set, slot the 4 corners + 2 long-axis midpoints
    (6 of 8 bolts). Slot orientation: long axis points radially toward
    pattern center, accommodating differential thermal expansion. Short-axis
    midpoints stay round.
    """
    import math

    if bolts.pattern != "corners_and_edge_midpoints":
        raise ValueError(f"Unsupported mounting pattern: {bolts.pattern}")

    x_outer = wide_dim / 2 - bolts.inset_mm
    y_outer = long_dim / 2 - bolts.inset_mm
    corners = [
        (-x_outer, -y_outer),
        (x_outer, -y_outer),
        (-x_outer, y_outer),
        (x_outer, y_outer),
    ]
    long_axis_midpoints = [
        (0, -y_outer),
        (0, y_outer),
    ]
    short_axis_midpoints = [
        (-x_outer, 0),
        (x_outer, 0),
    ]

    # Reason: cadquery .center() is RELATIVE; use pushPoints for absolute coords.
    # Short-axis midpoints always round — small radial offset, ample clearance.
    if short_axis_midpoints:
        plate = (
            plate.faces(">Z")
            .workplane()
            .pushPoints(short_axis_midpoints)
            .hole(bolts.diameter_mm)
        )

    slotted_positions = corners + long_axis_midpoints
    if bolts.slot_length_mm is None:
        # Legacy round-hole geometry; preserved for backward compat.
        plate = (
            plate.faces(">Z")
            .workplane()
            .pushPoints(slotted_positions)
            .hole(bolts.diameter_mm)
        )
        return plate

    for x, y in slotted_positions:
        # Slot's long axis points toward (0,0). atan2 gives angle of the radial
        # vector from center to bolt; slot2D's `angle` rotates the slot's long
        # axis from default +X by that amount, which lands it along the radial.
        # For long-axis midpoints at (0, ±y), atan2 returns ±90° → slot oriented
        # along Y. For corners, slot points along the diagonal.
        # Reason: slot2D needs to be at workplane origin, so reset workplane
        # via fresh .faces(">Z").workplane().moveTo(x, y) per slot.
        angle_deg = math.degrees(math.atan2(y, x))
        plate = (
            plate.faces(">Z")
            .workplane()
            .moveTo(x, y)
            .slot2D(bolts.slot_length_mm, bolts.diameter_mm, angle=angle_deg)
            .cutThruAll()
        )
    return plate
