"""Assertions for CG plate structural analysis.

Validates analytical model output against theory.ipynb expected values
and against design-pass thresholds.
"""

import pytest

from sim.cg.constants import (
    BOLT_CLEARANCE_RADIAL,
    BOLT_DIAMETER,
    DELTA_T_DEFENSE,
    EXPECTED_JOINT_TEMP_RISE,
    EXPECTED_JOINT_TEMP_RISE_REL_TOL,
    EXPECTED_THERMAL_OFFSET,
    EXPECTED_THERMAL_OFFSET_DEFENSE,
    EXPECTED_THERMAL_OFFSET_REL_TOL,
    FAB_TOLERANCE,
    JOINT_TEMP_THRESHOLD_C,
    PATTERN_DIAGONAL,
    SAFETY_MARGIN,
    SLOT_LENGTH,
    T_AMBIENT_FAULT_C,
    ureg,
)
from sim.cg.model import solve


class TestCGPlate:
    """Assertions against theory.ipynb expected values."""

    def test_joint_temp_rise_matches_theory(self) -> None:
        """Adiabatic fault joint temp rise within tolerance of analytical value."""
        # arrange
        expected_k = EXPECTED_JOINT_TEMP_RISE.to(ureg.kelvin).magnitude
        # act
        actual_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert
        assert actual_k == pytest.approx(
            expected_k, rel=EXPECTED_JOINT_TEMP_RISE_REL_TOL
        )

    def test_joint_peak_temp_below_yield_threshold(self) -> None:
        """Peak joint temp during fault stays below 6061-T6 yield-derating threshold."""
        # arrange
        threshold_above_ambient_k = JOINT_TEMP_THRESHOLD_C - T_AMBIENT_FAULT_C
        # act
        actual_rise_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert
        assert actual_rise_k < threshold_above_ambient_k

    def test_thermal_offset_matches_theory(self) -> None:
        """Per-corner-bolt thermal offset matches free-expansion analytical."""
        # arrange
        expected_mm = EXPECTED_THERMAL_OFFSET.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(
            expected_mm, rel=EXPECTED_THERMAL_OFFSET_REL_TOL
        )

    def test_thermal_offset_under_clearance(self) -> None:
        """Thermal offset stays within bolt clearance hole (no shear interference)."""
        # arrange
        clearance_mm = BOLT_CLEARANCE_RADIAL.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm < clearance_mm

    def test_slot_accommodates_thermal_offset(self) -> None:
        """Adopted Option 1: radial slots at corners + long-axis midpoints.

        Slot extends ±(slot_length - hole_diameter)/2 beyond the hole center
        on each side. That radial extra must cover the worst-case sum of
        thermal offset + fab tolerance + safety margin.
        """
        # arrange
        slot_radial_extra_mm = ((SLOT_LENGTH - BOLT_DIAMETER) / 2).to(ureg.mm).magnitude
        fab_tol_mm = FAB_TOLERANCE.to(ureg.mm).magnitude
        margin_mm = SAFETY_MARGIN.to(ureg.mm).magnitude
        # act
        offset_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert — slot extra must cover offset + fab + safety margin per side
        budget_per_side_mm = offset_mm + fab_tol_mm + margin_mm
        assert slot_radial_extra_mm >= budget_per_side_mm, (
            f"slot radial extra {slot_radial_extra_mm:.2f}mm < "
            f"required budget {budget_per_side_mm:.2f}mm"
        )

    def test_thermal_offset_defense_matches_theory(self) -> None:
        """Defense ΔT=111K (MIL-STD-810H) gives 0.586mm offset (linear scale)."""
        # arrange
        expected_mm = EXPECTED_THERMAL_OFFSET_DEFENSE.to(ureg.mm).magnitude
        # act
        actual_mm = solve(delta_t=DELTA_T_DEFENSE).thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(
            expected_mm, rel=EXPECTED_THERMAL_OFFSET_REL_TOL
        )

    def test_slot_accommodates_defense_thermal_offset(self) -> None:
        """13mm slot has 0.11mm headroom even at defense ΔT=111K."""
        # arrange
        slot_radial_extra_mm = ((SLOT_LENGTH - BOLT_DIAMETER) / 2).to(ureg.mm).magnitude
        fab_tol_mm = FAB_TOLERANCE.to(ureg.mm).magnitude
        margin_mm = SAFETY_MARGIN.to(ureg.mm).magnitude
        # act
        offset_mm = solve(delta_t=DELTA_T_DEFENSE).thermal_offset.to(ureg.mm).magnitude
        # assert
        budget_per_side_mm = offset_mm + fab_tol_mm + margin_mm
        assert slot_radial_extra_mm >= budget_per_side_mm, (
            f"defense slot radial extra {slot_radial_extra_mm:.2f}mm < "
            f"required budget {budget_per_side_mm:.2f}mm"
        )

    def test_pattern_diagonal_matches_geometry(self) -> None:
        """Sanity: pattern diagonal derived from PATTERN_W + PATTERN_L."""
        # arrange
        expected_diagonal_mm = 888.0  # sqrt(520² + 720²)
        # act
        actual_mm = PATTERN_DIAGONAL.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(expected_diagonal_mm, rel=0.005)
