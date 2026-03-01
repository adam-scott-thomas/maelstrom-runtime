"""Identity Cage V0 scenario -- sustained moral dominance with heavy identity vetoes.

The Identity Cage scenario sustains moral_weight at 0.88 (above the identity
veto threshold of 0.85), locking the system into the moral regime for the
entire run.  The identity overlay fires on execute nearly every cycle, producing
a large number of veto events.  Because moral_weight never drops and the regime
never switches, zero bypass events should occur.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def identity_cage_results(tmp_path_factory):
    """Run the Identity Cage V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "identity_cage_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("identity_cage")
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


def test_runs_correct_cycles(identity_cage_results):
    """Simulation completes exactly 50 cycles."""
    summary = identity_cage_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_moral_dominates(identity_cage_results):
    """Moral regime accounts for all 50 cycles (system locked in moral)."""
    summary = identity_cage_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("moral", 0) == 50, (
        f"Expected moral regime to dominate all 50 cycles, "
        f"got {dist.get('moral', 0)}.  Distribution: {dist}"
    )


def test_no_regime_switches(identity_cage_results):
    """Zero regime switches -- the system stays locked in moral throughout."""
    summary = identity_cage_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected zero regime switches, got {summary['regime_switches']}"
    )


def test_heavy_identity_vetoes(identity_cage_results):
    """Identity veto fires heavily, producing >= 100 total veto events.

    With moral_weight sustained above 0.85, the identity overlay triggers on
    the execute phase check each cycle.  Across 50 cycles with 3 phases
    checked per cycle, at least 100 veto events should accumulate.
    """
    summary = identity_cage_results["summary"]
    assert summary["total_veto_events"] >= 100, (
        f"Expected >= 100 total veto events from identity overlay, "
        f"got {summary['total_veto_events']}.  "
        f"Veto counts: {summary.get('veto_counts', 'N/A')}"
    )


def test_no_bypasses(identity_cage_results):
    """Zero bypass events -- moral lock-in prevents any bypass activation."""
    summary = identity_cage_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected zero bypasses, got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )
