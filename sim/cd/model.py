"""CD plate model — structural mirror of CG + coolant flow derivation.

Coolant flow is the CD-specific load case: derives volumetric flow rate
(and the QD body OD that follows) from heat load and secondary-loop ΔT.
Same closed-form analytical approach as the structural cases — no FEM.
"""

import math
from dataclasses import dataclass

import pint

from sim.cd.constants import (
    BOLT_COUNT,
    BOLT_DIAMETER,
    BOLT_INSET,
    BOLT_LENGTH,
    DELTA_T_OPERATING,
    DELTA_T_SECONDARY,
    FAULT_CURRENT,
    FAULT_DURATION,
    FRAME_ALPHA,
    HEAT_LOAD,
    PLATE_ALPHA,
    PLATE_CP,
    PLATE_DENSITY,
    PLATE_LENGTH,
    PLATE_THICKNESS,
    PLATE_WIDTH,
    R_JOINT_PER_BOLT,
    STEEL_CP,
    STEEL_DENSITY,
    WATER_CP,
    WATER_DENSITY,
    ureg,
)


@dataclass(frozen=True)
class StructuralResult:
    """Joint temp rise + thermal offset (mirror of every other plate)."""

    joint_temp_rise: pint.Quantity
    thermal_offset: pint.Quantity


@dataclass(frozen=True)
class CoolantResult:
    """Volumetric flow rate for sizing the QD body OD."""

    flow_per_line: pint.Quantity
    line_velocity_at_50mm_bore: pint.Quantity


def solve(delta_t: pint.Quantity | None = None) -> StructuralResult:
    """Compute joint temp rise + thermal offset for CD plate."""
    if delta_t is None:
        delta_t = DELTA_T_OPERATING
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
    delta_diagonal = (delta_alpha * diagonal * delta_t).to(ureg.mm)
    offset = delta_diagonal / 2

    return StructuralResult(joint_temp_rise=temp_rise, thermal_offset=offset)


def solve_coolant() -> CoolantResult:
    """Compute volumetric flow per line + line velocity at 2" bore.

    Returns:
        CoolantResult with nominal flow rate and 2"-bore line velocity.
    """
    # Reason: each line carries full mass flow (loop in series, not parallel).
    q_nom = HEAT_LOAD.magnitude.nominal_value * ureg.kW
    dt_nom = DELTA_T_SECONDARY.magnitude.nominal_value * ureg.kelvin

    m_dot = (q_nom / (WATER_CP * dt_nom)).to(ureg.kg / ureg.s)
    v_dot = (m_dot / WATER_DENSITY).to(ureg.liter / ureg.minute)

    qd_inner_dia = 50.0 * ureg.mm  # 2" nominal bore
    qd_area = (math.pi * (qd_inner_dia / 2) ** 2).to(ureg.m**2)
    line_velocity = (m_dot / WATER_DENSITY / qd_area).to(ureg.m / ureg.s)

    return CoolantResult(flow_per_line=v_dot, line_velocity_at_50mm_bore=line_velocity)
