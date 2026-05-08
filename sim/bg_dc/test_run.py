"""Assertions for BG-DC plate structural analysis (mirror of BG-AC tests)."""

import pytest

from sim.bg_dc.constants import (
    BOLT_CLEARANCE_RADIAL,
    EXPECTED_JOINT_TEMP_RISE,
    EXPECTED_JOINT_TEMP_RISE_REL_TOL,
    EXPECTED_THERMAL_OFFSET,
    EXPECTED_THERMAL_OFFSET_REL_TOL,
    JOINT_TEMP_THRESHOLD_C,
    T_AMBIENT_FAULT_C,
    ureg,
)
from sim.bg_dc.model import solve


class TestBGDCPlate:
    """Assertions against theory.ipynb expected values."""

    def test_joint_temp_rise_matches_theory(self) -> None:
        """Adiabatic DC fault joint temp rise within tolerance of analytical value."""
        # arrange
        expected_k = EXPECTED_JOINT_TEMP_RISE.to(ureg.kelvin).magnitude
        # act
        actual_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert
        assert actual_k == pytest.approx(
            expected_k, rel=EXPECTED_JOINT_TEMP_RISE_REL_TOL
        )

    def test_joint_peak_temp_below_yield_threshold(self) -> None:
        """Peak joint temp during DC fault stays below 6061-T6 yield-derating."""
        # arrange
        threshold_above_ambient_k = JOINT_TEMP_THRESHOLD_C - T_AMBIENT_FAULT_C
        # act
        actual_rise_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert
        assert actual_rise_k < threshold_above_ambient_k

    def test_thermal_offset_matches_theory(self) -> None:
        """Per-corner thermal offset matches free-expansion analytical."""
        # arrange
        expected_mm = EXPECTED_THERMAL_OFFSET.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(
            expected_mm, rel=EXPECTED_THERMAL_OFFSET_REL_TOL
        )

    def test_thermal_offset_under_clearance(self) -> None:
        """Thermal offset stays within bolt clearance hole."""
        # arrange
        clearance_mm = BOLT_CLEARANCE_RADIAL.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm < clearance_mm
