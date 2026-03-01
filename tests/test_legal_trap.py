"""Legal Trap V0 -- legal dominance, guilt bypass, identity veto."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def legal_trap_results(tmp_path_factory):
    """Run the Legal Trap V0 scenario once and share results across all tests
    in this module (scope=module avoids re-running the full simulation per test).
    """
    spec_path = EXAMPLES_DIR / "legal_trap_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    output_dir = tmp_path_factory.mktemp("legal_trap")
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


def test_legal_regime_dominant(legal_trap_results):
    summary = legal_trap_results["summary"]
    dist = summary["regime_distribution"]
    assert dist.get("legal", 0) / 56 >= 0.25, f"Legal too low: {dist}"


def test_guilt_bypass_fires(legal_trap_results):
    summary = legal_trap_results["summary"]
    assert summary["bypass_counts"].get("guilt", 0) >= 3, (
        f"Guilt bypasses: {summary['bypass_counts']}"
    )


def test_identity_veto_triggers(legal_trap_results):
    traces = legal_trap_results["traces"]
    identity_vetoes = sum(
        1 for t in traces for v in t.get("overlay_veto_events", [])
        if v.get("overlay_type") == "identity"
    )
    assert identity_vetoes >= 1, f"Identity vetoes: {identity_vetoes}"


def test_execute_phase_skipped(legal_trap_results):
    """At least one cycle where guilt bypass skips execute."""
    traces = legal_trap_results["traces"]
    skipped = any(
        "execute" not in t["execution_path"] for t in traces
    )
    assert skipped, "Execute phase never skipped"
