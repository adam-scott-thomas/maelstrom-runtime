"""Tests for maelstrom_runtime.bypasses — adaptive phase-collapsing dynamics."""
from __future__ import annotations

import pytest

from maelstrom.spec import BypassSpec
from maelstrom.legality import DeformedTransition
from maelstrom.bypasses import (
    CANONICAL_PHASES,
    BYPASS_REPLACES,
    BypassEligibility,
    BypassEvent,
    check_bypass_eligibility,
    select_bypass,
    determine_execution_path,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_bypass(
    name: str = "impulse",
    source_phase: str = "evaluate",
    target_phase: str = "execute",
    collapsed_path: list[str] | None = None,
    eligible_regimes: list[str] | None = None,
    stressor_weights: dict[str, float] | None = None,
    latency_budget: dict[str, float] | None = None,
) -> BypassSpec:
    return BypassSpec(
        name=name,
        source_phase=source_phase,
        target_phase=target_phase,
        collapsed_path=collapsed_path or ["evaluate", "execute", "reflect"],
        eligible_regimes=eligible_regimes or ["survival"],
        stressor_weights=stressor_weights or {"threat": 1.0},
        latency_budget=latency_budget or {"survival": 0.5},
    )


def _make_deformed(
    transitions: dict[str, tuple[float, float]] | None = None,
) -> dict[str, DeformedTransition]:
    """Build a deformed-transition map.

    *transitions* maps "source->target" to (A_prime, W_prime).
    Defaults to the full canonical set with all admissible.
    """
    defaults: dict[str, tuple[float, float]] = {
        "evaluate->generate": (0.8, 0.5),
        "generate->select": (0.7, 0.3),
        "select->execute": (0.6, 0.4),
        "execute->reflect": (0.5, 0.6),
        # Bypass transitions
        "evaluate->execute": (0.4, 0.2),
        "evaluate->reflect": (0.3, 0.3),
        "generate->execute": (0.5, 0.25),
        "select->reflect": (0.4, 0.35),
        "reflect->generate": (0.3, 0.15),
    }
    if transitions:
        defaults.update(transitions)
    result = {}
    for key, (a, w) in defaults.items():
        src, tgt = key.split("->")
        result[key] = DeformedTransition(
            source=src, target=tgt, A_prime=a, W_prime=w, admissible=a > 0,
        )
    return result


# ── CANONICAL_PHASES ─────────────────────────────────────────────────────


class TestCanonicalPhases:
    def test_canonical_phase_order(self):
        assert CANONICAL_PHASES == [
            "evaluate", "generate", "select", "execute", "reflect",
        ]


# ── Eligible when all conditions met ─────────────────────────────────────


class TestEligibleAllConditionsMet:
    """Bypass eligible: regime matches, intensity > budget, transition admissible."""

    def test_impulse_eligible(self):
        bp = _make_bypass(
            name="impulse",
            eligible_regimes=["survival"],
            stressor_weights={"threat": 1.0},
            latency_budget={"survival": 0.5},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.8},  # 0.8 > 0.5 budget
            deformed=deformed,
        )
        assert len(results) == 1
        assert results[0].eligible is True
        assert results[0].name == "impulse"
        assert results[0].regime == "survival"

    def test_stressor_intensity_correct(self):
        bp = _make_bypass(
            stressor_weights={"threat": 0.6, "cost": 0.4},
            latency_budget={"survival": 0.3},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.5, "cost": 0.5},
            deformed=deformed,
        )
        # intensity = 0.6*0.5 + 0.4*0.5 = 0.5
        assert results[0].stressor_intensity == pytest.approx(0.5)

    def test_latency_budget_is_per_bypass(self):
        """Each bypass uses its own latency_budget, not a global one."""
        bp_low = _make_bypass(
            name="impulse",
            latency_budget={"survival": 0.3},
            stressor_weights={"threat": 1.0},
        )
        bp_high = _make_bypass(
            name="mania",
            source_phase="generate",
            target_phase="execute",
            collapsed_path=["generate", "execute", "reflect"],
            eligible_regimes=["survival"],
            latency_budget={"survival": 0.9},
            stressor_weights={"threat": 1.0},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp_low, bp_high],
            active_regime="survival",
            stressor_map={"threat": 0.5},  # exceeds 0.3 but not 0.9
            deformed=deformed,
        )
        assert results[0].eligible is True   # impulse: 0.5 > 0.3
        assert results[1].eligible is False  # mania: 0.5 < 0.9


