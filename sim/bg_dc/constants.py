"""Physical parameters for BG-DC interface plate structural analysis.

BG-DC plate: same 6mm 6061-T6 / 640x840 / 8x M10 geometry as BG-AC. Different
fault current scenario — DC has no zero crossing, so fault is sustained until
the DC contactor opens (~50ms typical for fast DC contactors per IEC 60947-2).

Same two load cases as every other plate. Expected values derived in
theory.ipynb.
"""

from typing import Final

import pint
from uncertainties import ufloat

ureg = pint.UnitRegistry()

# --- Plate geometry (same as BG-AC, commercial deployment_context) ---
PLATE_THICKNESS: Final = 6.0 * ureg.mm
PLATE_WIDTH: Final = 640.0 * ureg.mm
PLATE_LENGTH: Final = 840.0 * ureg.mm

# --- Material: 6061-T6 aluminum ---
PLATE_DENSITY: Final = 2.70 * ureg.g / ureg.cm**3
PLATE_CP: Final = 896 * ureg.J / (ureg.kg * ureg.kelvin)
PLATE_ALPHA: Final = 23.6e-6 / ureg.kelvin

# --- Receiver frame: A36 mild steel ---
FRAME_ALPHA: Final = 11.7e-6 / ureg.kelvin

# --- Fasteners: same 8x M10 mounting bolts; M12 ground stud per spec ---
BOLT_COUNT: Final = 8
BOLT_DIAMETER: Final = 10.0 * ureg.mm
BOLT_CLEARANCE_HOLE: Final = 11.0 * ureg.mm
BOLT_INSET: Final = 60.0 * ureg.mm
BOLT_LENGTH: Final = 30.0 * ureg.mm
STEEL_DENSITY: Final = 7.85 * ureg.g / ureg.cm**3
STEEL_CP: Final = 460 * ureg.J / (ureg.kg * ureg.kelvin)

# --- Bolt pattern derived ---
PATTERN_WIDTH: Final = PLATE_WIDTH - 2 * BOLT_INSET
PATTERN_LENGTH: Final = PLATE_LENGTH - 2 * BOLT_INSET
PATTERN_DIAGONAL: Final = (PATTERN_WIDTH**2 + PATTERN_LENGTH**2) ** 0.5
BOLT_CLEARANCE_RADIAL: Final = (BOLT_CLEARANCE_HOLE - BOLT_DIAMETER) / 2

# --- Fault current scenario for BG-DC ---
# 4-string BESS aggregate fault: each string contributes ~2 kA via internal
# string fuse before DC contactor opens. 4 strings = ~8 kA worst-case sustained.
# ±25% uncertainty (string SOC + temp variation).
# Fast DC contactor clear time per IEC 60947-2: 50 ms (3-cycle equivalent at
# 60 Hz, faster than AC's 5-cycle clear because no zero-crossing wait).
FAULT_CURRENT: Final = ufloat(8.0, 2.0) * ureg.kA
FAULT_DURATION: Final = 50.0 * ureg.ms
R_JOINT_PER_BOLT: Final = ufloat(125, 75) * ureg.microohm

# --- Operating temperature range ---
T_AMBIENT_FAULT_C: Final = 25.0
DELTA_T_OPERATING: Final = 85.0 * ureg.kelvin

# --- Verdict thresholds (same as every plate) ---
JOINT_TEMP_THRESHOLD_C: Final = 150.0

# --- Expected values from theory.ipynb ---
# Worst-case current 10 kA (+1sigma) through 275 µΩ / 4 effective parallel
# = 68.75 µΩ effective. Energy = I² · R · t = 1e8 · 68.75e-6 · 0.05 = 344 J.
# System heat capacity (calibrated against CG: 5435 J → 50.8 K) ~107 J/K.
# Expected rise = 344 / 107 ~ 3.21 K. Comfortable headroom vs 125 K limit.
EXPECTED_JOINT_TEMP_RISE: Final = 3.21 * ureg.kelvin
EXPECTED_JOINT_TEMP_RISE_REL_TOL: Final = 0.50

# Thermal expansion identical to every plate (same materials, same geometry).
EXPECTED_THERMAL_OFFSET: Final = 0.449 * ureg.mm
EXPECTED_THERMAL_OFFSET_REL_TOL: Final = 0.05
