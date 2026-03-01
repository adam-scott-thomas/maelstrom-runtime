"""Slow Burn V0 scenario -- gradual stressor rise, regime drift, no bypasses.

The Slow Burn scenario models a system where stressors rise linearly from very
low to moderate over 40 cycles.  No bypass should fire (latency budgets are set
high), no vetoes should trigger (moral_weight stays below 0.85, competition and
resource_decay stay below coalition thresholds), and the regime should drift
from peacetime through epistemic into moral as the dominant stressors shift.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def slow_burn_results(tmp_path_factory):
    """Run the Slow Burn V0 scenario once and share results across all tests."""
    spec_path = EXAMPLES_DIR / "slow_burn_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("slow_burn")
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


def test_slow_burn_no_bypasses(slow_burn_results):
    """Zero architectural bypass events across all 40 cycles."""
    summary = slow_burn_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_slow_burn_no_vetoes(slow_burn_results):
    """Zero overlay veto events (moral_weight < 0.85, coalition thresholds not met)."""
    summary = slow_burn_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected zero vetoes, got {summary['total_veto_events']}"
    )


def test_slow_burn_multiple_regimes(slow_burn_results):
    """At least 3 distinct regimes appear during the run."""
    summary = slow_burn_results["summary"]
    assert len(summary["regime_distribution"]) >= 3, (
        f"Expected >= 3 regimes, got {len(summary['regime_distribution'])}: "
        f"{summary['regime_distribution']}"
    )


def test_slow_burn_regime_switches(slow_burn_results):
    """Between 2 and 8 regime switches over 40 cycles."""
    summary = slow_burn_results["summary"]
    assert 2 <= summary["regime_switches"] <= 8, (
        f"Expected 2-8 regime switches, got {summary['regime_switches']}"
    )


def test_slow_burn_no_dominant_regime(slow_burn_results):
    """No single regime dominates more than 60% of cycles."""
    summary = slow_burn_results["summary"]
    dist = summary["regime_distribution"]
    total = summary["total_cycles"]
    for regime, count in dist.items():
        assert count / total <= 0.60, (
            f"Regime '{regime}' dominates {count}/{total} = {count/total:.1%} "
            f"(>60%).  Distribution: {dist}"
        )
