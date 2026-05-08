"""Physical parameters for CD interface plate analysis.

CD plate: same 6mm 6061-T6 / 640x840 / 8x M10 geometry as CG. Three load cases:
1. Coolant flow & QD body OD sizing (CD-specific, derived in theory.ipynb)
2. Bolt pattern under stray-current ground fault (much lower than CG —
   cooling loop is electrically isolated; ground stud is bonding-grade)
3. Thermal expansion differential (same as every plate)

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

# --- Material: 6061-T6 aluminum ---
PLATE_DENSITY: Final = 2.70 * ureg.g / ureg.cm**3
PLATE_CP: Final = 896 * ureg.J / (ureg.kg * ureg.kelvin)
PLATE_ALPHA: Final = 23.6e-6 / ureg.kelvin

# --- Receiver frame: A36 mild steel ---
FRAME_ALPHA: Final = 11.7e-6 / ureg.kelvin

# --- Fasteners: 8x M10 mounting bolts (ground stud is M10 bonding) ---
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

# --- Fault current scenario for CD ---
# Cooling loop is electrically isolated from the MV/LV power path. Ground stud
# only handles bonding-grade currents: stray induced current from adjacent
# conductors, capacitive coupling via VFD comms shield, surge events.
# Conservative bonding-grade ground fault: 1 kA ±30% per IEEE Std 80-2013
# (substation grounding) — well below electrical-plate cases.
FAULT_CURRENT: Final = ufloat(1.0, 0.3) * ureg.kA
FAULT_DURATION: Final = (5 / 60) * ureg.s
R_JOINT_PER_BOLT: Final = ufloat(125, 75) * ureg.microohm

# --- Operating temperature range ---
T_AMBIENT_FAULT_C: Final = 25.0
DELTA_T_OPERATING: Final = 85.0 * ureg.kelvin

# --- Verdict thresholds (same as CG) ---
JOINT_TEMP_THRESHOLD_C: Final = 150.0

# --- Expected structural values from theory.ipynb ---
# Fault is ~1.3 kA worst-case +1sigma vs CG's 30.8 kA — temp rise scales as I²,
# so expected rise = 50.8 K * (1.3/30.8)² = ~0.09 K. Practically nil.
EXPECTED_JOINT_TEMP_RISE: Final = 0.09 * ureg.kelvin
EXPECTED_JOINT_TEMP_RISE_REL_TOL: Final = 0.50

# Thermal expansion identical to every other plate (same materials, same geometry).
EXPECTED_THERMAL_OFFSET: Final = 0.449 * ureg.mm
EXPECTED_THERMAL_OFFSET_REL_TOL: Final = 0.05

# --- Coolant sizing inputs (CD-specific, theory.ipynb cell `3b6a6f0d`) ---
HEAT_LOAD: Final = ufloat(70, 5) * ureg.kW
WATER_CP: Final = 4180.0 * ureg.J / (ureg.kg * ureg.kelvin)
WATER_DENSITY: Final = 1000.0 * ureg.kg / ureg.m**3
DELTA_T_SECONDARY: Final = ufloat(5, 1) * ureg.kelvin
QD_RATED_FLOW: Final = 250.0 * ureg.liter / ureg.minute  # Stäubli SBX 50

# --- Expected coolant values from theory.ipynb ---
EXPECTED_FLOW_PER_LINE: Final = 200.0 * ureg.liter / ureg.minute
EXPECTED_FLOW_REL_TOL: Final = 0.15
EXPECTED_QD_BODY_OD: Final = 75.0 * ureg.mm
