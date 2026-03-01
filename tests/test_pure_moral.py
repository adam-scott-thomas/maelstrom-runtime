"""Pure Moral V0 scenario -- sustained moral weight triggers identity vetoes.

The Pure Moral scenario models a system under constant high moral exposure
(moral_weight=0.88) with institutional_inertia=0.65 reinforcing the moral
regime.  The moral regime should dominate every cycle with zero switches.
Crucially, the identity veto overlay (threshold: moral_weight >= 0.85) fires
on every cycle that visits the execute phase, producing a large veto count.
No bypasses should fire because the regime never enters survival/epistemic/
economic territory.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_moral_results(tmp_path_factory):
    """Run the Pure Moral V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_moral_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_moral")
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


def test_runs_correct_cycles(pure_moral_results):
    """Simulation completes exactly 50 cycles."""
    summary = pure_moral_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_moral_dominates(pure_moral_results):
    """Moral regime owns all 50 cycles under sustained high moral weight."""
    summary = pure_moral_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("moral", 0) == 50, (
        f"Expected moral to dominate all 50 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_moral_results):
    """Zero regime switches -- the system never leaves moral."""
    summary = pure_moral_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_identity_vetoes_fire(pure_moral_results):
    """Identity veto fires heavily because moral_weight=0.88 exceeds the
    0.85 threshold on every cycle that traverses the execute phase.
    Calibrated expectation: >= 100 total veto events across 50 cycles.
    """
    summary = pure_moral_results["summary"]
    assert summary["total_veto_events"] >= 100, (
        f"Expected >= 100 identity veto events (moral_weight 0.88 > 0.85 "
        f"threshold), got {summary['total_veto_events']}"
    )


def test_no_bypasses(pure_moral_results):
    """No bypass events fire -- moral regime is not eligible for impulse,
    rumination, mania, or over_learning bypasses, and the guilt bypass
    stressor profile does not exceed the latency budget in this scenario.
    """
    summary = pure_moral_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected 0 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )
