"""Integration tests: Crucible V0 scenario.

The Crucible scenario is a stress test that pushes every subsystem to its
limits.  All bypass types should fire, both overlay types should veto,
governance should disallow, all 6 regimes should appear, and significant
regime switching should occur.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def crucible_results(tmp_path_factory):
    """Run the Crucible V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "crucible_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("crucible")
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


def test_crucible_all_bypasses_fire(crucible_results):
    """Every bypass type fires at least once."""
    summary = crucible_results["summary"]
    bypass_counts = summary["bypass_counts"]

    expected_bypasses = ["impulse", "rumination", "mania", "guilt", "over_learning"]
    for bp_name in expected_bypasses:
        count = bypass_counts.get(bp_name, 0)
        assert count >= 1, (
            f"Bypass '{bp_name}' never fired.  Bypass counts: {bypass_counts}"
        )


def test_crucible_identity_veto(crucible_results):
    """Identity overlay vetoes at least once."""
    traces = crucible_results["traces"]

    identity_veto_count = 0
    for t in traces:
        for v in t.get("overlay_veto_events", []):
            if v.get("overlay_type") == "identity":
                identity_veto_count += 1

    assert identity_veto_count >= 1, (
        "Identity overlay never vetoed any proposals in Crucible scenario"
    )


def test_crucible_coalition_veto(crucible_results):
    """Coalition overlay vetoes at least once."""
    traces = crucible_results["traces"]

    coalition_veto_count = 0
    for t in traces:
        for v in t.get("overlay_veto_events", []):
            if v.get("overlay_type") == "coalition":
                coalition_veto_count += 1

    assert coalition_veto_count >= 1, (
        "Coalition overlay never vetoed any proposals in Crucible scenario"
    )


def test_crucible_governance_disallow(crucible_results):
    """At least one governance disallow event.

    A governance disallow occurs when a canonical transition has
    admissible=False in the deformed legality graph.
    """
    traces = crucible_results["traces"]

    canonical_keys = [
        "evaluate->generate",
        "generate->select",
        "select->execute",
        "execute->reflect",
    ]

    disallow_cycles = 0
    for t in traces:
        leg = t.get("legality_summary", {})
        all_admissible = all(
            leg.get(k, {}).get("admissible", True) for k in canonical_keys
        )
        if not all_admissible:
            disallow_cycles += 1

    assert disallow_cycles >= 1, (
        "No governance disallow events detected.  Expected at least one "
        "canonical transition to become inadmissible under high stressor load."
    )


def test_crucible_regret_spikes(crucible_results):
    """Max regret exceeds 0.1."""
    summary = crucible_results["summary"]
    max_regret = summary["max_regret"]

    assert max_regret > 0.1, (
        f"Expected max regret > 0.1 in Crucible scenario, got {max_regret:.4f}"
    )


def test_crucible_regime_switching(crucible_results):
    """Many regime switches (>=5)."""
    summary = crucible_results["summary"]
    switches = summary["regime_switches"]

    assert switches >= 5, (
        f"Expected >= 5 regime switches in Crucible scenario, got {switches}"
    )


def test_crucible_all_regimes_visited(crucible_results):
    """All 6 regimes appear at least once."""
    summary = crucible_results["summary"]
    dist = summary["regime_distribution"]

    expected_regimes = {"survival", "legal", "moral", "economic", "epistemic", "peacetime"}
    visited = set(dist.keys())

    missing = expected_regimes - visited
    assert not missing, (
        f"Regimes never visited: {missing}.  Distribution: {dist}"
    )

    # Each regime should have at least 1 cycle
    for regime in expected_regimes:
        assert dist.get(regime, 0) >= 1, (
            f"Regime '{regime}' has 0 cycles.  Distribution: {dist}"
        )


def test_crucible_doctrine_candidates(crucible_results):
    """Doctrine candidates are generated."""
    summary = crucible_results["summary"]
    total_candidates = summary["doctrine_candidates_total"]

    assert total_candidates > 0, (
        "No doctrine candidates generated in Crucible scenario"
    )

    # With high regret, bypasses, and vetoes, we expect substantial doctrine output
    assert total_candidates >= 10, (
        f"Expected >= 10 doctrine candidates in Crucible scenario, "
        f"got {total_candidates}"
    )
