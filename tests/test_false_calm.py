"""False Calm V0 scenario -- extended peacetime then sudden sustained crisis.

The False Calm scenario models a system that coasts in near-zero-stress
peacetime for roughly 50 cycles, then experiences a sudden sustained crisis
for the final 22 cycles.  During the calm phase, peacetime dominates with
occasional minor drift.  When the crisis hits, survival, legal, and other
high-stress regimes activate.  The impulse bypass fires during the crisis
onset as threat_level and time_pressure spike sharply.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def false_calm_results(tmp_path_factory):
    """Run the False Calm V0 scenario once and share results across all tests."""
    spec_path = EXAMPLES_DIR / "false_calm_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("false_calm")
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


def test_runs_correct_cycles(false_calm_results):
    """Simulation completes exactly 72 cycles."""
    summary = false_calm_results["summary"]
    assert summary["total_cycles"] == 72, (
        f"Expected 72 cycles, got {summary['total_cycles']}"
    )


def test_peacetime_dominates(false_calm_results):
    """Peacetime regime accounts for at least 35 of 72 cycles -- the long
    calm phase before the crisis ensures peacetime accumulates a majority.
    """
    summary = false_calm_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("peacetime", 0) >= 35, (
        f"Expected peacetime >= 35 cycles, "
        f"got {dist.get('peacetime', 0)}.  Distribution: {dist}"
    )


def test_crisis_response(false_calm_results):
    """Non-peacetime regimes (legal + survival) accumulate at least 10 cycles
    during the sustained crisis phase.
    """
    summary = false_calm_results["summary"]
    dist = summary["regime_distribution"]
    crisis_cycles = dist.get("legal", 0) + dist.get("survival", 0)
    assert crisis_cycles >= 10, (
        f"Expected legal + survival >= 10 cycles during crisis, "
        f"got {crisis_cycles}.  Distribution: {dist}"
    )


def test_bounded_switches(false_calm_results):
    """Regime switches stay at or below 6 -- one major transition from calm
    to crisis, with minor fluctuations during crisis stabilisation.
    """
    summary = false_calm_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 6, (
        f"Expected at most 6 regime switches, got {switches}"
    )


def test_impulse_fires_in_crisis(false_calm_results):
    """Impulse bypass fires at least once when the sudden crisis onset
    pushes threat_level and time_pressure past the latency budget.
    """
    summary = false_calm_results["summary"]
    bypass_counts = summary["bypass_counts"]
    assert bypass_counts.get("impulse", 0) >= 1, (
        f"Expected impulse bypass to fire at least once during crisis, "
        f"but bypass counts were: {bypass_counts}"
    )
