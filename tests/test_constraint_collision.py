"""Constraint Collision V0 scenario -- oscillating stressors with heavy vetoes.

The Constraint Collision scenario models a system caught between oscillating
survival and legal stressor fields, with coalition veto thresholds permanently
exceeded (competition=0.66 > 0.65, resource_decay=0.56 > 0.55).  The
coalition overlay fires on both the select and execute phases every cycle,
producing extremely high veto counts.  The competing constraints generate
sustained governance friction reflected in elevated mean regret.  Regime
switches remain bounded because the oscillation period is regular, but
multiple regimes accumulate significant cycle counts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def constraint_collision_results(tmp_path_factory):
    """Run the Constraint Collision V0 scenario once and share results across
    all tests.
    """
    spec_path = EXAMPLES_DIR / "constraint_collision_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("constraint_collision")
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


def test_runs_correct_cycles(constraint_collision_results):
    """Simulation completes exactly 56 cycles."""
    summary = constraint_collision_results["summary"]
    assert summary["total_cycles"] == 56, (
        f"Expected 56 cycles, got {summary['total_cycles']}"
    )


def test_multi_regime_present(constraint_collision_results):
    """At least 2 regimes each accumulate 10 or more cycles -- the
    oscillating stressors distribute governance across competing regimes.
    """
    summary = constraint_collision_results["summary"]
    dist = summary["regime_distribution"]
    significant = [k for k, v in dist.items() if v >= 10]
    assert len(significant) >= 2, (
        f"Expected at least 2 regimes with >= 10 cycles each, "
        f"got {len(significant)}: {dist}"
    )


def test_bounded_switches(constraint_collision_results):
    """Regime switches stay at or below 8 -- the regular oscillation period
    and inertia prevent runaway switching.
    """
    summary = constraint_collision_results["summary"]
    switches = summary["regime_switches"]
    assert switches <= 8, (
        f"Expected at most 8 regime switches, got {switches}"
    )


def test_heavy_vetoes(constraint_collision_results):
    """At least 100 overlay veto events fire -- the coalition veto triggers
    on both select and execute phases every cycle because competition and
    resource_decay permanently exceed their thresholds.
    """
    summary = constraint_collision_results["summary"]
    assert summary["total_veto_events"] >= 100, (
        f"Expected at least 100 veto events from sustained coalition vetoes, "
        f"got {summary['total_veto_events']}"
    )


def test_high_regret(constraint_collision_results):
    """Mean regret exceeds 0.3 -- the constant governance friction from
    competing constraints and persistent vetoes elevates decision regret.
    """
    summary = constraint_collision_results["summary"]
    assert summary["mean_regret"] > 0.3, (
        f"Expected mean regret > 0.3 due to governance friction, "
        f"got {summary['mean_regret']:.4f}"
    )
