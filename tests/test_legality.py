"""Tests for maelstrom_runtime.legality — graph deformation per Appendix A.1."""
from __future__ import annotations

import pytest

from maelstrom.spec import MaelstromSpec, TransitionSpec
from maelstrom.legality import (
    DeformedTransition,
    deform_transition,
    deform_all,
    legality_summary,
    canonical_path_penalty,
    canonical_path_admissible,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_transition(
    source: str = "evaluate",
    target: str = "generate",
    A: float = 1.0,
    W: float = 0.5,
    alpha: list[float] | None = None,
    beta: list[float] | None = None,
) -> TransitionSpec:
    return TransitionSpec(
        source=source,
        target=target,
        A=A,
        W=W,
        alpha=alpha or [0.1, 0.2],
        beta=beta or [0.3, 0.1],
    )


def _make_canonical_spec() -> MaelstromSpec:
    """Spec with all five canonical transitions E->G->S->X->R->E."""
    transitions = [
        TransitionSpec("evaluate", "generate", A=1.0, W=0.5, alpha=[0.2, 0.1], beta=[0.1, 0.2]),
        TransitionSpec("generate", "select", A=0.8, W=0.3, alpha=[0.3, 0.0], beta=[0.2, 0.1]),
        TransitionSpec("select", "execute", A=0.9, W=0.4, alpha=[0.1, 0.2], beta=[0.0, 0.3]),
        TransitionSpec("execute", "reflect", A=0.7, W=0.6, alpha=[0.2, 0.3], beta=[0.1, 0.0]),
        TransitionSpec("reflect", "evaluate", A=1.0, W=0.05, alpha=[0.01, 0.01], beta=[0.02, 0.02]),
    ]
    return MaelstromSpec(
        name="canonical_test",
        total_cycles=10,
        seed=42,
        stressor_names=["threat", "cost"],
        stressor_schedule={"threat": [[0, 0.0]], "cost": [[0, 0.0]]},
        transitions=transitions,
        regimes=[],
        overlays=[],
        bypasses=[],
    )


# ── No stress preserves base values ─────────────────────────────────────


class TestNoStress:
    def test_zero_stressor_preserves_A(self):
        t = _make_transition(A=1.0)
        dt = deform_transition(t, [0.0, 0.0])
        assert dt.A_prime == 1.0

    def test_zero_stressor_preserves_W(self):
        t = _make_transition(W=0.5)
        dt = deform_transition(t, [0.0, 0.0])
        assert dt.W_prime == 0.5

    def test_zero_stressor_admissible(self):
        t = _make_transition(A=1.0)
        dt = deform_transition(t, [0.0, 0.0])
        assert dt.admissible is True

    def test_source_target_preserved(self):
        t = _make_transition(source="evaluate", target="generate")
        dt = deform_transition(t, [0.0, 0.0])
        assert dt.source == "evaluate"
        assert dt.target == "generate"


# ── High stress reduces admissibility ────────────────────────────────────


class TestHighStress:
    def test_high_stress_reduces_A_prime(self):
        t = _make_transition(A=0.5, alpha=[1.0, 0.0])
        dt = deform_transition(t, [0.6, 0.0])
        # A' = 0.5 - 1.0 * 0.6 = -0.1
        assert dt.A_prime == pytest.approx(-0.1)

    def test_high_stress_marks_inadmissible(self):
        t = _make_transition(A=0.5, alpha=[1.0, 0.0])
        dt = deform_transition(t, [0.6, 0.0])
        assert dt.admissible is False

    def test_exactly_zero_A_prime_is_inadmissible(self):
        """A'_ij(t) <= 0 means disallowed (boundary case)."""
        t = _make_transition(A=0.5, alpha=[0.5, 0.0])
        dt = deform_transition(t, [1.0, 0.0])
        # A' = 0.5 - 0.5 * 1.0 = 0.0
        assert dt.A_prime == pytest.approx(0.0)
        assert dt.admissible is False

    def test_barely_positive_A_prime_is_admissible(self):
        t = _make_transition(A=0.5, alpha=[0.499, 0.0])
        dt = deform_transition(t, [1.0, 0.0])
        # A' = 0.5 - 0.499 = 0.001
        assert dt.A_prime > 0
        assert dt.admissible is True


# ── Stress increases weight ──────────────────────────────────────────────


class TestStressIncreasesWeight:
    def test_positive_stress_increases_W_prime(self):
        t = _make_transition(W=0.5, beta=[0.3, 0.1])
        dt = deform_transition(t, [1.0, 1.0])
        # W' = 0.5 + 0.3*1.0 + 0.1*1.0 = 0.9
        assert dt.W_prime == pytest.approx(0.9)

    def test_multi_stressor_W_accumulates(self):
        t = _make_transition(W=0.2, beta=[0.5, 0.5])
        dt = deform_transition(t, [0.4, 0.6])
        # W' = 0.2 + 0.5*0.4 + 0.5*0.6 = 0.2 + 0.2 + 0.3 = 0.7
        assert dt.W_prime == pytest.approx(0.7)


# ── W_prime clamped >= 0 ────────────────────────────────────────────────


class TestWPrimeClamped:
    def test_negative_beta_clamped_at_zero(self):
        """W' should never go below 0 even with negative beta dot S."""
        t = _make_transition(W=0.1, beta=[-1.0, -1.0])
        dt = deform_transition(t, [1.0, 1.0])
        # W' = 0.1 + (-1.0)*1.0 + (-1.0)*1.0 = -1.9 -> clamped to 0.0
        assert dt.W_prime == 0.0

    def test_small_W_negative_product_clamped(self):
        t = _make_transition(W=0.05, beta=[-0.1, 0.0])
        dt = deform_transition(t, [1.0, 0.0])
        # W' = 0.05 + (-0.1)*1.0 = -0.05 -> clamped to 0.0
        assert dt.W_prime == 0.0


# ── Canonical path admissibility ─────────────────────────────────────────


class TestCanonicalPath:
    def test_all_admissible_under_no_stress(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        assert canonical_path_admissible(deformed) is True

    def test_not_admissible_when_one_blocked(self):
        """Block generate->select by overwhelming stress."""
        spec = _make_canonical_spec()
        # generate->select has A=0.8, alpha=[0.3, 0.0]
        # Need 0.8 - 0.3*S <= 0 => S >= 2.667
        deformed = deform_all(spec, [3.0, 0.0])
        assert canonical_path_admissible(deformed) is False

    def test_canonical_penalty_under_no_stress(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        # Sum of base weights: 0.5 + 0.3 + 0.4 + 0.6 + 0.05 = 1.85
        assert canonical_path_penalty(deformed) == pytest.approx(1.85)

    def test_canonical_penalty_increases_under_stress(self):
        spec = _make_canonical_spec()
        deformed_zero = deform_all(spec, [0.0, 0.0])
        deformed_high = deform_all(spec, [1.0, 1.0])
        assert canonical_path_penalty(deformed_high) > canonical_path_penalty(deformed_zero)

    def test_canonical_keys_are_present(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        expected_keys = {
            "evaluate->generate",
            "generate->select",
            "select->execute",
            "execute->reflect",
            "reflect->evaluate",
        }
        assert expected_keys == set(deformed.keys())


# ── Governance disallow (transition blocked) ─────────────────────────────


class TestGovernanceDisallow:
    def test_blocked_transition_not_admissible(self):
        """When stress drives A' <= 0, the transition must be disallowed."""
        t = _make_transition(source="select", target="execute", A=0.3, alpha=[0.5, 0.0])
        dt = deform_transition(t, [1.0, 0.0])
        # A' = 0.3 - 0.5*1.0 = -0.2
        assert dt.admissible is False
        assert dt.A_prime < 0

    def test_deform_all_marks_blocked_transitions(self):
        """In deform_all, transitions with A' <= 0 are marked inadmissible."""
        spec = _make_canonical_spec()
        # Extreme stress to block at least some transitions
        deformed = deform_all(spec, [5.0, 5.0])
        blocked = [k for k, dt in deformed.items() if not dt.admissible]
        assert len(blocked) > 0, "Expected at least one blocked transition under extreme stress"


# ── deform_all ───────────────────────────────────────────────────────────


class TestDeformAll:
    def test_returns_dict_keyed_by_source_target(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        for key, dt in deformed.items():
            assert "->" in key
            parts = key.split("->")
            assert parts[0] == dt.source
            assert parts[1] == dt.target

    def test_all_deformed_transitions_are_correct_type(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        for dt in deformed.values():
            assert isinstance(dt, DeformedTransition)


# ── legality_summary ─────────────────────────────────────────────────────


class TestLegalitySummary:
    def test_summary_keys_match_deformed_keys(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.5, 0.5])
        summary = legality_summary(deformed)
        assert set(summary.keys()) == set(deformed.keys())

    def test_summary_contains_expected_fields(self):
        spec = _make_canonical_spec()
        deformed = deform_all(spec, [0.0, 0.0])
        summary = legality_summary(deformed)
        for key, info in summary.items():
            assert "A_prime" in info
            assert "W_prime" in info
            assert "admissible" in info

    def test_summary_values_are_rounded(self):
        t = _make_transition(A=1.0, alpha=[0.33333333, 0.0])
        dt = deform_transition(t, [1.0, 0.0])
        summary = legality_summary({"test": dt})
        # A' = 1.0 - 0.33333333 = 0.66666667, rounded to 6 decimals
        assert summary["test"]["A_prime"] == round(dt.A_prime, 6)
