"""Guilt Spiral V0 scenario -- ramping moral weight triggers guilt bypass and identity veto.

The Guilt Spiral scenario models a system where moral_weight ramps from 0.50
to 0.86 over 50 cycles while institutional_inertia sits at 0.62.  The guilt
bypass has lowered budgets (moral=0.35, legal=0.40) so it fires frequently as
the weighted stressor signal (0.6*moral_weight + 0.4*institutional_inertia)
rises.  Epistemic and legal regimes dominate the distribution because the
regime selector oscillates under competing moral/legal/epistemic pressures,
producing heavy regime thrashing (>= 15 switches).  Once moral_weight crosses
0.85 near cycle 50, the identity overlay veto fires at least once.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def guilt_spiral_results(tmp_path_factory):
    """Run the Guilt Spiral V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "guilt_spiral_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("guilt_spiral")
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


def test_runs_correct_cycles(guilt_spiral_results):
    """Simulation completes exactly 50 cycles."""
    summary = guilt_spiral_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_epistemic_or_legal_dominates(guilt_spiral_results):
    """Epistemic + legal regimes together account for >= 30 of 50 cycles."""
    summary = guilt_spiral_results["summary"]
    dist = summary["regime_distribution"]
    combined = dist.get("epistemic", 0) + dist.get("legal", 0)
    assert combined >= 30, (
        f"Expected epistemic + legal to dominate with >= 30 cycles, "
        f"got {combined} (epistemic={dist.get('epistemic', 0)}, "
        f"legal={dist.get('legal', 0)}).  Full distribution: {dist}"
    )


def test_high_switch_count(guilt_spiral_results):
    """Regime switches >= 15 -- the ramping moral pressure causes heavy thrashing."""
    summary = guilt_spiral_results["summary"]
    switches = summary["regime_switches"]
    assert switches >= 15, (
        f"Expected >= 15 regime switches under moral/legal/epistemic "
        f"oscillation, got {switches}"
    )


def test_guilt_bypass_fires(guilt_spiral_results):
    """Guilt bypass fires >= 10 times as moral_weight ramps with lowered budgets."""
    summary = guilt_spiral_results["summary"]
    bypass_counts = summary["bypass_counts"]
    guilt_count = bypass_counts.get("guilt", 0)
    assert guilt_count >= 10, (
        f"Expected guilt bypass to fire >= 10 times with moral budget=0.35 "
        f"and legal budget=0.40 under ramping moral_weight + high "
        f"institutional_inertia, got {guilt_count}.  "
        f"Bypass counts: {bypass_counts}"
    )


def test_vetoes_present(guilt_spiral_results):
    """Identity veto fires at least once when moral_weight crosses 0.85 near cycle 50."""
    summary = guilt_spiral_results["summary"]
    assert summary["total_veto_events"] >= 1, (
        f"Expected at least 1 identity veto event when moral_weight "
        f"reaches 0.86, got {summary['total_veto_events']}"
    )
