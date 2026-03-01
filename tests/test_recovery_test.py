"""Recovery Test V0 scenario -- single disruption, sticky dominant regime.

The Recovery Test scenario models a system that experiences a brief disruption
(survival activation with an impulse bypass) before locking into a highly
sticky dominant regime for the remainder of the run.  The dominant regime
should account for the vast majority of cycles (>= 50), regime switches should
be few, and total bypass events should remain very low.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def recovery_test_results(tmp_path_factory):
    """Run the Recovery Test V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "recovery_test_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("recovery_test")
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


def test_runs_correct_cycles(recovery_test_results):
    """Simulation completes exactly 64 cycles."""
    summary = recovery_test_results["summary"]
    assert summary["total_cycles"] == 64, (
        f"Expected 64 cycles, got {summary['total_cycles']}"
    )


def test_survival_appears(recovery_test_results):
    """Survival regime activates at least once during the disruption."""
    summary = recovery_test_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) >= 1, (
        f"Expected survival to activate at least once, "
        f"but it never appeared.  Distribution: {dist}"
    )


def test_dominant_regime_sticky(recovery_test_results):
    """The most frequent regime accounts for >= 50 cycles (high inertia)."""
    summary = recovery_test_results["summary"]
    dist = summary["regime_distribution"]
    max_count = max(dist.values())
    dominant = max(dist, key=dist.get)
    assert max_count >= 50, (
        f"Expected dominant regime to have >= 50 cycles, "
        f"but '{dominant}' had only {max_count}.  Distribution: {dist}"
    )


def test_few_switches(recovery_test_results):
    """Regime switches remain very low (<= 5) after the brief disruption."""
    summary = recovery_test_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 5, (
        f"Expected at most 5 regime switches, got {switches}"
    )


def test_low_bypass_count(recovery_test_results):
    """Total bypass events remain very low (<= 3)."""
    summary = recovery_test_results["summary"]
    assert summary["total_bypass_events"] <= 3, (
        f"Expected at most 3 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )
