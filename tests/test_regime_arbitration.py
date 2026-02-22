"""Tests for regime penalty computation and gradient-based selection."""
import pytest

from maelstrom.regimes import (
    ConstraintState,
    compute_penalty,
    compute_all_penalties,
    compute_gradients,
    initial_constraint_state,
    select_active_regime,
    update_constraint_state,
)
from maelstrom.types import MaelstromSpec, RegimeSpec, TransitionSpec


class TestPenaltyComputation:
    def test_zero_stressors_zero_penalty(self):
        w = [0.5, 0.5]
        u = [0.0] * 6
        s = [0.0, 0.0]
        c = initial_constraint_state()
        assert compute_penalty(w, u, s, c) == 0.0

    def test_unit_stressors(self):
        w = [0.3, 0.7]
        u = [0.0] * 6
        s = [1.0, 1.0]
        c = initial_constraint_state()
        assert abs(compute_penalty(w, u, s, c) - 1.0) < 1e-9

    def test_constraint_contribution(self):
        w = [0.0, 0.0]
        u = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        s = [0.0, 0.0]
        c = ConstraintState(0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(compute_penalty(w, u, s, c) - 0.5) < 1e-9


class TestGradients:
    def test_first_cycle_gradient_equals_penalty(self):
        penalties = {"survival": 0.6, "peacetime": 0.1}
        g = compute_gradients(penalties, [])
        assert g == penalties

    def test_gradient_with_history(self):
        past = {"survival": 0.3, "peacetime": 0.1}
        current = {"survival": 0.6, "peacetime": 0.2}
        g = compute_gradients(current, [past])
        assert abs(g["survival"] - 0.3) < 1e-9
        assert abs(g["peacetime"] - 0.1) < 1e-9


class TestRegimeSelection:
    def test_highest_gradient_wins(self):
        g = {"survival": 0.9, "peacetime": 0.1, "legal": 0.3}
        assert select_active_regime(g) == "survival"

    def test_inertia_keeps_current(self):
        g = {"survival": 0.5, "peacetime": 0.45}
        assert select_active_regime(g, current_regime="peacetime", inertia=0.1) == "peacetime"

    def test_deterministic_tiebreak(self):
        g = {"legal": 0.5, "moral": 0.5, "economic": 0.5}
        assert select_active_regime(g) == "legal"


class TestConstraintStateUpdate:
    def test_decay(self):
        c = ConstraintState(1.0, 0.0, 0.0, 0.0, 0.0, 5.0)
        c2 = update_constraint_state(c, False, False, False, 0.0, False, False)
        assert c2.governance_disallow_count == 0.8
        assert c2.regime_age == 6.0

    def test_regime_change_resets_age(self):
        c = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 10.0)
        c2 = update_constraint_state(c, False, False, False, 0.0, False, True)
        assert c2.regime_age == 0.0
