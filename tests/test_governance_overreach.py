"""Governance Overreach V0 scenario -- governance friction blocks select-to-execute.

The Governance Overreach scenario has elevated stressors that make the
select-to-execute transition inadmissible (effective admissibility A' < 0),
causing governance_disallow every cycle.  The legal regime dominates with few
switches.  Vetoes remain at zero because vetoes originate from overlays, not
from governance admissibility checks.  The persistent governance friction
causes regret to accumulate above baseline levels.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def governance_overreach_results(tmp_path_factory):
    """Run the Governance Overreach V0 scenario once and share results across
    all tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "governance_overreach_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("governance_overreach")
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


def test_runs_correct_cycles(governance_overreach_results):
    """Simulation completes exactly 56 cycles."""
    summary = governance_overreach_results["summary"]
    assert summary["total_cycles"] == 56, (
        f"Expected 56 cycles, got {summary['total_cycles']}"
    )


def test_legal_dominates(governance_overreach_results):
    """Legal regime accounts for >= 40 cycles (dominant regime)."""
    summary = governance_overreach_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("legal", 0) >= 40, (
        f"Expected legal regime to have >= 40 cycles, "
        f"got {dist.get('legal', 0)}.  Distribution: {dist}"
    )


def test_few_switches(governance_overreach_results):
    """Regime switches remain very low (<= 3) under governance overreach."""
    summary = governance_overreach_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 3, (
        f"Expected at most 3 regime switches, got {switches}"
    )


def test_no_bypasses(governance_overreach_results):
    """Zero bypass events -- governance friction does not trigger bypasses."""
    summary = governance_overreach_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_high_regret(governance_overreach_results):
    """Mean regret exceeds 0.05 due to persistent governance friction.

    The governance_disallow on select-to-execute forces sub-optimal path
    selection every cycle, accumulating regret well above the baseline.
    """
    summary = governance_overreach_results["summary"]
    assert summary["mean_regret"] > 0.05, (
        f"Expected mean_regret > 0.05 due to governance friction, "
        f"got {summary['mean_regret']}"
    )
