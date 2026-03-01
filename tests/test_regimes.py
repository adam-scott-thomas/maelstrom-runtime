"""Tests for maelstrom_runtime.regimes — regime arbitration with ConstraintState."""
from __future__ import annotations

import pytest

from maelstrom.regimes import (
    CONSTRAINT_NAMES,
    ConstraintState,
    compute_all_penalties,
    compute_gradients,
    compute_penalty,
    constraint_state_dict,
    initial_constraint_state,
    regime_switch_trace,
    select_active_regime,
    update_constraint_state,
)
from maelstrom.spec import MaelstromSpec, RegimeSpec


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_spec(
    regime_defs: list[dict],
    stressor_names: list[str] | None = None,
) -> MaelstromSpec:
    """Build a minimal MaelstromSpec with the given regimes."""
    if stressor_names is None:
        stressor_names = ["threat", "cost", "time_pressure"]
    return MaelstromSpec(
        name="test",
        total_cycles=10,
        seed=42,
        stressor_names=stressor_names,
        stressor_schedule={s: [[0, 0.0]] for s in stressor_names},
        transitions=[],
        regimes=[RegimeSpec(**r) for r in regime_defs],
        overlays=[],
        bypasses=[],
    )


# ── ConstraintState NamedTuple ───────────────────────────────────────────


class TestConstraintState:
    def test_is_namedtuple(self):
        cs = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert hasattr(cs, "_fields")
        assert cs._fields == (
            "governance_disallow_count",
            "identity_veto_count",
            "coalition_veto_count",
            "coalition_drag",
            "bypass_count",
            "regime_age",
        )

    def test_constraint_names_matches_fields(self):
        assert CONSTRAINT_NAMES == list(ConstraintState._fields)

    def test_immutable(self):
        cs = ConstraintState(1.0, 2.0, 3.0, 0.5, 0.0, 10.0)
        with pytest.raises(AttributeError):
            cs.bypass_count = 5.0  # type: ignore[misc]

    def test_indexable_like_list(self):
        cs = ConstraintState(1.0, 2.0, 3.0, 0.5, 0.0, 10.0)
        assert cs[0] == 1.0
        assert cs[4] == 0.0
        assert len(cs) == 6


# ── initial_constraint_state ─────────────────────────────────────────────


class TestInitialConstraintState:
    def test_returns_constraint_state(self):
        cs = initial_constraint_state()
        assert isinstance(cs, ConstraintState)

    def test_all_zeros(self):
        cs = initial_constraint_state()
        for val in cs:
            assert val == 0.0

    def test_has_six_fields(self):
        cs = initial_constraint_state()
        assert len(cs) == 6


# ── compute_penalty ──────────────────────────────────────────────────────


class TestComputePenalty:
    def test_basic_dot_product(self):
        """P_r(t) = w . S(t) + u . C(t)"""
        w = [1.0, 0.0, 0.0]
        u = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        stressor = [0.5, 0.3, 0.2]
        constraint = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert compute_penalty(w, u, stressor, constraint) == pytest.approx(0.5)

    def test_both_terms_contribute(self):
        w = [1.0, 2.0]
        u = [0.5, 0.0, 0.0, 0.0, 0.0, 1.0]
        stressor = [0.4, 0.3]
        constraint = ConstraintState(1.0, 0.0, 0.0, 0.0, 0.0, 5.0)
        # w.S = 1.0*0.4 + 2.0*0.3 = 1.0
        # u.C = 0.5*1.0 + 0.0*0.0 + 0.0*0.0 + 0.0*0.0 + 0.0*0.0 + 1.0*5.0 = 5.5
        assert compute_penalty(w, u, stressor, constraint) == pytest.approx(6.5)

    def test_zero_stressors_and_constraints(self):
        w = [1.0, 1.0]
        u = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        stressor = [0.0, 0.0]
        constraint = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert compute_penalty(w, u, stressor, constraint) == 0.0


# ── compute_all_penalties ────────────────────────────────────────────────


class TestComputeAllPenalties:
    def test_returns_dict_for_each_regime(self):
        spec = _make_spec([
            {"name": "survival", "w": [0.8, 0.1, 0.1], "u": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            {"name": "peacetime", "w": [0.1, 0.4, 0.5], "u": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        ])
        stressor = [0.5, 0.3, 0.2]
        cs = initial_constraint_state()
        result = compute_all_penalties(spec, stressor, cs)
        assert "survival" in result
        assert "peacetime" in result

    def test_values_match_individual_compute(self):
        spec = _make_spec([
            {"name": "survival", "w": [0.8, 0.1, 0.1], "u": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            {"name": "peacetime", "w": [0.1, 0.4, 0.5], "u": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]},
        ])
        stressor = [0.5, 0.3, 0.2]
        cs = ConstraintState(1.0, 0.0, 0.0, 0.0, 0.0, 3.0)
        result = compute_all_penalties(spec, stressor, cs)

        expected_survival = compute_penalty(
            [0.8, 0.1, 0.1], [1.0, 0.0, 0.0, 0.0, 0.0, 0.0], stressor, cs
        )
        expected_peacetime = compute_penalty(
            [0.1, 0.4, 0.5], [0.0, 0.0, 0.0, 0.0, 0.0, 1.0], stressor, cs
        )
        assert result["survival"] == pytest.approx(expected_survival)
        assert result["peacetime"] == pytest.approx(expected_peacetime)


# ── compute_gradients ────────────────────────────────────────────────────


class TestComputeGradients:
    def test_first_cycle_gradient_equals_penalty(self):
        """On the first cycle (no history), gradient = penalty itself."""
        penalties = {"survival": 0.7, "peacetime": 0.2}
        grads = compute_gradients(penalties, penalty_history=[], window=1)
        assert grads["survival"] == pytest.approx(0.7)
        assert grads["peacetime"] == pytest.approx(0.2)

    def test_window_1_delta(self):
        """With window=1, gradient = current - previous."""
        prev = {"survival": 0.3, "peacetime": 0.5}
        curr = {"survival": 0.8, "peacetime": 0.4}
        grads = compute_gradients(curr, penalty_history=[prev], window=1)
        assert grads["survival"] == pytest.approx(0.5)
        assert grads["peacetime"] == pytest.approx(-0.1)

    def test_window_2_averages(self):
        """With window=2, gradient = (current - 2-ago) / 2."""
        history = [
            {"survival": 0.2, "peacetime": 0.6},
            {"survival": 0.5, "peacetime": 0.5},
        ]
        curr = {"survival": 0.8, "peacetime": 0.4}
        grads = compute_gradients(curr, penalty_history=history, window=2)
        # lookback=2: past = history[-2] = history[0]
        assert grads["survival"] == pytest.approx((0.8 - 0.2) / 2)
        assert grads["peacetime"] == pytest.approx((0.4 - 0.6) / 2)

    def test_window_larger_than_history(self):
        """If window > len(history), lookback clamps to len(history)."""
        history = [{"survival": 0.1, "peacetime": 0.1}]
        curr = {"survival": 0.5, "peacetime": 0.5}
        grads = compute_gradients(curr, penalty_history=history, window=5)
        # lookback = min(5, 1) = 1
        assert grads["survival"] == pytest.approx(0.4)
        assert grads["peacetime"] == pytest.approx(0.4)


# ── select_active_regime ─────────────────────────────────────────────────


class TestSelectActiveRegime:
    def test_picks_highest_gradient(self):
        grads = {"survival": 0.9, "peacetime": 0.2, "economic": 0.5}
        result = select_active_regime(grads)
        assert result == "survival"

    def test_tiebreak_uses_regime_priority(self):
        """When two regimes have equal gradients, survival wins over peacetime
        because it has lower REGIME_PRIORITY index."""
        grads = {"survival": 0.5, "peacetime": 0.5}
        result = select_active_regime(grads)
        assert result == "survival"

    def test_tiebreak_legal_over_economic(self):
        grads = {"legal": 0.5, "economic": 0.5}
        result = select_active_regime(grads)
        assert result == "legal"

    def test_scalar_inertia_keeps_current(self):
        """Scalar inertia gives current regime a bonus, preventing switch."""
        grads = {"survival": 0.5, "peacetime": 0.45}
        # Without inertia, survival wins. With inertia=0.1 and current=peacetime:
        # peacetime adjusted = 0.45 + 0.1 = 0.55 > 0.5
        result = select_active_regime(grads, current_regime="peacetime", inertia=0.1)
        assert result == "peacetime"

    def test_scalar_inertia_allows_switch_when_gradient_dominates(self):
        """If challenger gradient exceeds inertia margin, switch happens."""
        grads = {"survival": 1.0, "peacetime": 0.3}
        # peacetime adjusted = 0.3 + 0.1 = 0.4, still < 1.0
        result = select_active_regime(grads, current_regime="peacetime", inertia=0.1)
        assert result == "survival"

    def test_asymmetric_inertia_easy_enter_survival(self):
        """Survival should be easy to enter (low into_survival) and hard to
        leave (high out_of_survival)."""
        inertia = {
            "default": 0.0,
            "out_of_survival": 0.5,   # hard to leave survival
            "into_survival": 0.0,     # easy to enter survival
            "out_of_peacetime": 0.1,  # moderately sticky peacetime
            "into_peacetime": 0.3,    # hard to enter peacetime
        }
        grads = {"survival": 0.6, "peacetime": 0.5}
        # Currently peacetime: out_of_peacetime=0.1 bonus to peacetime
        # survival faces into_survival=0.0 penalty
        # peacetime faces into_peacetime=0.3 penalty (but is current, so not applied)
        # adjusted: survival=0.6, peacetime=0.5+0.1=0.6
        # Tie: survival wins via priority
        result = select_active_regime(grads, current_regime="peacetime", inertia=inertia)
        assert result == "survival"

    def test_asymmetric_inertia_hard_leave_survival(self):
        """Once in survival, high out_of_survival keeps us there."""
        inertia = {
            "default": 0.0,
            "out_of_survival": 0.5,
            "into_survival": 0.0,
            "out_of_peacetime": 0.1,
            "into_peacetime": 0.3,
        }
        grads = {"survival": 0.4, "peacetime": 0.6}
        # Currently survival: out_of_survival=0.5 bonus to survival
        # peacetime faces into_peacetime=0.3 penalty
        # adjusted: survival=0.4+0.5=0.9, peacetime=0.6-0.3=0.3
        result = select_active_regime(grads, current_regime="survival", inertia=inertia)
        assert result == "survival"

    def test_no_current_regime_selects_argmax(self):
        """When current_regime is None, no inertia is applied."""
        grads = {"survival": 0.3, "peacetime": 0.5}
        result = select_active_regime(grads, current_regime=None, inertia=0.2)
        assert result == "peacetime"

    def test_returns_peacetime_fallback_on_empty(self):
        """Edge case: empty gradients should return peacetime."""
        result = select_active_regime({})
        assert result == "peacetime"


# ── regime_switch_trace ──────────────────────────────────────────────────


class TestRegimeSwitchTrace:
    def test_blocked_by_inertia(self):
        """When inertia prevents a switch, blocked_by_inertia is True."""
        grads = {"survival": 0.5, "peacetime": 0.45}
        # Without inertia survival would win; with inertia peacetime stays
        selected = select_active_regime(grads, current_regime="peacetime", inertia=0.1)
        assert selected == "peacetime"

        trace = regime_switch_trace(grads, "peacetime", selected, inertia=0.1)
        assert trace["blocked_by_inertia"] is True
        assert trace["raw_winner"] == "survival"
        assert trace["selected_regime"] == "peacetime"
        assert trace["current_regime"] == "peacetime"

    def test_not_blocked_when_switch_happens(self):
        grads = {"survival": 1.0, "peacetime": 0.2}
        selected = select_active_regime(grads, current_regime="peacetime", inertia=0.1)
        assert selected == "survival"

        trace = regime_switch_trace(grads, "peacetime", selected, inertia=0.1)
        assert trace["blocked_by_inertia"] is False
        assert trace["selected_regime"] == "survival"
        assert trace["raw_winner"] == "survival"

    def test_trace_contains_expected_keys(self):
        grads = {"survival": 0.5, "peacetime": 0.3}
        trace = regime_switch_trace(grads, "peacetime", "survival", inertia=0.0)
        expected_keys = {
            "raw_gradients",
            "adjusted_gradients",
            "current_regime",
            "selected_regime",
            "raw_winner",
            "best_challenger",
            "challenger_gradient",
            "winner_margin",
            "out_of_bonus",
            "into_penalties",
            "blocked_by_inertia",
        }
        assert set(trace.keys()) == expected_keys

    def test_winner_margin_is_positive(self):
        grads = {"survival": 0.8, "peacetime": 0.3}
        trace = regime_switch_trace(grads, None, "survival", inertia=0.0)
        assert trace["winner_margin"] == pytest.approx(0.5)

    def test_best_challenger_when_current_set(self):
        grads = {"survival": 0.8, "peacetime": 0.3, "economic": 0.5}
        trace = regime_switch_trace(grads, "survival", "survival", inertia=0.0)
        assert trace["best_challenger"] == "economic"
        assert trace["challenger_gradient"] == pytest.approx(0.5)

    def test_no_challenger_when_current_is_none(self):
        grads = {"survival": 0.5}
        trace = regime_switch_trace(grads, None, "survival", inertia=0.0)
        assert trace["best_challenger"] is None
        assert trace["challenger_gradient"] is None


# ── update_constraint_state ──────────────────────────────────────────────


class TestUpdateConstraintState:
    def test_returns_constraint_state(self):
        prev = initial_constraint_state()
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
        )
        assert isinstance(result, ConstraintState)

    def test_bypass_count_exponential_decay(self):
        prev = ConstraintState(0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        # With bypass_activated=True, new = 1.0 * 0.8 + 1.0 = 1.8
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=True,
            regime_changed=False,
            decay=0.8,
        )
        assert result.bypass_count == pytest.approx(1.8)

    def test_bypass_count_decay_only(self):
        prev = ConstraintState(0.0, 0.0, 0.0, 0.0, 2.0, 0.0)
        # With bypass_activated=False, new = 2.0 * 0.8 + 0.0 = 1.6
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
            decay=0.8,
        )
        assert result.bypass_count == pytest.approx(1.6)

    def test_regime_age_resets_on_change(self):
        prev = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 10.0)
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=True,
        )
        assert result.regime_age == 0.0

    def test_regime_age_increments_without_change(self):
        prev = ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 5.0)
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
        )
        assert result.regime_age == 6.0

    def test_governance_disallow_set(self):
        prev = initial_constraint_state()
        result = update_constraint_state(
            prev,
            governance_disallow=True,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
        )
        # From zero: 0.0 * 0.8 + 1.0 = 1.0
        assert result.governance_disallow_count == pytest.approx(1.0)
        assert result.identity_veto_count == pytest.approx(0.0)

    def test_governance_disallow_decays(self):
        """Governance disallow count uses exponential decay, not binary."""
        prev = ConstraintState(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
            decay=0.8,
        )
        # 1.0 * 0.8 + 0.0 = 0.8 (decayed, not snapped to zero)
        assert result.governance_disallow_count == pytest.approx(0.8)

    def test_identity_veto_decays(self):
        """Identity veto count uses exponential decay."""
        prev = ConstraintState(0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
            decay=0.8,
        )
        assert result.identity_veto_count == pytest.approx(0.8)

    def test_coalition_veto_decays(self):
        """Coalition veto count uses exponential decay."""
        prev = ConstraintState(0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        result = update_constraint_state(
            prev,
            governance_disallow=False,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=False,
            regime_changed=False,
            decay=0.8,
        )
        assert result.coalition_veto_count == pytest.approx(0.8)

    def test_all_flags_set(self):
        prev = initial_constraint_state()
        result = update_constraint_state(
            prev,
            governance_disallow=True,
            identity_veto=True,
            coalition_veto=True,
            coalition_drag=0.75,
            bypass_activated=True,
            regime_changed=True,
        )
        # All from zero: 0.0 * 0.8 + 1.0 = 1.0
        assert result.governance_disallow_count == pytest.approx(1.0)
        assert result.identity_veto_count == pytest.approx(1.0)
        assert result.coalition_veto_count == pytest.approx(1.0)
        assert result.coalition_drag == 0.75
        assert result.bypass_count == pytest.approx(1.0)  # 0.0 * 0.8 + 1.0
        assert result.regime_age == 0.0  # reset on regime_changed

    def test_immutability_of_prev(self):
        """update_constraint_state must not mutate the previous state."""
        prev = initial_constraint_state()
        _ = update_constraint_state(
            prev,
            governance_disallow=True,
            identity_veto=True,
            coalition_veto=True,
            coalition_drag=0.5,
            bypass_activated=True,
            regime_changed=True,
        )
        # NamedTuple is inherently immutable, so prev should remain zeros
        assert all(v == 0.0 for v in prev)


# ── constraint_state_dict ────────────────────────────────────────────────


class TestConstraintStateDict:
    def test_returns_dict_with_named_keys(self):
        cs = ConstraintState(1.0, 0.0, 1.0, 0.5, 2.3, 7.0)
        d = constraint_state_dict(cs)
        assert d == {
            "governance_disallow_count": 1.0,
            "identity_veto_count": 0.0,
            "coalition_veto_count": 1.0,
            "coalition_drag": 0.5,
            "bypass_count": 2.3,
            "regime_age": 7.0,
        }

    def test_initial_state_dict_is_all_zeros(self):
        cs = initial_constraint_state()
        d = constraint_state_dict(cs)
        assert all(v == 0.0 for v in d.values())
        assert len(d) == 6
