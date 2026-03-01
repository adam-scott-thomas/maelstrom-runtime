"""Ambiguity Storm V0 — epistemic dominance, rumination + over_learning."""
import json
from pathlib import Path
from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec

SPEC_PATH = Path(__file__).resolve().parent.parent / "examples" / "ambiguity_storm_v0.json"

def _run_ambiguity_storm(tmp_path):
    spec = MaelstromSpec.from_json(SPEC_PATH)
    runtime = MaelstromRuntime(spec, output_dir=tmp_path / "out")
    summary = runtime.run()
    return summary, runtime.trace_writer.traces

def test_epistemic_dominates(tmp_path):
    summary, _ = _run_ambiguity_storm(tmp_path)
    dist = summary["regime_distribution"]
    assert dist.get("epistemic", 0) / 48 >= 0.40, f"Epistemic too low: {dist}"

def test_rumination_fires(tmp_path):
    summary, _ = _run_ambiguity_storm(tmp_path)
    assert summary["bypass_counts"].get("rumination", 0) >= 2, f"Rumination: {summary['bypass_counts']}"

def test_over_learning_fires(tmp_path):
    summary, _ = _run_ambiguity_storm(tmp_path)
    assert summary["bypass_counts"].get("over_learning", 0) >= 1, f"Over_learning: {summary['bypass_counts']}"

def test_no_survival(tmp_path):
    summary, _ = _run_ambiguity_storm(tmp_path)
    dist = summary["regime_distribution"]
    assert dist.get("survival", 0) == 0, f"Survival should not activate: {dist}"