# ── Ineligible: wrong regime ─────────────────────────────────────────────


class TestIneligibleWrongRegime:
    def test_wrong_regime_ineligible(self):
        bp = _make_bypass(eligible_regimes=["survival"])
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="epistemic",
            stressor_map={"threat": 0.8},
            deformed=deformed,
        )
        assert results[0].eligible is False


# ── Ineligible: low intensity ────────────────────────────────────────────


class TestIneligibleLowIntensity:
    def test_below_budget_ineligible(self):
        bp = _make_bypass(
            stressor_weights={"threat": 1.0},
            latency_budget={"survival": 0.9},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.5},  # 0.5 < 0.9
            deformed=deformed,
        )
        assert results[0].eligible is False

    def test_exactly_at_budget_ineligible(self):
        """intensity must be strictly greater than budget."""
        bp = _make_bypass(
            stressor_weights={"threat": 1.0},
            latency_budget={"survival": 0.5},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.5},  # 0.5 == 0.5 => not eligible
            deformed=deformed,
        )
        assert results[0].eligible is False


# ── Ineligible: blocked transition ───────────────────────────────────────


class TestIneligibleBlockedTransition:
    def test_inadmissible_transition_ineligible(self):
        bp = _make_bypass(
            source_phase="evaluate",
            target_phase="execute",
            latency_budget={"survival": 0.3},
        )
        # Make evaluate->execute inadmissible (A' <= 0)
        deformed = _make_deformed({"evaluate->execute": (-0.1, 0.5)})
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.8},
            deformed=deformed,
        )
        assert results[0].transition_admissible is False
        assert results[0].eligible is False

    def test_missing_transition_ineligible(self):
        """If the bypass transition is not in the deformed map at all."""
        bp = _make_bypass(
            source_phase="evaluate",
            target_phase="execute",
        )
        deformed = _make_deformed()
        del deformed["evaluate->execute"]
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.8},
            deformed=deformed,
        )
        assert results[0].transition_admissible is False
        assert results[0].eligible is False


# ── select_bypass picks highest saving ───────────────────────────────────


class TestSelectBypass:
    def test_picks_highest_penalty_saving(self):
        e1 = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.3,
        )
        e2 = BypassEligibility(
            name="mania", eligible=True, transition_admissible=True,
            stressor_intensity=0.7, latency_budget=0.4, regime="survival",
            penalty_saving=0.6,
        )
        result = select_bypass([e1, e2])
        assert result is not None
        assert result.name == "mania"

    def test_deterministic_tiebreak_by_name(self):
        e1 = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.5,
        )
        e2 = BypassEligibility(
            name="mania", eligible=True, transition_admissible=True,
            stressor_intensity=0.7, latency_budget=0.4, regime="survival",
            penalty_saving=0.5,
        )
        result = select_bypass([e1, e2])
        assert result is not None
        # Alphabetical tiebreak: "impulse" < "mania"
        assert result.name == "impulse"

    def test_none_eligible_returns_none(self):
        e1 = BypassEligibility(
            name="impulse", eligible=False, transition_admissible=True,
            stressor_intensity=0.3, latency_budget=0.5, regime="survival",
            penalty_saving=0.0,
        )
        result = select_bypass([e1])
        assert result is None

    def test_zero_saving_returns_none(self):
        """penalty_saving must be > 0 to be selected."""
        e1 = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.0,
        )
        result = select_bypass([e1])
        assert result is None

    def test_empty_list_returns_none(self):
        result = select_bypass([])
        assert result is None


