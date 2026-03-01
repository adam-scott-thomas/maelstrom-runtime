"""Pure Peacetime V0 scenario -- low stressors across the board sustain peacetime regime.

The Pure Peacetime scenario models a system at rest with all stressors at
minimal levels (all <= 0.07).  The peacetime regime, which weights boredom,
opportunity_pressure, competition, and novelty_pressure, should dominate
every cycle because no other regime's characteristic stressors are elevated.
With 40 cycles, zero regime switches, zero bypasses (no stressor exceeds any
latency budget), and zero vetoes (all overlay thresholds are far from being
reached).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_peacetime_results(tmp_path_factory):
    """Run the Pure Peacetime V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_peacetime_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_peacetime")
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


def test_runs_correct_cycles(pure_peacetime_results):
    """Simulation completes exactly 40 cycles."""
    summary = pure_peacetime_results["summary"]
    assert summary["total_cycles"] == 40, (
        f"Expected 40 cycles, got {summary['total_cycles']}"
    )


def test_peacetime_dominates(pure_peacetime_results):
    """Peacetime regime owns all 40 cycles under minimal stressor conditions."""
    summary = pure_peacetime_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("peacetime", 0) == 40, (
        f"Expected peacetime to dominate all 40 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_peacetime_results):
    """Zero regime switches -- the system never leaves peacetime."""
    summary = pure_peacetime_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_no_bypasses(pure_peacetime_results):
    """No bypass events fire -- all stressors are too low to exceed any
    latency budget, and peacetime is not an eligible regime for any bypass.
    """
    summary = pure_peacetime_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected 0 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(pure_peacetime_results):
    """No veto overlays fire -- moral_weight=0.03 is far below the 0.85
    identity threshold, and competition=0.05/resource_decay=0.04 are far
    below coalition thresholds.
    """
    summary = pure_peacetime_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected 0 total veto events, "
        f"got {summary['total_veto_events']}"
    )
