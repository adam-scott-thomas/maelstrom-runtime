"""Double Peak V0 scenario -- two stressor spikes, impulse fires at each peak.

The Double Peak scenario models a system that encounters two distinct stressor
spikes separated by a calmer interval.  Survival should activate during the
peaks, impulse bypass should fire at least once per peak, and no overlay vetoes
should trigger.  The regime switching count should be moderate, reflecting the
two disruption-recovery cycles.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def double_peak_results(tmp_path_factory):
    """Run the Double Peak V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "double_peak_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("double_peak")
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


def test_runs_correct_cycles(double_peak_results):
    """Simulation completes exactly 72 cycles."""
    summary = double_peak_results["summary"]
    assert summary["total_cycles"] == 72, (
        f"Expected 72 cycles, got {summary['total_cycles']}"
    )


def test_survival_activates(double_peak_results):
    """Survival regime activates at least twice (once per peak)."""
    summary = double_peak_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) >= 2, (
        f"Expected survival to activate at least twice across both peaks, "
        f"got {dist.get('survival', 0)}.  Distribution: {dist}"
    )


def test_impulse_fires_at_peaks(double_peak_results):
    """Impulse bypass fires at least twice (once per stressor peak)."""
    summary = double_peak_results["summary"]
    bypass_counts = summary["bypass_counts"]
    assert bypass_counts.get("impulse", 0) >= 2, (
        f"Expected impulse bypass to fire at least twice (once per peak), "
        f"but bypass counts were: {bypass_counts}"
    )


def test_switch_count(double_peak_results):
    """Regime switches stay within 3-12 range for a two-peak scenario."""
    summary = double_peak_results["summary"]
    switches = summary["regime_switches"]
    assert 3 <= switches <= 12, (
        f"Expected 3-12 regime switches, got {switches}"
    )


def test_no_vetoes(double_peak_results):
    """Zero overlay veto events -- peaks do not cross veto thresholds."""
    summary = double_peak_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes, got {summary['total_veto_events']}"
    )
