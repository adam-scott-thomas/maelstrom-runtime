"""Distribution Shift V0 scenario -- clean mid-run regime transition.

The Distribution Shift scenario models a system where the first 40 cycles are
epistemic-dominant (high ambiguity + novelty_pressure, low threat) and the
second 40 cycles are survival-dominant (high threat_level + time_pressure,
low ambiguity).  The transition is a controlled crossover around cycle 40,
producing a single clean regime switch with hysteresis keeping total switches
very low.  No bypasses fire and no overlay vetoes trigger.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def distribution_shift_results(tmp_path_factory):
    """Run the Distribution Shift V0 scenario once and share results across
    all tests.
    """
    spec_path = EXAMPLES_DIR / "distribution_shift_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("distribution_shift")
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


def test_runs_correct_cycles(distribution_shift_results):
    """Simulation completes exactly 80 cycles."""
    summary = distribution_shift_results["summary"]
    assert summary["total_cycles"] == 80, (
        f"Expected 80 cycles, got {summary['total_cycles']}"
    )


def test_two_regime_dominance(distribution_shift_results):
    """Both epistemic and survival regimes each account for at least 25
    cycles -- each half of the run is dominated by its respective regime.
    """
    summary = distribution_shift_results["summary"]
    dist = summary["regime_distribution"]
    epistemic_count = dist.get("epistemic", 0)
    survival_count = dist.get("survival", 0)
    assert epistemic_count >= 25, (
        f"Expected epistemic >= 25 cycles, got {epistemic_count}.  "
        f"Distribution: {dist}"
    )
    assert survival_count >= 25, (
        f"Expected survival >= 25 cycles, got {survival_count}.  "
        f"Distribution: {dist}"
    )


def test_clean_transition(distribution_shift_results):
    """Regime switches remain at or below 4 -- the controlled crossover
    with hysteresis produces a clean transition, not rapid oscillation.
    """
    summary = distribution_shift_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 4, (
        f"Expected at most 4 regime switches for a clean mid-run transition, "
        f"got {switches}"
    )


def test_no_bypasses(distribution_shift_results):
    """Zero architectural bypass events -- neither half of the run
    breaches latency budgets.
    """
    summary = distribution_shift_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(distribution_shift_results):
    """Zero overlay veto events -- moral_weight and coalition stressors
    stay well below their thresholds in both halves.
    """
    summary = distribution_shift_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes, got {summary['total_veto_events']}"
    )
