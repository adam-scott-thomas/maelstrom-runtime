"""Tests for the agents module — 5 specialist proposal generators."""
from __future__ import annotations

import pytest

from maelstrom.agents import (
    PHASE_SPECIALIST,
    REGIME_SCORE_WEIGHTS,
    SCORE_DIMS,
    generate_all_proposals,
    score_proposal_for_regime,
    select_best_proposal,
)
from maelstrom.utils import DeterministicRNG


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rng() -> DeterministicRNG:
    return DeterministicRNG(seed=42)


@pytest.fixture
def stressor_map() -> dict[str, float]:
    return {
        "time_pressure": 0.5,
        "ambiguity": 0.3,
        "threat_level": 0.6,
        "opportunity_pressure": 0.4,
        "novelty_pressure": 0.2,
        "competition": 0.5,
        "moral_weight": 0.7,
        "institutional_inertia": 0.3,
        "resource_decay": 0.4,
        "failure_count": 0.2,
    }


@pytest.fixture
def all_proposals(stressor_map: dict, rng: DeterministicRNG) -> dict[str, list[dict]]:
    return generate_all_proposals(cycle=1, stressor_map=stressor_map, rng=rng)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_score_dims_count(self):
        assert len(SCORE_DIMS) == 5

    def test_score_dims_names(self):
        assert SCORE_DIMS == ["clarity", "novelty", "defensibility", "tempo", "coherence"]

    def test_phase_specialist_count(self):
        assert len(PHASE_SPECIALIST) == 5

    def test_phase_specialist_phases(self):
        assert set(PHASE_SPECIALIST.keys()) == {
            "evaluate", "generate", "select", "execute", "reflect",
        }

    def test_regime_weights_sum_to_one(self):
        for regime, weights in REGIME_SCORE_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-9, f"{regime} weights sum to {total}"


# ---------------------------------------------------------------------------
# Proposal generation — structure
# ---------------------------------------------------------------------------

class TestAllPhasesProduceProposals:
    def test_all_phases_present(self, all_proposals: dict):
        for phase in PHASE_SPECIALIST:
            assert phase in all_proposals, f"missing phase: {phase}"

    def test_three_proposals_per_phase(self, all_proposals: dict):
        for phase, proposals in all_proposals.items():
            assert len(proposals) == 3, f"{phase} has {len(proposals)} proposals, expected 3"

    def test_total_proposals(self, all_proposals: dict):
        total = sum(len(ps) for ps in all_proposals.values())
        assert total == 15


class TestProposalFields:
    REQUIRED_FIELDS = {"id", "cycle", "phase", "specialist", "description", "scores"}

    def test_required_fields_present(self, all_proposals: dict):
        for phase, proposals in all_proposals.items():
            for p in proposals:
                missing = self.REQUIRED_FIELDS - set(p.keys())
                assert not missing, f"proposal {p.get('id', '?')} missing fields: {missing}"

    def test_id_format(self, all_proposals: dict):
        for phase, proposals in all_proposals.items():
            for p in proposals:
                pid = p["id"]
                assert pid.startswith("c001_"), f"bad id prefix: {pid}"
                assert phase in pid, f"phase not in id: {pid}"

    def test_cycle_value(self, all_proposals: dict):
        for proposals in all_proposals.values():
            for p in proposals:
                assert p["cycle"] == 1

    def test_specialist_matches_phase(self, all_proposals: dict):
        for phase, proposals in all_proposals.items():
            expected_specialist = PHASE_SPECIALIST[phase]
            for p in proposals:
                assert p["specialist"] == expected_specialist

    def test_description_is_nonempty_string(self, all_proposals: dict):
        for proposals in all_proposals.values():
            for p in proposals:
                assert isinstance(p["description"], str)
                assert len(p["description"]) > 0


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------

class TestScoresInRange:
    def test_all_scores_between_0_and_1(self, all_proposals: dict):
        for phase, proposals in all_proposals.items():
            for p in proposals:
                for dim in SCORE_DIMS:
                    val = p["scores"][dim]
                    assert 0.0 <= val <= 1.0, (
                        f"{p['id']}.{dim} = {val} out of range"
                    )

    def test_all_score_dims_present(self, all_proposals: dict):
        for proposals in all_proposals.values():
            for p in proposals:
                assert set(p["scores"].keys()) == set(SCORE_DIMS)

    def test_scores_are_floats(self, all_proposals: dict):
        for proposals in all_proposals.values():
            for p in proposals:
                for dim, val in p["scores"].items():
                    assert isinstance(val, float), f"{p['id']}.{dim} is {type(val)}"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_same_proposals(self, stressor_map: dict):
        rng1 = DeterministicRNG(seed=99)
        rng2 = DeterministicRNG(seed=99)
        p1 = generate_all_proposals(cycle=5, stressor_map=stressor_map, rng=rng1)
        p2 = generate_all_proposals(cycle=5, stressor_map=stressor_map, rng=rng2)
        for phase in PHASE_SPECIALIST:
            for i in range(3):
                assert p1[phase][i]["id"] == p2[phase][i]["id"]
                assert p1[phase][i]["scores"] == p2[phase][i]["scores"]

    def test_different_seed_different_proposals(self, stressor_map: dict):
        rng1 = DeterministicRNG(seed=1)
        rng2 = DeterministicRNG(seed=2)
        p1 = generate_all_proposals(cycle=1, stressor_map=stressor_map, rng=rng1)
        p2 = generate_all_proposals(cycle=1, stressor_map=stressor_map, rng=rng2)
        # At least one score should differ somewhere
        any_diff = False
        for phase in PHASE_SPECIALIST:
            for i in range(3):
                if p1[phase][i]["scores"] != p2[phase][i]["scores"]:
                    any_diff = True
                    break
        assert any_diff, "different seeds produced identical proposals"


