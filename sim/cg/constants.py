"""Physical parameters for CG interface plate structural analysis.

CG plate: 6mm 6061-T6 aluminum, 640x840mm, 8x M10 bolts, mounted on welded
A36 receiver frame. Two load cases:
1. Bolt pattern under fault current (joint heating)
2. Thermal expansion differential (plate vs frame across temp swing)

Expected values derived in theory.ipynb (see same dir).
"""

from typing import Final

import pint
from uncertainties import ufloat

ureg = pint.UnitRegistry()

# --- Plate geometry (commercial deployment_context per ADR-008) ---
PLATE_THICKNESS: Final = 6.0 * ureg.mm
PLATE_WIDTH: Final = 640.0 * ureg.mm
PLATE_LENGTH: Final = 840.0 * ureg.mm

# --- Material: 6061-T6 aluminum (ASTM B209, ASM Aluminum Handbook) ---
PLATE_DENSITY: Final = 2.70 * ureg.g / ureg.cm**3
PLATE_CP: Final = 896 * ureg.J / (ureg.kg * ureg.kelvin)
PLATE_ALPHA: Final = 23.6e-6 / ureg.kelvin
PLATE_YIELD_AT_25C: Final = 276 * ureg.MPa

# --- Receiver frame: A36 mild steel ---
FRAME_ALPHA: Final = 11.7e-6 / ureg.kelvin

# --- Fasteners: 8x M10 grade 8.8 zinc-plated steel ---
BOLT_COUNT: Final = 8
BOLT_DIAMETER: Final = 10.0 * ureg.mm
BOLT_CLEARANCE_HOLE: Final = 11.0 * ureg.mm
BOLT_INSET: Final = 60.0 * ureg.mm
BOLT_LENGTH: Final = 30.0 * ureg.mm  # nominal engagement
STEEL_DENSITY: Final = 7.85 * ureg.g / ureg.cm**3
STEEL_CP: Final = 460 * ureg.J / (ureg.kg * ureg.kelvin)

# --- Bolt pattern derived ---
PATTERN_WIDTH: Final = PLATE_WIDTH - 2 * BOLT_INSET
PATTERN_LENGTH: Final = PLATE_LENGTH - 2 * BOLT_INSET
PATTERN_DIAGONAL: Final = (PATTERN_WIDTH**2 + PATTERN_LENGTH**2) ** 0.5
BOLT_CLEARANCE_RADIAL: Final = (BOLT_CLEARANCE_HOLE - BOLT_DIAMETER) / 2

# --- Fault current scenario for CG ---
# 28 kA at 415V LV bus (ADR-005 study), ±10% uncertainty.
# 5-cycle clear time at 60Hz = 83 ms.
# Joint resistance: 125 ±75 µΩ per IEEE Std 142 grounding studies.
FAULT_CURRENT: Final = ufloat(28, 2.8) * ureg.kA
FAULT_DURATION: Final = (5 / 60) * ureg.s
R_JOINT_PER_BOLT: Final = ufloat(125, 75) * ureg.microohm

# --- Operating temperature range (commercial deployment) ---
T_AMBIENT_FAULT_C: Final = 25.0
DELTA_T_OPERATING: Final = 85.0 * ureg.kelvin  # -25 to +60 °C swing

# --- Slotted-bolt mitigation (per Option 1, theory.ipynb design-risk cell) ---
# Slot length sized for worst-case slotted bolt (corner @ 0.449mm offset):
#   D_hole + 2*(thermal_offset + fab_tol + margin) = 11 + 2*(0.449 + 0.1 + 0.2)
#   = 12.5 → 13mm (rounded up). Same slot covers long-axis midpoints
#   (0.364mm offset → 0.664mm budget < 1.0mm slot extra per side).
# Short-axis midpoints stay round (0.263mm offset, 0.137mm net margin after
# fab tol — comfortable).
FAB_TOLERANCE: Final = 0.1 * ureg.mm  # ISO 2768-m hole position
SAFETY_MARGIN: Final = 0.2 * ureg.mm  # engineering buffer
SLOT_LENGTH: Final = 13.0 * ureg.mm

# --- Verdict thresholds ---
JOINT_TEMP_THRESHOLD_C: Final = 150.0  # 6061-T6 yield derating point

# --- Expected values from theory.ipynb (closed-form analytical) ---
# Reason: at worst-case fault current (+1sigma = 30.8 kA) through worst-case
# joint resistance (+2sigma = 275 µΩ per bolt / 4 effective parallel = 68.8 µΩ),
# adiabatic temp rise = energy / heat_capacity = 50.8 K above ambient.
EXPECTED_JOINT_TEMP_RISE: Final = 50.8 * ureg.kelvin
EXPECTED_JOINT_TEMP_RISE_REL_TOL: Final = 0.50  # ±50% — joint R is dominant unknown

# Reason: 6061 vs A36 differential alpha = 11.9e-6 /K. Bolt pattern diagonal 888mm.
# At deltaT=85K: differential expansion 0.898mm. Per-corner-bolt offset = 0.449mm.
EXPECTED_THERMAL_OFFSET: Final = 0.449 * ureg.mm
EXPECTED_THERMAL_OFFSET_REL_TOL: Final = 0.05  # ±5% — material coefs well-characterized
