"""Assertions for L-bracket bolted connection FEM analysis.

Validates bolt reaction forces against bolt group hand calc,
and bracket stress against yield.
"""

import pytest

from sim.constants import (
    CRITICAL_BOLT_FORCE,
    YIELD_STRESS,
    ureg,
)
from sim.model import solve


class TestLBracket:
    """Assertions against theory.ipynb expected values."""

    def test_bolt_reaction_force(self) -> None:
        """FEM critical bolt reaction vs bolt group hand calc within 35%.

        Reason: hand calc assumes rigid bracket with symmetric bolt group
        (conservative). FEM captures bracket flexibility and asymmetric bolt
        pattern (offset up for bolt head clearance). 35% tolerance accounts
        for rigid assumption + pattern asymmetry.
        """
        # arrange
        expected_n = CRITICAL_BOLT_FORCE.to(ureg.N).magnitude

        # act
        bolt_force_n, _ = solve()

        # assert
        assert bolt_force_n == pytest.approx(expected_n, rel=0.35)

    def test_bracket_stress_below_yield(self) -> None:
        """Peak von Mises stress is below yield (safety factor > 1)."""
        # arrange
        yield_mpa = YIELD_STRESS.to(ureg.MPa).magnitude

        # act
        _, max_stress_mpa = solve()

        # assert
        assert max_stress_mpa < yield_mpa
