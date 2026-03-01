"""Black Swan V0 scenario -- unpredictable sharp spikes across a broad regime mix.

The Black Swan scenario models a system with 3 unpredictable sharp stressor
spikes at cycles 18, 47, and 71, each driven by a different stressor
combination (survival/threat at 18, moral/institutional at 47, economic/
competition/resource at 71).  Between spikes the system idles in low-stress
peacetime/epistemic territory.  The broad stressor variety produces at least 4
distinct regimes, with no single regime dominating more than 40 of the 80
cycles.  Some spikes are intense enough to trigger overlay vetoes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def black_swan_results(tmp_path_factory):
    """Run the Black Swan V0 scenario once and share results across all tests."""
    spec_path = EXAMPLES_DIR / "black_swan_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("black_swan")
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


def test_runs_correct_cycles(black_swan_results):
    """Simulation completes exactly 80 cycles."""
    summary = black_swan_results["summary"]
    assert summary["total_cycles"] == 80, (
        f"Expected 80 cycles, got {summary['total_cycles']}"
    )


def test_multi_regime_distribution(black_swan_results):
    """At least 4 different regimes appear due to varied spike stressors."""
    summary = black_swan_results["summary"]
    dist = summary["regime_distribution"]
    active_regimes = [k for k, v in dist.items() if v > 0]
    assert len(active_regimes) >= 4, (
        f"Expected at least 4 distinct regimes, got {len(active_regimes)}: "
        f"{dist}"
    )


def test_bounded_switches(black_swan_results):
    """Regime switches stay between 3 and 12 -- spikes cause transitions but
    low-stress intervals provide stability between them.
    """
    summary = black_swan_results["summary"]
    switches = summary["regime_switches"]
    assert 3 <= switches <= 12, (
        f"Expected 3-12 regime switches, got {switches}"
    )


def test_vetoes_present(black_swan_results):
    """At least 5 overlay veto events fire across the 3 spike windows."""
    summary = black_swan_results["summary"]
    assert summary["total_veto_events"] >= 5, (
        f"Expected at least 5 veto events, "
        f"got {summary['total_veto_events']}"
    )


def test_no_single_regime_dominates(black_swan_results):
    """No single regime exceeds 40 of the 80 cycles -- the varied spikes
    prevent any one regime from accumulating a majority.
    """
    summary = black_swan_results["summary"]
    dist = summary["regime_distribution"]
    for regime, count in dist.items():
        assert count <= 40, (
            f"Regime '{regime}' dominates with {count}/80 cycles (>40).  "
            f"Distribution: {dist}"
        )
