"""Noise Field V0 scenario -- slow wobble absorbed by inertia, no bypasses.

The Noise Field scenario models a system under a slow sinusoidal wobble
(period ~7 cycles) between survival and peacetime stressors, with
gradient_window=5 and moderate regime inertia.  The wobble amplitude is
moderate enough that survival dominates throughout, peacetime fills the
troughs, and inertia absorbs jitter so regime switches stay low.  No bypasses
fire (latency budgets are generous) and no overlays veto (moral_weight and
coalition stressors remain well below thresholds).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def noise_field_results(tmp_path_factory):
    """Run the Noise Field V0 scenario once and share results across all tests."""
    spec_path = EXAMPLES_DIR / "noise_field_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("noise_field")
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


def test_runs_correct_cycles(noise_field_results):
    """Simulation completes exactly 60 cycles."""
    summary = noise_field_results["summary"]
    assert summary["total_cycles"] == 60, (
        f"Expected 60 cycles, got {summary['total_cycles']}"
    )


def test_survival_dominates(noise_field_results):
    """Survival regime accounts for at least 30 of 60 cycles -- the wobble
    peaks keep survival stressors above the peacetime threshold most of the
    time.
    """
    summary = noise_field_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) >= 30, (
        f"Expected survival to have >= 30 cycles, "
        f"got {dist.get('survival', 0)}.  Distribution: {dist}"
    )


def test_bounded_switches(noise_field_results):
    """Regime switches stay at or below 8 -- inertia absorbs the slow wobble
    jitter and prevents rapid oscillation.
    """
    summary = noise_field_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 8, (
        f"Expected at most 8 regime switches (inertia absorbs jitter), "
        f"got {switches}"
    )


def test_no_bypasses(noise_field_results):
    """Zero architectural bypass events -- the slow wobble never breaches
    latency budgets.
    """
    summary = noise_field_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(noise_field_results):
    """Zero overlay veto events -- moral_weight and coalition stressors
    remain well below their respective thresholds throughout.
    """
    summary = noise_field_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes, got {summary['total_veto_events']}"
    )
