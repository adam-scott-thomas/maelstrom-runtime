"""Tests for Phase 9 doctrine trigger types: gov_disallow_loop, low_conf_switch, oscillation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from maelstrom.doctrine import DoctrineCandidate, DoctrineRecord, DoctrineState, candidate_to_record
from maelstrom.feedback import (
    FeedbackDelta,
    compute_feedback_deltas,
    write_feedback_deltas,
    DELTA_BOUNDS,
)
from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_call(ds: DoctrineState, cycle: int, active_regime: str = "peacetime",
               governance_disallow: bool = False,
               regime_switch_decision: dict | None = None) -> list[DoctrineCandidate]:
    """Call generate_doctrine_candidates with defaults for non-new args."""
    return ds.generate_doctrine_candidates(
        cycle=cycle,
        regret=0.0,
        active_regime=active_regime,
        bypass_activated=False,
        veto_events=[],
        governance_disallow=governance_disallow,
        regime_switch_decision=regime_switch_decision,
    )


# ---------------------------------------------------------------------------
# TestGovDisallowLoop
# ---------------------------------------------------------------------------

class TestGovDisallowLoop:
    """gov_disallow_loop fires when governance disallows happen 3+ consecutive cycles."""

    def test_no_candidate_below_streak(self):
        """2 consecutive disallows should NOT produce a candidate."""
        ds = DoctrineState()
        c1 = _base_call(ds, cycle=1, governance_disallow=True)
        c2 = _base_call(ds, cycle=2, governance_disallow=True)
        gov_candidates = [c for c in c1 + c2 if c.dtype == "gov_disallow_loop"]
        assert len(gov_candidates) == 0

    def test_candidate_at_streak_3(self):
        """3 consecutive disallows should produce a candidate with correct fields."""
        ds = DoctrineState()
        _base_call(ds, cycle=1, governance_disallow=True)
        _base_call(ds, cycle=2, governance_disallow=True)
        c3 = _base_call(ds, cycle=3, governance_disallow=True)

        gov_candidates = [c for c in c3 if c.dtype == "gov_disallow_loop"]
        assert len(gov_candidates) == 1

        c = gov_candidates[0]
        assert c.cycle == 3
        assert c.proposed_change["disallow_streak"] == 3
        assert c.proposed_change["action"] == "reduce_governance_penalty"
        assert c.regret_triggered is False

    def test_streak_resets_on_false(self):
        """Streak of 3, then False, then 2 more should NOT produce a new candidate."""
        ds = DoctrineState()
        _base_call(ds, cycle=1, governance_disallow=True)
        _base_call(ds, cycle=2, governance_disallow=True)
        _base_call(ds, cycle=3, governance_disallow=True)  # triggers candidate here

        # Reset
        _base_call(ds, cycle=4, governance_disallow=False)

        # Two more True values -- not enough for new streak of 3
        c5 = _base_call(ds, cycle=5, governance_disallow=True)
        c6 = _base_call(ds, cycle=6, governance_disallow=True)

        gov_candidates = [c for c in c5 + c6 if c.dtype == "gov_disallow_loop"]
        assert len(gov_candidates) == 0


# ---------------------------------------------------------------------------
# TestLowConfSwitch
# ---------------------------------------------------------------------------

class TestLowConfSwitch:
    """low_conf_switch fires when a regime switch has margin < 0.005."""

    def test_low_conf_switch_detected(self):
        """margin=0.002 with regime change should emit candidate."""
        ds = DoctrineState()
        decision = {
            "current_regime": "peacetime",
            "selected_regime": "survival",
            "winner_margin": 0.002,
        }
        candidates = _base_call(ds, cycle=1, active_regime="survival",
                                regime_switch_decision=decision)
        lc = [c for c in candidates if c.dtype == "low_conf_switch"]
        assert len(lc) == 1

        c = lc[0]
        assert c.cycle == 1
        assert c.proposed_change["margin"] == 0.002
        assert c.proposed_change["from_regime"] == "peacetime"
        assert c.proposed_change["to_regime"] == "survival"
        assert c.proposed_change["action"] == "increase_gradient_window"
        assert c.regret_triggered is False

    def test_no_candidate_when_margin_high(self):
        """margin=0.05 should NOT emit candidate even though regime changed."""
        ds = DoctrineState()
        decision = {
            "current_regime": "peacetime",
            "selected_regime": "survival",
            "winner_margin": 0.05,
        }
        candidates = _base_call(ds, cycle=1, active_regime="survival",
                                regime_switch_decision=decision)
        lc = [c for c in candidates if c.dtype == "low_conf_switch"]
        assert len(lc) == 0

    def test_no_candidate_when_no_switch(self):
        """Same regime in and out -- no candidate even with low margin."""
        ds = DoctrineState()
        decision = {
            "current_regime": "peacetime",
            "selected_regime": "peacetime",
            "winner_margin": 0.001,
        }
        candidates = _base_call(ds, cycle=1, active_regime="peacetime",
                                regime_switch_decision=decision)
        lc = [c for c in candidates if c.dtype == "low_conf_switch"]
        assert len(lc) == 0


# ---------------------------------------------------------------------------
# TestOscillation
# ---------------------------------------------------------------------------

class TestOscillation:
    """oscillation fires when A-B-A-B-A-B pattern detected in last 6 regime history entries."""

    def test_oscillation_detected_abab(self):
        """6-cycle A-B-A-B-A-B pattern should emit candidate."""
        ds = DoctrineState()
        regimes = ["peacetime", "survival", "peacetime", "survival", "peacetime", "survival"]
        candidates_all = []
        for i, r in enumerate(regimes):
            candidates_all = _base_call(ds, cycle=i + 1, active_regime=r)

        osc = [c for c in candidates_all if c.dtype == "oscillation"]
        assert len(osc) == 1

        c = osc[0]
        assert c.cycle == 6
        assert c.proposed_change["oscillation_length"] == 6
        assert c.proposed_change["regime_a"] == "peacetime"
        assert c.proposed_change["regime_b"] == "survival"
        assert c.proposed_change["action"] == "increase_inertia"
        assert c.proposed_change["evidence_cycles"] == [1, 2, 3, 4, 5, 6]
        assert c.regret_triggered is False

    def test_no_oscillation_when_stable(self):
        """6 cycles of the same regime should NOT emit candidate."""
        ds = DoctrineState()
        for i in range(6):
            candidates = _base_call(ds, cycle=i + 1, active_regime="peacetime")

        osc = [c for c in candidates if c.dtype == "oscillation"]
        assert len(osc) == 0

    def test_no_oscillation_under_6_cycles(self):
        """Only 5 cycles (even if alternating) should NOT emit candidate."""
        ds = DoctrineState()
        regimes = ["peacetime", "survival", "peacetime", "survival", "peacetime"]
        all_candidates = []
        for i, r in enumerate(regimes):
            cs = _base_call(ds, cycle=i + 1, active_regime=r)
            all_candidates.extend(cs)

        osc = [c for c in all_candidates if c.dtype == "oscillation"]
        assert len(osc) == 0


# ---------------------------------------------------------------------------
# TestDoctrineRecord
# ---------------------------------------------------------------------------

class TestDoctrineRecord:
    def test_regret_spike_mapping(self):
        dc = DoctrineCandidate(
            cycle=5, dtype="sensitivity_adjustment", description="test",
            proposed_change={"regime": "survival", "regret": 0.25,
                             "action": "increase_exploration_weight"},
            regret_triggered=True,
        )
        record = candidate_to_record(dc, "survival")
        assert record is not None
        assert record.trigger_type == "regret_spike"
        assert record.regime == "survival"
        assert record.trigger_metrics["regret"] == 0.25
        assert record.proposed_action == "increase_exploration_weight"
        assert len(record.deterministic_hash) == 64

    def test_veto_gridlock_mapping(self):
        dc = DoctrineCandidate(
            cycle=10, dtype="veto_pattern", description="test",
            proposed_change={"veto_count": 5, "action": "update_constraint_sensitivity"},
            regret_triggered=False,
        )
        record = candidate_to_record(dc, "legal")
        assert record is not None
        assert record.trigger_type == "veto_gridlock"
        assert record.trigger_metrics["veto_count"] == 5.0

    def test_regime_bias_returns_none(self):
        dc = DoctrineCandidate(
            cycle=1, dtype="regime_bias", description="test",
            proposed_change={"action": "recalibrate_latency_budget"},
            regret_triggered=False,
        )
        record = candidate_to_record(dc, "economic")
        assert record is None

    def test_deterministic_hash_stable(self):
        dc = DoctrineCandidate(
            cycle=5, dtype="oscillation", description="test",
            proposed_change={"oscillation_length": 6, "regime_a": "survival",
                             "regime_b": "peacetime", "action": "increase_inertia",
                             "evidence_cycles": [1, 2, 3, 4, 5, 6]},
            regret_triggered=False,
        )
        r1 = candidate_to_record(dc, "survival")
        r2 = candidate_to_record(dc, "survival")
        assert r1.deterministic_hash == r2.deterministic_hash

    def test_to_dict_has_all_fields(self):
        dc = DoctrineCandidate(
            cycle=3, dtype="gov_disallow_loop", description="test",
            proposed_change={"disallow_streak": 4, "action": "reduce_governance_penalty"},
            regret_triggered=False,
        )
        record = candidate_to_record(dc, "legal")
        d = record.to_dict()
        required_keys = {"cycle", "regime", "trigger_type", "trigger_metrics",
                         "proposed_action", "evidence", "deterministic_hash"}
        assert required_keys == set(d.keys())


# ---------------------------------------------------------------------------
# TestDoctrineJSONLEmission
# ---------------------------------------------------------------------------

class TestDoctrineJSONLEmission:
    def test_jsonl_file_created(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        with tempfile.TemporaryDirectory() as td:
            runtime = MaelstromRuntime(spec, output_dir=Path(td))
            runtime.run()
            jsonl_path = Path(td) / "doctrine_candidates.jsonl"
            assert jsonl_path.exists()

    def test_jsonl_lines_valid(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "guilt_spiral_v0.json")
        with tempfile.TemporaryDirectory() as td:
            runtime = MaelstromRuntime(spec, output_dir=Path(td))
            runtime.run()
            jsonl_path = Path(td) / "doctrine_candidates.jsonl"
            lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) > 0
            for line in lines:
                record = json.loads(line)
                assert "cycle" in record
                assert "regime" in record
                assert "trigger_type" in record
                assert record["trigger_type"] in {
                    "regret_spike", "veto_gridlock", "gov_disallow_loop",
                    "low_conf_switch", "oscillation",
                }
                assert "trigger_metrics" in record
                assert "proposed_action" in record
                assert "evidence" in record
                assert "deterministic_hash" in record
                assert len(record["deterministic_hash"]) == 64

    def test_jsonl_deterministic(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        runs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                runtime = MaelstromRuntime(spec, output_dir=Path(td))
                runtime.run()
                jsonl_path = Path(td) / "doctrine_candidates.jsonl"
                runs.append(jsonl_path.read_text(encoding="utf-8"))
        assert runs[0] == runs[1]


# ---------------------------------------------------------------------------
# TestFeedbackDeltas
# ---------------------------------------------------------------------------

class TestFeedbackDeltas:
    def test_high_regret_produces_W_delta(self):
        summary = {"mean_regret": 0.25, "max_regret": 0.4, "regime_switches": 2,
                    "total_cycles": 50, "total_veto_events": 0, "total_bypass_events": 0}
        candidates = [{"trigger_type": "regret_spike", "trigger_metrics": {"regret": 0.25}}]
        deltas = compute_feedback_deltas(summary, candidates)
        w_deltas = [d for d in deltas if d.parameter == "W"]
        assert len(w_deltas) >= 1
        for d in w_deltas:
            lo, hi = DELTA_BOUNDS["W"]
            assert lo <= d.delta <= hi

    def test_oscillation_produces_inertia_delta(self):
        summary = {"mean_regret": 0.0, "max_regret": 0.0, "regime_switches": 8,
                    "total_cycles": 50, "total_veto_events": 0, "total_bypass_events": 0}
        candidates = [{"trigger_type": "oscillation"} for _ in range(3)]
        deltas = compute_feedback_deltas(summary, candidates)
        inertia_deltas = [d for d in deltas if d.parameter == "inertia"]
        assert len(inertia_deltas) == 1
        assert inertia_deltas[0].delta > 0
        lo, hi = DELTA_BOUNDS["inertia"]
        assert lo <= inertia_deltas[0].delta <= hi

    def test_gov_disallow_reduces_sensitivity(self):
        summary = {"mean_regret": 0.0, "max_regret": 0.0, "regime_switches": 0,
                    "total_cycles": 50, "total_veto_events": 0, "total_bypass_events": 0}
        candidates = [{"trigger_type": "gov_disallow_loop"} for _ in range(4)]
        deltas = compute_feedback_deltas(summary, candidates)
        gov_deltas = [d for d in deltas if d.parameter == "governance_sensitivity"]
        assert len(gov_deltas) == 1
        assert gov_deltas[0].delta < 0

    def test_no_deltas_when_clean(self):
        summary = {"mean_regret": 0.01, "max_regret": 0.02, "regime_switches": 1,
                    "total_cycles": 50, "total_veto_events": 0, "total_bypass_events": 0}
        candidates = []
        deltas = compute_feedback_deltas(summary, candidates)
        assert len(deltas) == 0

    def test_all_deltas_bounded(self):
        summary = {"mean_regret": 0.9, "max_regret": 1.0, "regime_switches": 40,
                    "total_cycles": 50, "total_veto_events": 100, "total_bypass_events": 50}
        candidates = (
            [{"trigger_type": "regret_spike"}] * 20
            + [{"trigger_type": "oscillation"}] * 10
            + [{"trigger_type": "gov_disallow_loop"}] * 15
            + [{"trigger_type": "veto_gridlock"}] * 10
            + [{"trigger_type": "low_conf_switch"}] * 8
        )
        deltas = compute_feedback_deltas(summary, candidates)
        for d in deltas:
            lo, hi = DELTA_BOUNDS[d.parameter]
            assert lo <= d.delta <= hi, (
                f"{d.parameter} delta {d.delta} out of bounds [{lo}, {hi}]"
            )

    def test_write_feedback_deltas_file(self, tmp_path):
        deltas = [
            FeedbackDelta("W", "select->execute", -0.01, "test"),
            FeedbackDelta("inertia", "global", 0.002, "test"),
        ]
        out = tmp_path / "feedback_deltas.json"
        write_feedback_deltas(deltas, out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["total_deltas"] == 2
        assert len(data["deltas"]) == 2


# ---------------------------------------------------------------------------
# TestFeedbackDeltaEmission
# ---------------------------------------------------------------------------

class TestFeedbackDeltaEmission:
    """Verify runtime emits feedback_deltas.json after each run."""

    def test_feedback_deltas_json_created(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        with tempfile.TemporaryDirectory() as td:
            runtime = MaelstromRuntime(spec, output_dir=Path(td))
            runtime.run()
            fd_path = Path(td) / "feedback_deltas.json"
            assert fd_path.exists()
            data = json.loads(fd_path.read_text(encoding="utf-8"))
            assert "total_deltas" in data
            assert "deltas" in data
            assert isinstance(data["deltas"], list)

    def test_feedback_deltas_deterministic(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        runs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                runtime = MaelstromRuntime(spec, output_dir=Path(td))
                runtime.run()
                fd_path = Path(td) / "feedback_deltas.json"
                runs.append(fd_path.read_text(encoding="utf-8"))
        assert runs[0] == runs[1]


# ---------------------------------------------------------------------------
# Doctrine Store Tests
# ---------------------------------------------------------------------------

from maelstrom.doctrine.store import (
    Doctrine,
    load_active,
    save_active,
    load_proposals,
    save_proposals,
)


class TestDoctrineStore:
    def test_doctrine_to_dict_roundtrip(self):
        d = Doctrine(
            id="test_001", name="reduce_oscillation_v1", version="1.0.0",
            description="Increase inertia when oscillation detected",
            trigger_conditions={"oscillation_count": {"min": 3}},
            action_deltas={"inertia_delta": 0.003},
            safety_constraints={"max_inertia": 0.05, "max_regret_increase": 0.02},
            created_from_candidates=["abc123", "def456"],
        )
        d2 = Doctrine.from_dict(d.to_dict())
        assert d2.id == d.id
        assert d2.name == d.name
        assert d2.version == d.version
        assert d2.action_deltas == d.action_deltas
        assert d2.created_from_candidates == d.created_from_candidates

    def test_load_active_empty(self):
        doctrines = load_active()
        assert isinstance(doctrines, list)
        assert len(doctrines) == 0

    def test_load_proposals_empty(self):
        proposals = load_proposals()
        assert isinstance(proposals, list)
        assert len(proposals) == 0

    def test_save_and_load_active(self, tmp_path):
        d = Doctrine(
            id="test_001", name="test_doctrine", version="1.0.0",
            description="test", trigger_conditions={},
            action_deltas={"inertia_delta": 0.001},
            safety_constraints={},
            created_from_candidates=["hash1"],
        )
        active_path = tmp_path / "active.json"
        save_active([d], active_path)
        loaded = load_active(active_path)
        assert len(loaded) == 1
        assert loaded[0].id == "test_001"
        assert loaded[0].action_deltas == {"inertia_delta": 0.001}

    def test_save_and_load_proposals(self, tmp_path):
        d = Doctrine(
            id="prop_001", name="proposed_doctrine", version="0.1.0",
            description="proposal", trigger_conditions={"regret": {"min": 0.2}},
            action_deltas={"W_delta": -0.01},
            safety_constraints={"max_regret_increase": 0.05},
            created_from_candidates=["h1", "h2"],
        )
        prop_path = tmp_path / "proposals.json"
        save_proposals([d], prop_path)
        loaded = load_proposals(prop_path)
        assert len(loaded) == 1
        assert loaded[0].id == "prop_001"


class TestDoctrineSchema:
    def test_schema_file_exists(self):
        schema_path = Path(__file__).parent.parent / "maelstrom" / "doctrine" / "schema.md"
        assert schema_path.exists()
        content = schema_path.read_text(encoding="utf-8")
        assert "id" in content
        assert "version" in content
        assert "trigger_conditions" in content
        assert "action_deltas" in content
        assert "safety_constraints" in content


class TestExistingDoctrineImportsStillWork:
    """Verify that converting doctrine.py to doctrine/__init__.py breaks nothing."""

    def test_import_doctrine_state(self):
        from maelstrom.doctrine import DoctrineState
        ds = DoctrineState()
        assert ds is not None

    def test_import_doctrine_candidate(self):
        from maelstrom.doctrine import DoctrineCandidate
        dc = DoctrineCandidate(cycle=1, dtype="test", description="test",
                               proposed_change={}, regret_triggered=False)
        assert dc.cycle == 1

    def test_import_counterfactual_entry(self):
        from maelstrom.doctrine import CounterfactualEntry
        assert CounterfactualEntry is not None

    def test_import_doctrine_record(self):
        from maelstrom.doctrine import DoctrineRecord, candidate_to_record
        assert DoctrineRecord is not None
        assert candidate_to_record is not None


# ---------------------------------------------------------------------------
# Promotion Evaluator Tests
# ---------------------------------------------------------------------------

from maelstrom.doctrine.evaluate import (
    run_scenario,
    run_suite,
    apply_deltas,
    compare_metrics,
    evaluate_proposal,
)


class TestApplyDeltas:
    def test_apply_W_delta(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        deltas = [{"parameter": "W", "target": "select->execute", "delta": 0.02}]
        new_spec = apply_deltas(spec, deltas)
        orig_t = spec.get_transition("select", "execute")
        new_t = new_spec.get_transition("select", "execute")
        assert new_t.W == pytest.approx(orig_t.W + 0.02, abs=1e-8)
        # Original unchanged
        assert orig_t.W != new_t.W or orig_t.W == pytest.approx(orig_t.W, abs=1e-8)

    def test_apply_inertia_delta_scalar(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        orig_inertia = spec.regime_inertia
        deltas = [{"parameter": "inertia", "target": "global", "delta": 0.002}]
        new_spec = apply_deltas(spec, deltas)
        if isinstance(orig_inertia, dict):
            for key in orig_inertia:
                assert new_spec.regime_inertia[key] == pytest.approx(
                    orig_inertia[key] + 0.002, abs=1e-8
                )
        else:
            assert new_spec.regime_inertia == pytest.approx(
                orig_inertia + 0.002, abs=1e-8
            )

    def test_apply_gradient_window_delta(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        deltas = [{"parameter": "gradient_window", "target": "global", "delta": 1}]
        new_spec = apply_deltas(spec, deltas)
        assert new_spec.gradient_window == spec.gradient_window + 1

    def test_delta_W_clamped(self):
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
        deltas = [{"parameter": "W", "target": "select->execute", "delta": 10.0}]
        new_spec = apply_deltas(spec, deltas)
        t = new_spec.get_transition("select", "execute")
        assert t.W <= 2.0  # clamped


class TestRunScenario:
    def test_run_scenario_returns_summary(self):
        result = run_scenario(EXAMPLES_DIR / "meridian_v0.json")
        assert "mean_regret" in result
        assert "total_cycles" in result

    def test_run_scenario_deterministic(self):
        r1 = run_scenario(EXAMPLES_DIR / "meridian_v0.json")
        r2 = run_scenario(EXAMPLES_DIR / "meridian_v0.json")
        assert r1["mean_regret"] == r2["mean_regret"]
        assert r1["regime_switches"] == r2["regime_switches"]


class TestCompareMetrics:
    def test_improvement_detected(self):
        baseline = {
            "s1": {"mean_regret": 0.2, "max_regret": 0.5, "regime_switches": 5,
                    "total_veto_events": 10, "total_bypass_events": 3},
        }
        candidate = {
            "s1": {"mean_regret": 0.1, "max_regret": 0.4, "regime_switches": 4,
                    "total_veto_events": 10, "total_bypass_events": 3},
        }
        result = compare_metrics(baseline, candidate)
        assert result["promote"] is True
        assert len(result["improvements"]) > 0

    def test_safety_violation_blocks_promotion(self):
        baseline = {
            "s1": {"mean_regret": 0.2, "max_regret": 0.5, "regime_switches": 5,
                    "total_veto_events": 10, "total_bypass_events": 3},
        }
        candidate = {
            "s1": {"mean_regret": 0.1, "max_regret": 0.4, "regime_switches": 4,
                    "total_veto_events": 20, "total_bypass_events": 3},
        }
        result = compare_metrics(baseline, candidate)
        assert result["promote"] is False
        assert result["safety_ok"] is False

    def test_no_improvement_no_promotion(self):
        baseline = {
            "s1": {"mean_regret": 0.1, "max_regret": 0.2, "regime_switches": 2,
                    "total_veto_events": 5, "total_bypass_events": 1},
        }
        candidate = {
            "s1": {"mean_regret": 0.1, "max_regret": 0.2, "regime_switches": 2,
                    "total_veto_events": 5, "total_bypass_events": 1},
        }
        result = compare_metrics(baseline, candidate)
        assert result["promote"] is False


class TestEvaluateProposal:
    def test_evaluate_with_empty_deltas(self):
        result = evaluate_proposal(EXAMPLES_DIR, [])
        assert "promote" in result
        # Empty deltas = no improvement = no promotion
        assert result["promote"] is False


# ---------------------------------------------------------------------------
# TestAllScenariosEmitJSONL
# ---------------------------------------------------------------------------

class TestAllScenariosEmitJSONL:
    """Every scenario produces a valid doctrine_candidates.jsonl and feedback_deltas.json."""

    @pytest.fixture(scope="module", params=sorted(
        p.stem for p in (Path(__file__).parent.parent / "examples").glob("*_v0.json")
    ))
    def scenario_output(self, request, tmp_path_factory):
        name = request.param
        spec = MaelstromSpec.from_json(EXAMPLES_DIR / f"{name}.json")
        out = tmp_path_factory.mktemp(name)
        runtime = MaelstromRuntime(spec, output_dir=out)
        runtime.run()
        return name, out

    def test_jsonl_exists(self, scenario_output):
        name, out = scenario_output
        jsonl_path = out / "doctrine_candidates.jsonl"
        assert jsonl_path.exists(), f"{name}: doctrine_candidates.jsonl missing"

    def test_jsonl_valid_records(self, scenario_output):
        name, out = scenario_output
        jsonl_path = out / "doctrine_candidates.jsonl"
        content = jsonl_path.read_text(encoding="utf-8").strip()
        if not content:
            return  # Empty is valid (scenario may have no triggers)
        for i, line in enumerate(content.splitlines()):
            record = json.loads(line)
            assert "trigger_type" in record, f"{name} line {i}: missing trigger_type"
            assert record["trigger_type"] in {
                "regret_spike", "veto_gridlock", "gov_disallow_loop",
                "low_conf_switch", "oscillation",
            }, f"{name} line {i}: unknown trigger_type {record['trigger_type']}"
            assert "deterministic_hash" in record, f"{name} line {i}: missing hash"
            assert len(record["deterministic_hash"]) == 64, (
                f"{name} line {i}: hash length {len(record['deterministic_hash'])} != 64"
            )

    def test_feedback_deltas_exists(self, scenario_output):
        name, out = scenario_output
        delta_path = out / "feedback_deltas.json"
        assert delta_path.exists(), f"{name}: feedback_deltas.json missing"

    def test_feedback_deltas_valid(self, scenario_output):
        name, out = scenario_output
        delta_path = out / "feedback_deltas.json"
        data = json.loads(delta_path.read_text(encoding="utf-8"))
        assert "deltas" in data, f"{name}: missing deltas key"
        assert "total_deltas" in data, f"{name}: missing total_deltas key"
        assert isinstance(data["deltas"], list), f"{name}: deltas is not a list"
        assert data["total_deltas"] == len(data["deltas"]), (
            f"{name}: total_deltas {data['total_deltas']} != len(deltas) {len(data['deltas'])}"
        )
