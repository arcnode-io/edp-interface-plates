"""Physical parameters for BG-AC interface plate structural analysis.

BG-AC plate: same 6mm 6061-T6 / 640x840 / 8x M10 geometry as CG. Different
fault current scenario (BESS-side fault contribution, lower than compute LV
bus) and M12 ground stud (vs CG's M10) per spec.yaml deployment_contexts.

Same two load cases as CG. Expected values derived in theory.ipynb.
"""

from typing import Final

import pint
from uncertainties import ufloat

ureg = pint.UnitRegistry()

# --- Plate geometry (same as CG, commercial deployment_context) ---
PLATE_THICKNESS: Final = 6.0 * ureg.mm
PLATE_WIDTH: Final = 640.0 * ureg.mm
PLATE_LENGTH: Final = 840.0 * ureg.mm

# --- Material: 6061-T6 aluminum ---
PLATE_DENSITY: Final = 2.70 * ureg.g / ureg.cm**3
PLATE_CP: Final = 896 * ureg.J / (ureg.kg * ureg.kelvin)
PLATE_ALPHA: Final = 23.6e-6 / ureg.kelvin

# --- Receiver frame: A36 mild steel ---
FRAME_ALPHA: Final = 11.7e-6 / ureg.kelvin

# --- Fasteners: same 8x M10 as CG (mounting bolts; ground stud is M12 per spec) ---
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

# --- Fault current scenario for BG-AC ---
# Tesla Megapack 2 XL inverter: ~1.5 kA per inverter under bolted fault.
# 4 inverters per Megapack contributing simultaneously into the BG-AC plate
# ground path = ~6 kA worst-case. ±20% uncertainty.
# 5-cycle clear time per Megapack internal breaker (faster than utility-side).
FAULT_CURRENT: Final = ufloat(6.0, 1.2) * ureg.kA
FAULT_DURATION: Final = (5 / 60) * ureg.s
R_JOINT_PER_BOLT: Final = ufloat(125, 75) * ureg.microohm

# --- Operating temperature range ---
T_AMBIENT_FAULT_C: Final = 25.0
DELTA_T_OPERATING: Final = 85.0 * ureg.kelvin
# Defense forward operating range per MIL-STD-810H typical: -40 to +71 °C.
DELTA_T_DEFENSE: Final = 111.0 * ureg.kelvin

# --- Verdict thresholds (same as CG) ---
JOINT_TEMP_THRESHOLD_C: Final = 150.0

# --- Expected values from theory.ipynb (BG-AC fault is much lower than CG) ---
# Fault current is ~7.2 kA (worst-case +1sigma) vs CG's 30.8 kA — temp rise
# scales as I², so expected rise = 50.8 K * (7.2/30.8)² = ~2.8 K. Comfortable.
EXPECTED_JOINT_TEMP_RISE: Final = 2.8 * ureg.kelvin
EXPECTED_JOINT_TEMP_RISE_REL_TOL: Final = 0.50

# Thermal expansion identical to CG (same materials, same geometry).
EXPECTED_THERMAL_OFFSET: Final = 0.449 * ureg.mm
EXPECTED_THERMAL_OFFSET_REL_TOL: Final = 0.05