# ── Canonical path when no bypass ────────────────────────────────────────


class TestCanonicalPath:
    def test_no_bypass_returns_canonical(self):
        path, event = determine_execution_path(
            bypasses=[], selected_bypass=None,
        )
        assert path == ["evaluate", "generate", "select", "execute", "reflect"]
        assert event is None


# ── Shortened path with bypass ───────────────────────────────────────────


class TestBypassPath:
    def test_impulse_shortens_path(self):
        bp = _make_bypass(
            name="impulse",
            collapsed_path=["evaluate", "execute", "reflect"],
        )
        selected = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.3,
        )
        path, event = determine_execution_path(
            bypasses=[bp], selected_bypass=selected,
        )
        assert path == ["evaluate", "execute", "reflect"]
        assert event is not None
        assert event.name == "impulse"

    def test_bypass_event_fields(self):
        bp = _make_bypass(
            name="impulse",
            collapsed_path=["evaluate", "execute", "reflect"],
        )
        selected = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.3,
        )
        _, event = determine_execution_path(
            bypasses=[bp], selected_bypass=selected,
        )
        assert event.collapsed_path == ["evaluate", "execute", "reflect"]
        assert event.stressor_intensity == 0.8
        assert event.regime == "survival"

    def test_bypass_not_found_returns_canonical(self):
        """If the selected bypass name doesn't match any spec, fall back."""
        selected = BypassEligibility(
            name="nonexistent", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.3,
        )
        path, event = determine_execution_path(
            bypasses=[], selected_bypass=selected,
        )
        assert path == CANONICAL_PHASES
        assert event is None


# ── Skipped phases ───────────────────────────────────────────────────────


class TestSkippedPhases:
    def test_impulse_skips_generate_and_select(self):
        bp = _make_bypass(
            name="impulse",
            collapsed_path=["evaluate", "execute", "reflect"],
        )
        selected = BypassEligibility(
            name="impulse", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.5, regime="survival",
            penalty_saving=0.3,
        )
        _, event = determine_execution_path(
            bypasses=[bp], selected_bypass=selected,
        )
        assert set(event.skipped_phases) == {"generate", "select"}

    def test_rumination_skips_generate_select_execute(self):
        bp = _make_bypass(
            name="rumination",
            source_phase="evaluate",
            target_phase="reflect",
            collapsed_path=["evaluate", "reflect"],
            eligible_regimes=["epistemic"],
        )
        selected = BypassEligibility(
            name="rumination", eligible=True, transition_admissible=True,
            stressor_intensity=0.9, latency_budget=0.4, regime="epistemic",
            penalty_saving=0.5,
        )
        _, event = determine_execution_path(
            bypasses=[bp], selected_bypass=selected,
        )
        assert set(event.skipped_phases) == {"generate", "select", "execute"}

    def test_over_learning_adds_phases(self):
        """Over-learning: reflect->generate (adds phases, doesn't skip)."""
        bp = _make_bypass(
            name="over_learning",
            source_phase="reflect",
            target_phase="generate",
            collapsed_path=["evaluate", "generate", "select", "execute", "reflect", "generate"],
            eligible_regimes=["epistemic", "economic"],
            latency_budget={"epistemic": 0.4},
        )
        selected = BypassEligibility(
            name="over_learning", eligible=True, transition_admissible=True,
            stressor_intensity=0.8, latency_budget=0.4, regime="epistemic",
            penalty_saving=0.4,
        )
        path, event = determine_execution_path(
            bypasses=[bp], selected_bypass=selected,
        )
        # Over-learning keeps all canonical phases + adds "generate" at end
        assert path == ["evaluate", "generate", "select", "execute", "reflect", "generate"]
        # No phases skipped (all canonical phases are present)
        assert event.skipped_phases == []


# ── BypassEvent.to_dict ─────────────────────────────────────────────────


