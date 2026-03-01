"""Integration tests: Meridian V0 scenario.

The Meridian scenario models a stable agent in mild conditions with a brief
crisis window around cycles 27-30.  Most cycles should be in peacetime.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def meridian_results(tmp_path_factory):
    """Run the Meridian V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "meridian_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("meridian")
    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    summary = runtime.run()

    # Read full trace for detailed assertions
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


def test_meridian_peacetime_dominant(meridian_results):
    """Peacetime is dominant regime (>80% of cycles)."""
    summary = meridian_results["summary"]
    dist = summary["regime_distribution"]
    total = summary["total_cycles"]

    peacetime_count = dist.get("peacetime", 0)
    peacetime_pct = peacetime_count / total

    assert peacetime_pct > 0.80, (
        f"Expected peacetime > 80% of cycles, got {peacetime_pct:.1%} "
        f"({peacetime_count}/{total}).  Distribution: {dist}"
    )


def test_meridian_survival_appears(meridian_results):
    """Survival regime appears during crisis window."""
    traces = meridian_results["traces"]

    survival_cycles = [
        t["cycle"] for t in traces if t["active_regime"] == "survival"
    ]

    assert len(survival_cycles) > 0, "Survival regime never appeared in Meridian scenario"

    # Survival should appear during or near the crisis window (cycles ~27-30)
    for c in survival_cycles:
        assert 20 <= c <= 35, (
            f"Survival appeared at unexpected cycle {c} (expected near 27-30)"
        )


def test_meridian_regime_switches(meridian_results):
    """Approximately 4 regime switches."""
    summary = meridian_results["summary"]
    switches = summary["regime_switches"]

    assert 2 <= switches <= 8, (
        f"Expected 2-8 regime switches, got {switches}"
    )


def test_meridian_no_bypasses(meridian_results):
    """Zero architectural bypass events."""
    summary = meridian_results["summary"]
    total_bypass = summary["total_bypass_events"]

    assert total_bypass == 0, (
        f"Expected zero bypasses in mild Meridian scenario, got {total_bypass}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_meridian_moral_rise(meridian_results):
    """Moral regime appears in the run."""
    traces = meridian_results["traces"]

    moral_cycles = [
        t["cycle"] for t in traces if t["active_regime"] == "moral"
    ]

    assert len(moral_cycles) > 0, (
        "Moral regime never appeared in Meridian scenario.  "
        "Expected moral_weight stressor to drive moral regime activation."
    )
