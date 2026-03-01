"""Impulse Storm V0 scenario -- constant high threat forces impulse bypass every cycle.

The Impulse Storm scenario models a system under sustained high time_pressure
(0.82) and threat_level (0.80) with a lowered impulse survival budget (0.40).
The system locks into the survival regime for all 50 cycles with zero regime
switches.  The impulse bypass fires nearly every cycle because the weighted
stressor signal (0.5*0.82 + 0.5*0.80 = 0.81) consistently exceeds the
survival latency budget of 0.40.  No overlay vetoes trigger because
moral_weight stays far below 0.85 and competition/resource_decay remain low.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def impulse_storm_results(tmp_path_factory):
    """Run the Impulse Storm V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "impulse_storm_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("impulse_storm")
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


def test_runs_correct_cycles(impulse_storm_results):
    """Simulation completes exactly 50 cycles."""
    summary = impulse_storm_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_survival_dominates(impulse_storm_results):
    """Survival regime owns all 50 cycles under sustained high threat."""
    summary = impulse_storm_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) == 50, (
        f"Expected survival to dominate all 50 cycles, "
        f"got {dist.get('survival', 0)}.  Distribution: {dist}"
    )


def test_no_regime_switches(impulse_storm_results):
    """Zero regime switches -- the system stays locked in survival throughout."""
    summary = impulse_storm_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected zero regime switches under constant threat, "
        f"got {summary['regime_switches']}"
    )


def test_impulse_bypass_dominates(impulse_storm_results):
    """Impulse bypass fires nearly every cycle (>= 40 of 50) due to lowered budget."""
    summary = impulse_storm_results["summary"]
    bypass_counts = summary["bypass_counts"]
    impulse_count = bypass_counts.get("impulse", 0)
    assert impulse_count >= 40, (
        f"Expected impulse bypass to fire >= 40 times under sustained "
        f"time_pressure=0.82 + threat_level=0.80 with survival budget=0.40, "
        f"got {impulse_count}.  Bypass counts: {bypass_counts}"
    )


def test_no_vetoes(impulse_storm_results):
    """Zero overlay veto events -- moral_weight and coalition stressors stay far below thresholds."""
    summary = impulse_storm_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes (moral_weight=0.05, competition=0.05, "
        f"resource_decay=0.10 all below thresholds), "
        f"got {summary['total_veto_events']}"
    )
