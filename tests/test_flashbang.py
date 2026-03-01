"""Flashbang V0 scenario -- sudden spike triggers survival, impulse bypass fires.

The Flashbang scenario models a sudden, sharp stressor spike that pushes the
system into survival mode before rapidly recovering into legal-dominant steady
state.  The impulse bypass should fire during the spike, regime switches should
remain low (the system stabilises quickly), and legal should dominate the
post-spike recovery phase.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def flashbang_results(tmp_path_factory):
    """Run the Flashbang V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "flashbang_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("flashbang")
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


def test_runs_correct_cycles(flashbang_results):
    """Simulation completes exactly 60 cycles."""
    summary = flashbang_results["summary"]
    assert summary["total_cycles"] == 60, (
        f"Expected 60 cycles, got {summary['total_cycles']}"
    )


def test_survival_enters_during_spike(flashbang_results):
    """Survival regime activates at least once during the stressor spike."""
    summary = flashbang_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) >= 1, (
        f"Expected survival to activate during spike, but it never appeared.  "
        f"Distribution: {dist}"
    )


def test_impulse_bypass_fires(flashbang_results):
    """Impulse bypass fires at least once in response to the sudden spike."""
    summary = flashbang_results["summary"]
    bypass_counts = summary["bypass_counts"]
    assert bypass_counts.get("impulse", 0) >= 1, (
        f"Expected impulse bypass to fire at least once, "
        f"but bypass counts were: {bypass_counts}"
    )


def test_switch_count(flashbang_results):
    """Regime switches remain bounded -- the spike is sharp but recovery is fast."""
    summary = flashbang_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 6, (
        f"Expected at most 6 regime switches, got {switches}"
    )


def test_post_spike_recovery(flashbang_results):
    """Legal regime dominates the recovery phase (>= 20 cycles in legal)."""
    summary = flashbang_results["summary"]
    dist = summary["regime_distribution"]
    legal_count = dist.get("legal", 0)
    assert legal_count >= 20, (
        f"Expected legal regime to dominate recovery with >= 20 cycles, "
        f"got {legal_count}.  Distribution: {dist}"
    )