class TestBypassEventToDict:
    def test_to_dict_fields(self):
        event = BypassEvent(
            name="impulse",
            collapsed_path=["evaluate", "execute", "reflect"],
            skipped_phases=["generate", "select"],
            stressor_intensity=0.8123456789,
            regime="survival",
        )
        d = event.to_dict()
        assert d["name"] == "impulse"
        assert d["collapsed_path"] == ["evaluate", "execute", "reflect"]
        assert d["skipped_phases"] == ["generate", "select"]
        assert d["stressor_intensity"] == round(0.8123456789, 6)
        assert d["regime"] == "survival"


# ── Penalty saving computation ───────────────────────────────────────────


class TestPenaltySaving:
    def test_impulse_penalty_saving(self):
        """penalty_saving = canonical_sub_penalty - bypass_penalty."""
        bp = _make_bypass(
            name="impulse",
            source_phase="evaluate",
            target_phase="execute",
            latency_budget={"survival": 0.3},
            stressor_weights={"threat": 1.0},
        )
        deformed = _make_deformed()
        # Impulse replaces: evaluate->generate (0.5), generate->select (0.3), select->execute (0.4)
        # canonical_sub_penalty = 0.5 + 0.3 + 0.4 = 1.2
        # bypass_penalty = evaluate->execute W_prime = 0.2
        # penalty_saving = 1.2 - 0.2 = 1.0
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="survival",
            stressor_map={"threat": 0.8},
            deformed=deformed,
        )
        assert results[0].penalty_saving == pytest.approx(1.0)

    def test_over_learning_penalty_saving_is_intensity_minus_budget(self):
        """For over_learning (no replaced transitions), saving = intensity - budget."""
        bp = _make_bypass(
            name="over_learning",
            source_phase="reflect",
            target_phase="generate",
            collapsed_path=["evaluate", "generate", "select", "execute", "reflect", "generate"],
            eligible_regimes=["epistemic"],
            stressor_weights={"curiosity": 1.0},
            latency_budget={"epistemic": 0.3},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="epistemic",
            stressor_map={"curiosity": 0.7},
            deformed=deformed,
        )
        # intensity=0.7, budget=0.3 => saving = 0.7 - 0.3 = 0.4
        assert results[0].penalty_saving == pytest.approx(0.4)

    def test_over_learning_below_budget_zero_saving(self):
        """When over_learning doesn't exceed budget, saving is 0."""
        bp = _make_bypass(
            name="over_learning",
            source_phase="reflect",
            target_phase="generate",
            collapsed_path=["evaluate", "generate", "select", "execute", "reflect", "generate"],
            eligible_regimes=["epistemic"],
            stressor_weights={"curiosity": 1.0},
            latency_budget={"epistemic": 0.9},
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="epistemic",
            stressor_map={"curiosity": 0.5},
            deformed=deformed,
        )
        assert results[0].penalty_saving == pytest.approx(0.0)

    def test_default_budget_when_regime_missing(self):
        """When active_regime is not in bp.latency_budget, default to 1.0."""
        bp = _make_bypass(
            name="impulse",
            eligible_regimes=["survival", "economic"],
            stressor_weights={"threat": 1.0},
            latency_budget={"survival": 0.3},  # no "economic" key
        )
        deformed = _make_deformed()
        results = check_bypass_eligibility(
            bypasses=[bp],
            active_regime="economic",
            stressor_map={"threat": 0.8},  # 0.8 < 1.0 default
            deformed=deformed,
        )
        assert results[0].latency_budget == pytest.approx(1.0)
        assert results[0].eligible is False  # 0.8 < 1.0


# ── BYPASS_REPLACES structure ────────────────────────────────────────────


class TestBypassReplaces:
    def test_all_five_bypass_types_present(self):
        expected = {"impulse", "rumination", "mania", "guilt", "over_learning"}
        assert set(BYPASS_REPLACES.keys()) == expected

    def test_over_learning_replaces_nothing(self):
        assert BYPASS_REPLACES["over_learning"] == []

    def test_impulse_replaces_three_transitions(self):
        assert len(BYPASS_REPLACES["impulse"]) == 3
