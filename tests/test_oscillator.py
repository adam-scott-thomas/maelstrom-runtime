"""Oscillator V0 scenario -- two-regime oscillation, no bypasses, no vetoes.

The Oscillator scenario models a system that alternates between survival and
peacetime regimes in a regular pattern.  No bypass should fire, no overlay
vetoes should trigger, and regime switching should stay within a moderate
bounded range reflecting the periodic oscillation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def oscillator_results(tmp_path_factory):
    """Run the Oscillator V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "oscillator_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("oscillator")
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


def test_runs_correct_cycles(oscillator_results):
    """Simulation completes exactly 80 cycles."""
    summary = oscillator_results["summary"]
    assert summary["total_cycles"] == 80, (
        f"Expected 80 cycles, got {summary['total_cycles']}"
    )


def test_two_regime_oscillation(oscillator_results):
    """Only survival and peacetime regimes appear in the distribution."""
    summary = oscillator_results["summary"]
    dist = summary["regime_distribution"]
    allowed = {"survival", "peacetime"}
    unexpected = set(dist.keys()) - allowed
    assert not unexpected, (
        f"Expected only survival and peacetime regimes, "
        f"but also found: {unexpected}.  Distribution: {dist}"
    )


def test_switch_count_bounded(oscillator_results):
    """Regime switches fall within 4-10 range for periodic oscillation."""
    summary = oscillator_results["summary"]
    switches = summary["regime_switches"]
    assert 4 <= switches <= 10, (
        f"Expected 4-10 regime switches for periodic oscillation, got {switches}"
    )


def test_no_bypasses(oscillator_results):
    """Zero architectural bypass events across all 80 cycles."""
    summary = oscillator_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(oscillator_results):
    """Zero overlay veto events -- thresholds are never crossed."""
    summary = oscillator_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes, got {summary['total_veto_events']}"
    )
