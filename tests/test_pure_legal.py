"""Pure Legal V0 scenario -- institutional inertia and moral weight sustain legal regime.

The Pure Legal scenario models a system under sustained institutional pressure
(institutional_inertia=0.88, moral_weight=0.50) with crisis stressors
suppressed.  The legal regime, which heavily weights institutional_inertia
(w=0.30) and moral_weight (w=0.25), should dominate every cycle.  No regime
switches should occur.  The identity veto requires moral_weight >= 0.85 and
moral_weight=0.50 is well below threshold.  The guilt bypass is eligible in
legal but the stressor profile should not exceed the latency budget.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_legal_results(tmp_path_factory):
    """Run the Pure Legal V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_legal_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_legal")
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


def test_runs_correct_cycles(pure_legal_results):
    """Simulation completes exactly 50 cycles."""
    summary = pure_legal_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_legal_dominates(pure_legal_results):
    """Legal regime owns all 50 cycles under sustained institutional inertia
    and moderate moral weight.
    """
    summary = pure_legal_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("legal", 0) == 50, (
        f"Expected legal to dominate all 50 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_legal_results):
    """Zero regime switches -- the system never leaves legal."""
    summary = pure_legal_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_no_bypasses(pure_legal_results):
    """No bypass events fire under the calibrated legal stressor profile."""
    summary = pure_legal_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected 0 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(pure_legal_results):
    """No veto overlays fire -- moral_weight=0.50 is far below the 0.85
    identity threshold, and competition/resource_decay are too low for
    the coalition veto.
    """
    summary = pure_legal_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected 0 total veto events, "
        f"got {summary['total_veto_events']}"
    )
