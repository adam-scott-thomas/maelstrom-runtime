"""Tests for bypass eligibility and path collapse."""
import pytest

from maelstrom.bypasses import (
    BypassEligibility,
    check_bypass_eligibility,
    select_bypass,
    determine_execution_path,
)
from maelstrom.types import BypassSpec, DeformedTransition, CANONICAL_PHASES


def _make_deformed(admissible=True):
    """Create a minimal deformed graph with a single bypass transition."""
    return {
        "evaluate->execute": DeformedTransition(
            "evaluate", "execute", A_prime=1.0 if admissible else -0.1,
            W_prime=0.1, admissible=admissible,
        ),
    }


def _impulse_bypass(**overrides):
    defaults = dict(
        name="impulse",
        source_phase="evaluate",
        target_phase="execute",
        collapsed_path=["evaluate", "execute", "reflect"],
        eligible_regimes=["survival"],
        stressor_weights={"pressure": 1.0},
        latency_budget={"survival": 0.5},
    )
    defaults.update(overrides)
    return BypassSpec(**defaults)


class TestBypassEligibility:
    def test_eligible_when_conditions_met(self):
        bp = _impulse_bypass()
        results = check_bypass_eligibility(
            [bp], "survival", {"pressure": 0.8}, _make_deformed(),
        )
        assert len(results) == 1
        assert results[0].eligible is True

    def test_ineligible_wrong_regime(self):
        bp = _impulse_bypass()
        results = check_bypass_eligibility(
            [bp], "peacetime", {"pressure": 0.8}, _make_deformed(),
        )
        assert results[0].eligible is False

    def test_ineligible_low_intensity(self):
        bp = _impulse_bypass()
        results = check_bypass_eligibility(
            [bp], "survival", {"pressure": 0.3}, _make_deformed(),
        )
        assert results[0].eligible is False

    def test_ineligible_transition_blocked(self):
        bp = _impulse_bypass()
        results = check_bypass_eligibility(
            [bp], "survival", {"pressure": 0.8}, _make_deformed(admissible=False),
        )
        assert results[0].eligible is False


class TestPathDetermination:
    def test_canonical_without_bypass(self):
        path, event = determine_execution_path([], None)
        assert path == CANONICAL_PHASES
        assert event is None

    def test_bypass_collapses_path(self):
        bp = _impulse_bypass()
        eligibility = BypassEligibility(
            name="impulse", eligible=True,
            transition_admissible=True, stressor_intensity=0.8,
            latency_budget=0.5, regime="survival",
        )
        path, event = determine_execution_path([bp], eligibility)
        assert path == ["evaluate", "execute", "reflect"]
        assert event is not None
        assert event.name == "impulse"
        assert "generate" in event.skipped_phases
        assert "select" in event.skipped_phases