# ---------------------------------------------------------------------------
# Regime-weighted scoring
# ---------------------------------------------------------------------------

class TestRegimeScoring:
    def test_survival_prefers_tempo(self, all_proposals: dict):
        """In survival regime, high-tempo proposals should score well."""
        execute_proposals = all_proposals["execute"]
        # Vance Calderon's proposals have high tempo
        scores = [score_proposal_for_regime(p, "survival") for p in execute_proposals]
        # The decisive_action or rapid_deployment (highest tempo) should score highest
        best_idx = scores.index(max(scores))
        best = execute_proposals[best_idx]
        assert best["scores"]["tempo"] >= 0.7, (
            f"survival best has tempo {best['scores']['tempo']}, expected >= 0.7"
        )

    def test_epistemic_prefers_clarity(self, all_proposals: dict):
        """In epistemic regime, high-clarity proposals should score well."""
        eval_proposals = all_proposals["evaluate"]
        scores = [score_proposal_for_regime(p, "epistemic") for p in eval_proposals]
        best_idx = scores.index(max(scores))
        best = eval_proposals[best_idx]
        assert best["scores"]["clarity"] >= 0.7, (
            f"epistemic best has clarity {best['scores']['clarity']}, expected >= 0.7"
        )

    def test_score_is_weighted_sum(self, all_proposals: dict):
        """Score should equal the weighted sum of dimension scores."""
        p = all_proposals["evaluate"][0]
        regime = "peacetime"
        expected = sum(
            REGIME_SCORE_WEIGHTS[regime][d] * p["scores"][d]
            for d in SCORE_DIMS
        )
        actual = score_proposal_for_regime(p, regime)
        assert abs(actual - expected) < 1e-9

    def test_unknown_regime_uses_peacetime(self, all_proposals: dict):
        p = all_proposals["evaluate"][0]
        unknown_score = score_proposal_for_regime(p, "nonexistent_regime")
        peacetime_score = score_proposal_for_regime(p, "peacetime")
        assert abs(unknown_score - peacetime_score) < 1e-9


# ---------------------------------------------------------------------------
# select_best_proposal
# ---------------------------------------------------------------------------

class TestSelectBestProposal:
    def test_returns_none_for_empty(self):
        assert select_best_proposal([], "survival") is None

    def test_returns_best_for_regime(self, all_proposals: dict):
        all_flat = [p for ps in all_proposals.values() for p in ps]
        best = select_best_proposal(all_flat, "survival")
        assert best is not None
        best_score = score_proposal_for_regime(best, "survival")
        for p in all_flat:
            s = score_proposal_for_regime(p, "survival")
            assert s <= best_score + 1e-12

    def test_deterministic_tiebreak(self, all_proposals: dict):
        """Selecting from same list twice returns same proposal."""
        all_flat = [p for ps in all_proposals.values() for p in ps]
        best1 = select_best_proposal(all_flat, "legal")
        best2 = select_best_proposal(all_flat, "legal")
        assert best1 is not None
        assert best1["id"] == best2["id"]


# ---------------------------------------------------------------------------
# Regret-previous integration
# ---------------------------------------------------------------------------

class TestRegretPrevious:
    def test_regret_affects_reflect_proposals(self, stressor_map: dict):
        rng1 = DeterministicRNG(seed=50)
        rng2 = DeterministicRNG(seed=50)
        p_no_regret = generate_all_proposals(
            cycle=1, stressor_map=stressor_map, rng=rng1, regret_prev=0.0,
        )
        p_high_regret = generate_all_proposals(
            cycle=1, stressor_map=stressor_map, rng=rng2, regret_prev=0.9,
        )
        # lesson_extraction (index 2) should differ in novelty
        le_no = p_no_regret["reflect"][2]["scores"]["novelty"]
        le_hi = p_high_regret["reflect"][2]["scores"]["novelty"]
        assert le_hi > le_no, "high regret should increase novelty in lesson_extraction"

    def test_non_reflect_phases_unaffected_by_regret(self, stressor_map: dict):
        rng1 = DeterministicRNG(seed=50)
        rng2 = DeterministicRNG(seed=50)
        p1 = generate_all_proposals(
            cycle=1, stressor_map=stressor_map, rng=rng1, regret_prev=0.0,
        )
        p2 = generate_all_proposals(
            cycle=1, stressor_map=stressor_map, rng=rng2, regret_prev=0.9,
        )
        for phase in ["evaluate", "generate", "select", "execute"]:
            for i in range(3):
                assert p1[phase][i]["scores"] == p2[phase][i]["scores"], (
                    f"{phase}[{i}] changed with regret"
                )
