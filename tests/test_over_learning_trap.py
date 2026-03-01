"""Over-Learning Trap V0 scenario -- sustained ambiguity forces R->G loops every cycle.

The Over-Learning Trap scenario models a system under sustained high ambiguity
(0.78) and novelty_pressure (0.72) with moderate failure_count (0.50).  The
over_learning bypass has a lowered epistemic budget (0.40) so the weighted
stressor signal (0.4*0.50 + 0.3*0.78 + 0.3*0.72 = 0.65) consistently
exceeds the threshold, forcing reflect-to-generate loops nearly every cycle.
The system locks into the epistemic regime for all 50 cycles with zero regime
switches and zero overlay vetoes (moral_weight=0.05 stays far below 0.85,
competition and resource_decay remain low).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def over_learning_trap_results(tmp_path_factory):
    """Run the Over-Learning Trap V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "over_learning_trap_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("over_learning_trap")
    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    summary = runtime.run()

    trace_records = []
    trace_path = output_dir / "trace.jsonl"
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            trace_records.append(json.loads(line))

    return {
        "summary": summary,
        "traces": trace_records,
        "output_dir": output_dir,
    }


# -- Tests ------------------------------------------------------------------


def test_runs_correct_cycles(over_learning_trap_results):
    """Simulation completes exactly 50 cycles."""
    summary = over_learning_trap_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_epistemic_dominates(over_learning_trap_results):
    """Epistemic regime owns all 50 cycles under sustained ambiguity and novelty."""
    summary = over_learning_trap_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("epistemic", 0) == 50, (
        f"Expected epistemic to dominate all 50 cycles, "
        f"got {dist.get('epistemic', 0)}.  Distribution: {dist}"
    )


def test_no_regime_switches(over_learning_trap_results):
    """Zero regime switches -- the system stays locked in epistemic throughout."""
    summary = over_learning_trap_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected zero regime switches under constant epistemic pressure, "
        f"got {summary['regime_switches']}"
    )


def test_over_learning_dominates(over_learning_trap_results):
    """Over-learning bypass fires nearly every cycle (>= 40 of 50) due to lowered budget."""
    summary = over_learning_trap_results["summary"]
    bypass_counts = summary["bypass_counts"]
    ol_count = bypass_counts.get("over_learning", 0)
    assert ol_count >= 40, (
        f"Expected over_learning bypass to fire >= 40 times under sustained "
        f"ambiguity=0.78 + novelty_pressure=0.72 + failure_count=0.50 "
        f"with epistemic budget=0.40, got {ol_count}.  "
        f"Bypass counts: {bypass_counts}"
    )


def test_no_vetoes(over_learning_trap_results):
    """Zero overlay veto events -- moral_weight and coalition stressors stay far below thresholds."""
    summary = over_learning_trap_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes (moral_weight=0.05, competition=0.06, "
        f"resource_decay=0.04 all below thresholds), "
        f"got {summary['total_veto_events']}"
    )
