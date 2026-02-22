"""Tests for legality graph deformation math."""
import pytest

from maelstrom.legality import (
    deform_transition,
    deform_all,
    canonical_path_admissible,
    canonical_path_penalty,
)
from maelstrom.types import TransitionSpec, MaelstromSpec, RegimeSpec


class TestDeformTransition:
    def test_zero_stress_preserves_baseline(self):
        t = TransitionSpec("a", "b", A=1.0, W=0.2, alpha=[0.0, 0.0], beta=[0.0, 0.0])
        dt = deform_transition(t, [0.5, 0.5])
        assert dt.A_prime == 1.0
        assert dt.W_prime == 0.2
        assert dt.admissible is True

    def test_high_stress_disables_transition(self):
        t = TransitionSpec("a", "b", A=0.5, W=0.1, alpha=[1.0, 0.0], beta=[0.0, 0.0])
        dt = deform_transition(t, [0.8, 0.0])
        assert dt.A_prime == pytest.approx(-0.3)
        assert dt.admissible is False

    def test_stress_increases_penalty(self):
        t = TransitionSpec("a", "b", A=1.0, W=0.1, alpha=[0.0, 0.0], beta=[0.5, 0.5])
        dt = deform_transition(t, [0.6, 0.4])
        expected_w = 0.1 + (0.5 * 0.6 + 0.5 * 0.4)
        assert dt.W_prime == pytest.approx(expected_w)

    def test_w_prime_floor_at_zero(self):
        t = TransitionSpec("a", "b", A=1.0, W=0.0, alpha=[0.0], beta=[-2.0])
        dt = deform_transition(t, [1.0])
        assert dt.W_prime == 0.0


class TestCanonicalPath:
    def _make_spec(self, a_values):
        transitions = [
            TransitionSpec(s, t, A=a, W=0.1, alpha=[0.0], beta=[0.0])
            for (s, t), a in zip([
                ("evaluate", "generate"), ("generate", "select"),
                ("select", "execute"), ("execute", "reflect"),
                ("reflect", "evaluate"),
            ], a_values)
        ]
        return MaelstromSpec(
            name="test", total_cycles=1, seed=0,
            stressor_names=["x"], stressor_schedule={},
            transitions=transitions,
            regimes=[RegimeSpec("peacetime", w=[0.0], u=[0.0]*6)],
            overlays=[], bypasses=[],
        )

    def test_all_admissible(self):
        spec = self._make_spec([1.0, 1.0, 1.0, 1.0, 1.0])
        deformed = deform_all(spec, [0.0])
        assert canonical_path_admissible(deformed) is True

    def test_one_blocked(self):
        spec = self._make_spec([1.0, 1.0, -0.1, 1.0, 1.0])
        deformed = deform_all(spec, [0.0])
        assert canonical_path_admissible(deformed) is False

    def test_penalty_sum(self):
        spec = self._make_spec([1.0] * 5)
        deformed = deform_all(spec, [0.0])
        assert canonical_path_penalty(deformed) == pytest.approx(0.5)
