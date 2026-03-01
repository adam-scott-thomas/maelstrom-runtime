"""Creeping Doom V0 scenario -- slow multi-regime drift, no bypasses.

The Creeping Doom scenario models a system under gradually increasing pressure
that drifts through at least three regimes (epistemic, moral, economic) with
very few switches.  No bypass should fire and no vetoes should trigger.  The
regime distribution should show broad coverage across the three primary
regimes, with epistemic playing a significant role.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def creeping_doom_results(tmp_path_factory):
    """Run the Creeping Doom V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "creeping_doom_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("creeping_doom")
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


def test_runs_correct_cycles(creeping_doom_results):
    """Simulation completes exactly 100 cycles."""
    summary = creeping_doom_results["summary"]
    assert summary["total_cycles"] == 100, (
        f"Expected 100 cycles, got {summary['total_cycles']}"
    )


def test_three_regime_drift(creeping_doom_results):
    """At least 3 distinct regimes appear during the gradual drift."""
    summary = creeping_doom_results["summary"]
    dist = summary["regime_distribution"]
    assert len(dist) >= 3, (
        f"Expected at least 3 distinct regimes, got {len(dist)}: {dist}"
    )


def test_minimal_switches(creeping_doom_results):
    """Regime switches remain very low (<= 5) due to gradual pressure."""
    summary = creeping_doom_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 5, (
        f"Expected at most 5 regime switches for gradual drift, got {switches}"
    )


def test_no_bypasses(creeping_doom_results):
    """Zero architectural bypass events across all 100 cycles."""
    summary = creeping_doom_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_epistemic_present(creeping_doom_results):
    """Epistemic regime accounts for at least 10 cycles."""
    summary = creeping_doom_results["summary"]
    dist = summary["regime_distribution"]
    epistemic_count = dist.get("epistemic", 0)
    assert epistemic_count >= 10, (
        f"Expected epistemic regime to have >= 10 cycles, "
        f"got {epistemic_count}.  Distribution: {dist}"
    )
