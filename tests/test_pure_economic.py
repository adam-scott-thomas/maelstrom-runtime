"""Pure Economic V0 scenario -- opportunity and competition drive economic lock.

The Pure Economic scenario models a system under sustained economic pressure
(opportunity_pressure=0.88, competition=0.80, resource_decay=0.45) with all
crisis-level stressors suppressed.  The economic regime should dominate every
cycle with zero regime switches.  Despite high competition, the coalition veto
requires BOTH competition >= 0.65 AND resource_decay >= 0.55 (logic="all"),
and resource_decay=0.45 stays below threshold.  The mania bypass is eligible
in economic but the stressor profile should not exceed the latency budget.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_economic_results(tmp_path_factory):
    """Run the Pure Economic V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_economic_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_economic")
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


def test_runs_correct_cycles(pure_economic_results):
    """Simulation completes exactly 50 cycles."""
    summary = pure_economic_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_economic_dominates(pure_economic_results):
    """Economic regime owns all 50 cycles under sustained opportunity and
    competition pressure.
    """
    summary = pure_economic_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("economic", 0) == 50, (
        f"Expected economic to dominate all 50 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_economic_results):
    """Zero regime switches -- the system never leaves economic."""
    summary = pure_economic_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_no_bypasses(pure_economic_results):
    """No bypass events fire under the calibrated economic stressor profile."""
    summary = pure_economic_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected 0 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(pure_economic_results):
    """No veto overlays fire -- moral_weight is low (identity veto silent)
    and resource_decay=0.45 is below the coalition veto threshold of 0.55.
    """
    summary = pure_economic_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected 0 total veto events, "
        f"got {summary['total_veto_events']}"
    )
