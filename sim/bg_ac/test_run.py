"""Assertions for BG-AC plate structural analysis.

Same load cases as CG. BG-AC sees lower fault current (BESS-side) so
joint heating is much smaller; thermal expansion is identical to CG
(same materials, same geometry).
"""

import pytest

from sim.bg_ac.constants import (
    BOLT_CLEARANCE_RADIAL,
    DELTA_T_DEFENSE,
    EXPECTED_JOINT_TEMP_RISE,
    EXPECTED_JOINT_TEMP_RISE_REL_TOL,
    EXPECTED_THERMAL_OFFSET,
    EXPECTED_THERMAL_OFFSET_DEFENSE,
    EXPECTED_THERMAL_OFFSET_REL_TOL,
    JOINT_TEMP_THRESHOLD_C,
    T_AMBIENT_FAULT_C,
    ureg,
)
from sim.bg_ac.model import solve


class TestBGACPlate:
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
        """BG-AC fault is much smaller than CG; comfortable margin."""
        # arrange
        threshold_above_ambient_k = JOINT_TEMP_THRESHOLD_C - T_AMBIENT_FAULT_C
        # act
        actual_rise_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert
        assert actual_rise_k < threshold_above_ambient_k

    def test_thermal_offset_matches_theory(self) -> None:
        """Identical thermal expansion to CG (same materials + geometry)."""
        # arrange
        expected_mm = EXPECTED_THERMAL_OFFSET.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(
            expected_mm, rel=EXPECTED_THERMAL_OFFSET_REL_TOL
        )

    def test_thermal_offset_under_clearance(self) -> None:
        """Same razor-thin margin as CG — same plate, same risk."""
        # arrange
        clearance_mm = BOLT_CLEARANCE_RADIAL.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm < clearance_mm

    def test_thermal_offset_defense_matches_theory(self) -> None:
        """Defense ΔT=111K (MIL-STD-810H) gives 0.586mm offset."""
        # arrange
        expected_mm = EXPECTED_THERMAL_OFFSET_DEFENSE.to(ureg.mm).magnitude
        # act
        actual_mm = solve(delta_t=DELTA_T_DEFENSE).thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(
            expected_mm, rel=EXPECTED_THERMAL_OFFSET_REL_TOL
        )
