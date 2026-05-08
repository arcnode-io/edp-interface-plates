"""BG-DC plate structural model — analytical (closed-form, mirror of BG-AC)."""

import math
from dataclasses import dataclass

import pint

from sim.bg_dc.constants import (
    BOLT_COUNT,
    BOLT_DIAMETER,
    BOLT_INSET,
    BOLT_LENGTH,
    DELTA_T_OPERATING,
    FAULT_CURRENT,
    FAULT_DURATION,
    FRAME_ALPHA,
    PLATE_ALPHA,
    PLATE_CP,
    PLATE_DENSITY,
    PLATE_LENGTH,
    PLATE_THICKNESS,
    PLATE_WIDTH,
    R_JOINT_PER_BOLT,
    STEEL_CP,
    STEEL_DENSITY,
    ureg,
)


@dataclass(frozen=True)
class StructuralResult:
    """Two analytical results for BG-DC design verification."""

    joint_temp_rise: pint.Quantity
    thermal_offset: pint.Quantity


def solve() -> StructuralResult:
    """Compute joint temp rise + thermal offset for BG-DC plate."""
    n_eff = BOLT_COUNT / 2
    i_worst = (
        FAULT_CURRENT.magnitude.nominal_value + FAULT_CURRENT.magnitude.std_dev
    ) * ureg.kA
    r_worst = (
        R_JOINT_PER_BOLT.magnitude.nominal_value
        + 2 * R_JOINT_PER_BOLT.magnitude.std_dev
    ) * ureg.microohm
    r_total = r_worst / n_eff
    energy = (i_worst**2 * r_total * FAULT_DURATION).to(ureg.J)

    bolt_volume = (math.pi * (BOLT_DIAMETER / 2) ** 2 * BOLT_LENGTH).to(ureg.cm**3)
    bolt_mass = (bolt_volume * STEEL_DENSITY).to(ureg.g)
    heated_radius = 2 * BOLT_DIAMETER
    plate_zone_volume = (math.pi * heated_radius**2 * PLATE_THICKNESS).to(ureg.cm**3)
    plate_zone_mass = (plate_zone_volume * PLATE_DENSITY).to(ureg.g)
    cap_per_joint = bolt_mass * STEEL_CP + plate_zone_mass * PLATE_CP
    total_capacity = n_eff * cap_per_joint

    temp_rise = (energy / total_capacity).to(ureg.kelvin)

    delta_alpha = PLATE_ALPHA - FRAME_ALPHA
    pattern_w = PLATE_WIDTH - 2 * BOLT_INSET
    pattern_l = PLATE_LENGTH - 2 * BOLT_INSET
    diagonal = (pattern_w**2 + pattern_l**2) ** 0.5
    delta_diagonal = (delta_alpha * diagonal * DELTA_T_OPERATING).to(ureg.mm)
    offset = delta_diagonal / 2

    return StructuralResult(joint_temp_rise=temp_rise, thermal_offset=offset)
