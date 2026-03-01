"""Pure Survival V0 scenario -- constant high-threat environment locks regime.

The Pure Survival scenario models a system under sustained extreme threat
(threat_level=0.92, time_pressure=0.90) with all other stressors suppressed.
The survival regime should dominate every single cycle with zero regime
switches, zero bypasses (impulse bypass requires latency budget exceedance,
which the flat stressor profile avoids), and zero identity/coalition vetoes
(moral_weight=0.08 is well below the 0.85 identity threshold).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pure_survival_results(tmp_path_factory):
    """Run the Pure Survival V0 scenario once and share results across all
    tests in this module (scope=module avoids re-running the full simulation
    per test).
    """
    spec_path = EXAMPLES_DIR / "pure_survival_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("pure_survival")
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


def test_runs_correct_cycles(pure_survival_results):
    """Simulation completes exactly 50 cycles."""
    summary = pure_survival_results["summary"]
    assert summary["total_cycles"] == 50, (
        f"Expected 50 cycles, got {summary['total_cycles']}"
    )


def test_survival_dominates(pure_survival_results):
    """Survival regime owns all 50 cycles under sustained high threat."""
    summary = pure_survival_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) == 50, (
        f"Expected survival to dominate all 50 cycles, "
        f"but distribution was: {dist}"
    )


def test_no_regime_switches(pure_survival_results):
    """Zero regime switches -- the system never leaves survival."""
    summary = pure_survival_results["summary"]
    assert summary["regime_switches"] == 0, (
        f"Expected 0 regime switches, got {summary['regime_switches']}"
    )


def test_no_bypasses(pure_survival_results):
    """No bypass events fire under a flat stressor profile in pure survival."""
    summary = pure_survival_results["summary"]
    assert summary["total_bypass_events"] == 0, (
        f"Expected 0 total bypass events, "
        f"got {summary['total_bypass_events']}.  "
        f"Bypass counts: {summary['bypass_counts']}"
    )


def test_no_vetoes(pure_survival_results):
    """No veto overlays fire -- moral_weight=0.08 is far below the 0.85
    identity threshold, and competition/resource_decay are too low for
    the coalition veto.
    """
    summary = pure_survival_results["summary"]
    assert summary["total_veto_events"] == 0, (
        f"Expected 0 total veto events, "
        f"got {summary['total_veto_events']}"
    )
