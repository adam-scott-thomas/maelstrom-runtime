"""Pure Epistemic V0 scenario -- high ambiguity and novelty drive epistemic lock with over-learning bypass.

The Pure Epistemic scenario models a system under sustained epistemic pressure
(ambiguity=0.90, novelty_pressure=0.85, failure_count=0.40) with crisis
stressors suppressed.  The epistemic regime, which heavily weights ambiguity
(w=0.40) and novelty_pressure (w=0.30), should dominate every cycle.  No
regime switches should occur.  The over_learning bypass (eligible in epistemic,
weighted by failure_count=0.4, ambiguity=0.3, novelty_pressure=0.3) fires
heavily because the combined stressor signal exceeds the epistemic latency
budget of 0.60.  No vetoes fire because moral_weight is low and competition/
resource_decay are far below coalition thresholds.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_epistemic_results(tmp_path_factory):
    """Run the Pure Epistemic V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_epistemic_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_epistemic")
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


def test_runs_correct_cycles(pure_epistemic_results):
    """Simulation completes exactly 50 cycles."""
    summary = pure_epistemic_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_epistemic_dominates(pure_epistemic_results):
    """Epistemic regime owns all 50 cycles under sustained ambiguity and
    novelty pressure.
    """
    summary = pure_epistemic_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("epistemic", 0) == 50, (
        f"Expected epistemic to dominate all 50 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_epistemic_results):
    """Zero regime switches -- the system never leaves epistemic."""
    summary = pure_epistemic_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_over_learning_bypass_dominates(pure_epistemic_results):
    """Over-learning bypass fires heavily (>= 40 times) because the epistemic
    stressor signal (failure_count*0.4 + ambiguity*0.3 + novelty*0.3 =
    0.40*0.4 + 0.90*0.3 + 0.85*0.3 = 0.685) exceeds the epistemic latency
    budget of 0.60.  The bypass triggers on every cycle that traverses the
    reflect->generate edge.
    """
    summary = pure_epistemic_results["summary"]
    bypass_counts = summary["bypass_counts"]
    over_learning_count = bypass_counts.get("over_learning", 0)
    assert over_learning_count >= 40, (
        f"Expected over_learning bypass to fire >= 40 times, "
        f"got {over_learning_count}.  "
        f"Full bypass counts: {bypass_counts}"
    )


def test_no_vetoes(pure_epistemic_results):
    """No veto overlays fire -- moral_weight=0.06 is far below the 0.85
    identity threshold, and competition=0.08/resource_decay=0.05 are far
    below coalition thresholds.
    """
    summary = pure_epistemic_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected 0 total veto events, "
        f"got {summary['total_veto_events']}"
    )
