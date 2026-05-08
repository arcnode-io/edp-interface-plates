"""EX-C plate structural model — analytical (closed-form, no FEM needed).

Both load cases are linear-elastic with homogeneous materials, where the
analytical formulas are exact under the lumped-thermal + free-expansion
assumptions. FEM would just confirm what the math already gives.
"""

import math
from dataclasses import dataclass

import pint

from sim.ex_c.constants import (
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
    """Two analytical results for a plate's design verification."""

    joint_temp_rise: pint.Quantity  # K above ambient during fault
    thermal_offset: pint.Quantity  # mm corner-bolt radial offset at full deltaT


def solve() -> StructuralResult:
    """Compute joint temp rise + thermal offset (worst-case envelope).

    Returns:
        StructuralResult with both load case outputs in pint units.
    """
    # --- Fault current heating (adiabatic, 5-cycle) ---
    # Conservative: half the bolts (4 closest to ground stud) carry the fault.
    n_eff = BOLT_COUNT / 2

    # Worst-case current: nominal + 1sigma
    i_worst = (
        FAULT_CURRENT.magnitude.nominal_value + FAULT_CURRENT.magnitude.std_dev
    ) * ureg.kA
    # Worst-case joint resistance: nominal + 2sigma
    r_worst = (
        R_JOINT_PER_BOLT.magnitude.nominal_value
        + 2 * R_JOINT_PER_BOLT.magnitude.std_dev
    ) * ureg.microohm
    r_total = r_worst / n_eff
    energy = (i_worst**2 * r_total * FAULT_DURATION).to(ureg.J)

    # Heat capacity of bolted-joint zone (bolt + plate volume around it).
    bolt_volume = (math.pi * (BOLT_DIAMETER / 2) ** 2 * BOLT_LENGTH).to(ureg.cm**3)
    bolt_mass = (bolt_volume * STEEL_DENSITY).to(ureg.g)

    heated_radius = 2 * BOLT_DIAMETER
    plate_zone_volume = (math.pi * heated_radius**2 * PLATE_THICKNESS).to(ureg.cm**3)
    plate_zone_mass = (plate_zone_volume * PLATE_DENSITY).to(ureg.g)

    cap_per_joint = bolt_mass * STEEL_CP + plate_zone_mass * PLATE_CP
    total_capacity = n_eff * cap_per_joint

    temp_rise = (energy / total_capacity).to(ureg.kelvin)

    # --- Thermal expansion differential ---
    delta_alpha = PLATE_ALPHA - FRAME_ALPHA
    pattern_w = PLATE_WIDTH - 2 * BOLT_INSET
    pattern_l = PLATE_LENGTH - 2 * BOLT_INSET
    diagonal = (pattern_w**2 + pattern_l**2) ** 0.5

    delta_diagonal = (delta_alpha * diagonal * DELTA_T_OPERATING).to(ureg.mm)
    offset = delta_diagonal / 2

    return StructuralResult(joint_temp_rise=temp_rise, thermal_offset=offset)
