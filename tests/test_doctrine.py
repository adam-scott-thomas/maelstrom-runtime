"""Tests for maelstrom_runtime.doctrine — regret engine & counterfactual archive."""
from __future__ import annotations

import pytest

from maelstrom.doctrine import (
    CounterfactualEntry,
    DoctrineCandidate,
    DoctrineState,
)
from maelstrom.agents import SCORE_DIMS, score_proposal_for_regime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prop(pid: str, phase: str = "evaluate", **score_overrides) -> dict:
    """Build a minimal proposal dict for testing."""
    scores = {d: 0.5 for d in SCORE_DIMS}
    scores.update(score_overrides)
    return {
        "id": pid,
        "cycle": 1,
        "phase": phase,
        "specialist": "test",
        "description": f"test_{pid}",
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# CounterfactualEntry
# ---------------------------------------------------------------------------

class TestCounterfactualEntry:
    def test_to_dict_fields(self):
        p = _prop("p1", phase="generate")
        entry = CounterfactualEntry(
            proposal=p, reason="vetoed", cycle=3, phase="generate", regime_value=0.42,
        )
        d = entry.to_dict()
        assert d["proposal_id"] == "p1"
        assert d["phase"] == "generate"
        assert d["reason"] == "vetoed"
        assert d["cycle"] == 3
        assert d["regime_value"] == 0.42
        assert d["scores"] == p["scores"]


# ---------------------------------------------------------------------------
# DoctrineCandidate
# ---------------------------------------------------------------------------

class TestDoctrineCandidate:
    def test_to_dict_defaults(self):
        dc = DoctrineCandidate(
            cycle=5,
            dtype="sensitivity_adjustment",
            description="test desc",
            proposed_change={"action": "increase_exploration_weight"},
            regret_triggered=True,
        )
        d = dc.to_dict()
        assert d["cycle"] == 5
        assert d["type"] == "sensitivity_adjustment"
        assert d["regret_triggered"] is True
        assert d["promoted"] is False

    def test_promoted_override(self):
        dc = DoctrineCandidate(
            cycle=1, dtype="veto_pattern", description="x",
            proposed_change={}, regret_triggered=False, promoted=True,
        )
        assert dc.to_dict()["promoted"] is True


# ---------------------------------------------------------------------------
# DoctrineState.archive_proposals
# ---------------------------------------------------------------------------

class TestArchiveProposals:
    def test_stores_entries(self):
        ds = DoctrineState()
        p1 = _prop("a1", phase="evaluate")
        p2 = _prop("a2", phase="generate")

        entries = ds.archive_proposals([p1, p2], "not_selected", cycle=1, regime="peacetime")

        assert len(entries) == 2
        assert len(ds.counterfactual_archive) == 2
        assert entries[0].reason == "not_selected"
        assert entries[1].cycle == 1

    def test_archive_uses_score_proposal_for_regime(self):
        ds = DoctrineState()
        p = _prop("sv", phase="select", clarity=1.0, tempo=0.0)

        entries = ds.archive_proposals([p], "bypassed", cycle=2, regime="epistemic")
        # epistemic weights clarity at 0.50 — regime_value should reflect that
        expected_value = score_proposal_for_regime(p, "epistemic")
        assert entries[0].regime_value == pytest.approx(expected_value, abs=1e-6)

    def test_archive_records_phase_from_proposal(self):
        ds = DoctrineState()
        p = _prop("ph", phase="reflect")
        entries = ds.archive_proposals([p], "vetoed", cycle=4, regime="moral")
        assert entries[0].phase == "reflect"

    def test_archive_unknown_phase_default(self):
        ds = DoctrineState()
        p = {"id": "nophase", "description": "x", "scores": {d: 0.5 for d in SCORE_DIMS}}
        entries = ds.archive_proposals([p], "not_selected", cycle=1, regime="peacetime")
        assert entries[0].phase == "unknown"


# ---------------------------------------------------------------------------
# DoctrineState.compute_regret
# ---------------------------------------------------------------------------

class TestComputeRegret:
    def test_regret_positive_when_counterfactual_better(self):
        ds = DoctrineState()
        # Archive a high-value proposal
        high = _prop("high", clarity=0.95, novelty=0.9, defensibility=0.9, tempo=0.9, coherence=0.9)
        ds.archive_proposals([high], "not_selected", cycle=1, regime="peacetime")
        high_value = score_proposal_for_regime(high, "peacetime")

        # Selected something with lower value
        selected_value = 0.3
        regret = ds.compute_regret(selected_value, cycle=1, regime="peacetime")

        assert regret > 0
        assert regret == pytest.approx(high_value - selected_value, abs=1e-6)
        assert len(ds.regret_history) == 1
        assert ds.regret_history[0] == regret

    def test_regret_zero_when_best_chosen(self):
        ds = DoctrineState()
        p = _prop("best", clarity=0.5, novelty=0.5, defensibility=0.5, tempo=0.5, coherence=0.5)
        ds.archive_proposals([p], "not_selected", cycle=2, regime="peacetime")
        cf_value = score_proposal_for_regime(p, "peacetime")

        # Selected value is >= counterfactual value
        regret = ds.compute_regret(cf_value + 0.1, cycle=2, regime="peacetime")
        assert regret == 0.0

    def test_regret_zero_when_no_counterfactuals(self):
        ds = DoctrineState()
        regret = ds.compute_regret(0.5, cycle=99, regime="peacetime")
        assert regret == 0.0
        assert ds.regret_history == [0.0]

    def test_regret_history_accumulates(self):
        ds = DoctrineState()
        # Cycle 1
        p1 = _prop("c1", clarity=0.8)
        ds.archive_proposals([p1], "not_selected", cycle=1, regime="peacetime")
        ds.compute_regret(0.3, cycle=1, regime="peacetime")

        # Cycle 2 — no counterfactuals
        ds.compute_regret(0.5, cycle=2, regime="peacetime")

        assert len(ds.regret_history) == 2


# ---------------------------------------------------------------------------
# DoctrineState.generate_doctrine_candidates
# ---------------------------------------------------------------------------

class TestGenerateDoctrineCandidates:
    def test_high_regret_produces_sensitivity_candidate(self):
        ds = DoctrineState()
        candidates = ds.generate_doctrine_candidates(
            cycle=1, regret=0.25, active_regime="survival",
            bypass_activated=False, veto_events=[],
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.dtype == "sensitivity_adjustment"
        assert c.regret_triggered is True
        assert "survival" in c.description
        assert c.proposed_change["regime"] == "survival"
        assert c.proposed_change["action"] == "increase_exploration_weight"

    def test_no_candidate_when_regret_below_threshold(self):
        ds = DoctrineState()
        candidates = ds.generate_doctrine_candidates(
            cycle=1, regret=0.05, active_regime="peacetime",
            bypass_activated=False, veto_events=[],
        )
        assert len(candidates) == 0

    def test_bypass_produces_regime_bias_candidate(self):
        ds = DoctrineState()
        candidates = ds.generate_doctrine_candidates(
            cycle=2, regret=0.0, active_regime="economic",
            bypass_activated=True, veto_events=[],
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.dtype == "regime_bias"
        assert c.regret_triggered is False
        assert c.proposed_change["action"] == "recalibrate_latency_budget"

    def test_veto_events_produce_veto_pattern_candidate(self):
        ds = DoctrineState()
        veto = [{"type": "identity", "reason": "test"}]
        candidates = ds.generate_doctrine_candidates(
            cycle=3, regret=0.0, active_regime="legal",
            bypass_activated=False, veto_events=veto,
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.dtype == "veto_pattern"
        assert c.proposed_change["veto_count"] == 1
        assert c.proposed_change["action"] == "update_constraint_sensitivity"

    def test_veto_history_records(self):
        ds = DoctrineState()
        veto = [{"type": "coalition", "reason": "quorum_fail"}]
        ds.generate_doctrine_candidates(
            cycle=1, regret=0.0, active_regime="peacetime",
            bypass_activated=False, veto_events=veto,
        )
        assert len(ds.veto_history) == 1
        assert ds.veto_history[0]["type"] == "coalition"

    def test_multiple_conditions_produce_multiple_candidates(self):
        ds = DoctrineState()
        veto = [{"type": "identity", "reason": "blocked"}]
        candidates = ds.generate_doctrine_candidates(
            cycle=5, regret=0.5, active_regime="moral",
            bypass_activated=True, veto_events=veto,
        )
        # All three conditions met: sensitivity + regime_bias + veto_pattern
        assert len(candidates) == 3
        types = {c.dtype for c in candidates}
        assert types == {"sensitivity_adjustment", "regime_bias", "veto_pattern"}

    def test_candidates_persisted_in_state(self):
        ds = DoctrineState()
        ds.generate_doctrine_candidates(
            cycle=1, regret=0.3, active_regime="survival",
            bypass_activated=False, veto_events=[],
        )
        ds.generate_doctrine_candidates(
            cycle=2, regret=0.0, active_regime="survival",
            bypass_activated=True, veto_events=[],
        )
        assert len(ds.doctrine_candidates) == 2


# ---------------------------------------------------------------------------
# DoctrineState.regret_summary
# ---------------------------------------------------------------------------

class TestRegretSummary:
    def test_empty_history(self):
        ds = DoctrineState()
        s = ds.regret_summary()
        assert s == {"mean": 0.0, "max": 0.0, "total_cycles": 0}

    def test_with_data(self):
        ds = DoctrineState()
        ds.regret_history = [0.0, 0.2, 0.0, 0.4]
        s = ds.regret_summary()
        assert s["total_cycles"] == 4
        assert s["cycles_with_regret"] == 2
        assert s["max"] == 0.4
        assert s["mean"] == pytest.approx(0.15, abs=1e-6)
