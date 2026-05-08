"""Assertions for CD plate analysis (structural + coolant flow)."""

import pytest

from sim.cd.constants import (
    BOLT_CLEARANCE_RADIAL,
    EXPECTED_FLOW_PER_LINE,
    EXPECTED_FLOW_REL_TOL,
    EXPECTED_JOINT_TEMP_RISE,
    EXPECTED_JOINT_TEMP_RISE_REL_TOL,
    EXPECTED_QD_BODY_OD,
    EXPECTED_THERMAL_OFFSET,
    EXPECTED_THERMAL_OFFSET_REL_TOL,
    JOINT_TEMP_THRESHOLD_C,
    QD_RATED_FLOW,
    T_AMBIENT_FAULT_C,
    ureg,
)
from sim.cd.model import solve, solve_coolant


class TestCDPlateStructural:
    """Structural assertions: same shape as every other plate."""

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
        """Peak joint temp under bonding-grade fault stays below yield threshold."""
        # arrange
        threshold_above_ambient_k = JOINT_TEMP_THRESHOLD_C - T_AMBIENT_FAULT_C
        # act
        actual_rise_k = solve().joint_temp_rise.to(ureg.kelvin).magnitude
        # assert — bonding-grade fault: huge headroom expected
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
        """Thermal offset stays within bolt clearance hole (no shear interference)."""
        # arrange
        clearance_mm = BOLT_CLEARANCE_RADIAL.to(ureg.mm).magnitude
        # act
        actual_mm = solve().thermal_offset.to(ureg.mm).magnitude
        # assert
        assert actual_mm < clearance_mm


class TestCDPlateCoolant:
    """Coolant sizing assertions specific to CD."""

    def test_flow_per_line_matches_theory(self) -> None:
        """Flow rate matches theory.ipynb derivation within ±15%."""
        # arrange
        expected_lpm = EXPECTED_FLOW_PER_LINE.to(ureg.liter / ureg.minute).magnitude
        # act
        actual_lpm = (
            solve_coolant().flow_per_line.to(ureg.liter / ureg.minute).magnitude
        )
        # assert
        assert actual_lpm == pytest.approx(expected_lpm, rel=EXPECTED_FLOW_REL_TOL)

    def test_flow_below_qd_rated_capacity(self) -> None:
        """Operating flow stays under Stäubli SBX 50 rated capacity."""
        # arrange
        rated_lpm = QD_RATED_FLOW.to(ureg.liter / ureg.minute).magnitude
        # act
        actual_lpm = (
            solve_coolant().flow_per_line.to(ureg.liter / ureg.minute).magnitude
        )
        # assert
        assert actual_lpm < rated_lpm

    def test_line_velocity_under_3_meters_per_second(self) -> None:
        """Line velocity at 2" bore stays under steel-pipe rule of thumb."""
        # arrange
        v_max_m_per_s = 3.0  # rule of thumb for steel pipe / QD bore
        # act
        actual_v = (
            solve_coolant().line_velocity_at_50mm_bore.to(ureg.m / ureg.s).magnitude
        )
        # assert
        assert actual_v < v_max_m_per_s

    def test_qd_body_od_matches_2_inch_class(self) -> None:
        """Pin the spec output: power_conduit_od_mm = 75 (2" class)."""
        # arrange / act / assert
        assert EXPECTED_QD_BODY_OD.to(ureg.mm).magnitude == pytest.approx(75.0, abs=0.5)
