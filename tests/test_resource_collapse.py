"""Resource Collapse V0 -- coalition veto, mania bypass, economic pressure."""
import json
from pathlib import Path
from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec

SPEC_PATH = Path(__file__).resolve().parent.parent / "examples" / "resource_collapse_v0.json"


def _run_resource_collapse(tmp_path):
    spec = MaelstromSpec.from_json(SPEC_PATH)
    runtime = MaelstromRuntime(spec, output_dir=tmp_path / "out")
    summary = runtime.run()
    return summary, runtime.trace_writer.traces


def test_coalition_veto_triggers(tmp_path):
    _, traces = _run_resource_collapse(tmp_path)
    coalition_vetoes = sum(
        1 for t in traces for v in t.overlay_veto_events
        if v.get("overlay_type") == "coalition"
    )
    assert coalition_vetoes >= 5, f"Coalition vetoes: {coalition_vetoes}"


def test_mania_bypass_fires(tmp_path):
    summary, _ = _run_resource_collapse(tmp_path)
    assert summary["bypass_counts"].get("mania", 0) >= 2, f"Mania: {summary['bypass_counts']}"


def test_economic_regime_active(tmp_path):
    summary, _ = _run_resource_collapse(tmp_path)
    dist = summary["regime_distribution"]
    assert dist.get("economic", 0) / 52 >= 0.10, f"Economic too low: {dist}"


def test_mean_regret_nontrivial(tmp_path):
    summary, _ = _run_resource_collapse(tmp_path)
    assert summary["mean_regret"] > 0.05, f"Mean regret too low: {summary['mean_regret']}"
