"""Coalition Gridlock V0 scenario -- sustained coalition vetoes under legal dominance.

The Coalition Gridlock scenario sustains competition >= 0.65 AND resource_decay
>= 0.55, triggering the coalition overlay veto on both the select and execute
phases every cycle.  The legal regime dominates throughout with very few
switches.  Despite the heavy veto pressure, no bypass should fire because the
stressor profile does not meet any bypass activation thresholds.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def coalition_gridlock_results(tmp_path_factory):
    """Run the Coalition Gridlock V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "coalition_gridlock_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("coalition_gridlock")
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


def test_runs_correct_cycles(coalition_gridlock_results):
    """Simulation completes exactly 50 cycles."""
    summary = coalition_gridlock_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_legal_dominates(coalition_gridlock_results):
    """Legal regime accounts for >= 40 cycles (dominant regime)."""
    summary = coalition_gridlock_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("legal", 0) >= 40, (
        f"Expected legal regime to have >= 40 cycles, "
        f"got {dist.get('legal', 0)}.  Distribution: {dist}"
    )


def test_few_switches(coalition_gridlock_results):
    """Regime switches remain very low (<= 3) under sustained gridlock."""
    summary = coalition_gridlock_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 3, (
        f"Expected at most 3 regime switches, got {switches}"
    )


def test_heavy_coalition_vetoes(coalition_gridlock_results):
    """Coalition veto fires heavily, producing >= 200 total veto events.

    With competition >= 0.65 and resource_decay >= 0.55 sustained every cycle,
    the coalition overlay triggers on both the select and execute phases each
    cycle, accumulating a large veto count across all 50 cycles.
    """
    summary = coalition_gridlock_results["summary"]
    assert summary["total_veto_events"] >= 200, (
        f"Expected >= 200 total veto events from coalition overlay, "
        f"got {summary['total_veto_events']}.  "
        f"Veto counts: {summary.get('veto_counts', 'N/A')}"
    )


def test_no_bypasses(coalition_gridlock_results):
    """Zero bypass events -- gridlock conditions do not trigger any bypass."""
    summary = coalition_gridlock_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )
