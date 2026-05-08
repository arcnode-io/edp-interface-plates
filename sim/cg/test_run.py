"""Assertions for CG plate structural analysis.

Validates analytical model output against theory.ipynb expected values
and against design-pass thresholds.
"""

import pytest

from sim.cg.constants import (
    BOLT_CLEARANCE_RADIAL,
    EXPECTED_JOINT_TEMP_RISE,
    EXPECTED_JOINT_TEMP_RISE_REL_TOL,
    EXPECTED_THERMAL_OFFSET,
    EXPECTED_THERMAL_OFFSET_REL_TOL,
    JOINT_TEMP_THRESHOLD_C,
    PATTERN_DIAGONAL,
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

    def test_thermal_margin_is_tight(self) -> None:
        """Pin the design risk: commercial CG has razor-thin thermal margin.

        Real fab tolerance (±0.1mm per ISO 2768-m) consumes most of this
        margin. Future revisions should slot corner bolt holes or specify
        tighter tolerance.
        """
        # arrange
        clearance_mm = BOLT_CLEARANCE_RADIAL.to(ureg.mm).magnitude
        # act
        offset_mm = solve().thermal_offset.to(ureg.mm).magnitude
        margin_mm = clearance_mm - offset_mm
        # assert — margin must be positive but is intentionally < 100 µm to
        # capture the design risk we surfaced via theory.
        assert margin_mm > 0
        assert margin_mm < 0.1

    def test_pattern_diagonal_matches_geometry(self) -> None:
        """Sanity: pattern diagonal derived from PATTERN_W + PATTERN_L."""
        # arrange
        expected_diagonal_mm = 888.0  # sqrt(520² + 720²)
        # act
        actual_mm = PATTERN_DIAGONAL.to(ureg.mm).magnitude
        # assert
        assert actual_mm == pytest.approx(expected_diagonal_mm, rel=0.005)
