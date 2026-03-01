"""Promotion evaluator — benchmark harness for doctrine proposals.

Runs the full scenario suite with doctrines OFF (baseline) and ON (candidate),
compares metrics, and determines whether a proposal should be promoted.
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from ..runtime import MaelstromRuntime
from ..spec import MaelstromSpec
from ..utils import clamp


def apply_deltas(spec: MaelstromSpec, deltas: list[dict]) -> MaelstromSpec:
    """Create a new MaelstromSpec with feedback deltas applied.

    Returns a deep copy with bounded adjustments. Original is not modified.
    """
    new_spec = copy.deepcopy(spec)

    for delta in deltas:
        param = delta["parameter"]
        target = delta["target"]
        value = delta["delta"]

        if param == "W":
            for t in new_spec.transitions:
                if f"{t.source}->{t.target}" == target:
                    t.W = clamp(t.W + value, 0.0, 2.0)

        elif param == "A":
            for t in new_spec.transitions:
                if f"{t.source}->{t.target}" == target:
                    t.A = clamp(t.A + value, 0.0, 2.0)

        elif param == "inertia":
            if isinstance(new_spec.regime_inertia, dict):
                for key in new_spec.regime_inertia:
                    new_spec.regime_inertia[key] = clamp(
                        new_spec.regime_inertia[key] + value, 0.0, 0.1,
                    )
            else:
                new_spec.regime_inertia = clamp(
                    new_spec.regime_inertia + value, 0.0, 0.1,
                )

        elif param == "gradient_window":
            new_spec.gradient_window = max(1, new_spec.gradient_window + int(value))

        elif param == "governance_sensitivity":
            for r in new_spec.regimes:
                if len(r.u) > 0:
                    r.u[0] = clamp(r.u[0] + value, 0.0, 1.0)

    return new_spec


def run_scenario(
    spec_path: Path,
    deltas: list[dict] | None = None,
) -> dict:
    """Run a single scenario and return its summary dict."""
    spec = MaelstromSpec.from_json(spec_path)
    if deltas:
        spec = apply_deltas(spec, deltas)
    with tempfile.TemporaryDirectory() as td:
        runtime = MaelstromRuntime(spec, output_dir=Path(td))
        summary = runtime.run()
    return summary


def run_suite(
    scenario_dir: Path,
    deltas: list[dict] | None = None,
) -> dict[str, dict]:
    """Run all *_v0.json scenarios and return {name: summary}."""
    results: dict[str, dict] = {}
    for spec_path in sorted(scenario_dir.glob("*_v0.json")):
        results[spec_path.stem] = run_scenario(spec_path, deltas)
    return results


def compare_metrics(
    baseline: dict[str, dict],
    candidate: dict[str, dict],
) -> dict:
    """Compare baseline vs candidate suite results.

    Promotion rule:
    - Must improve at least 1 primary metric (lower is better)
    - Must not worsen any safety metric beyond 5% tolerance
    """
    primary_metrics = ["mean_regret", "max_regret", "regime_switches"]
    safety_metrics = ["total_veto_events", "total_bypass_events"]
    tolerance = 0.05

    improvements: dict[str, dict] = {}
    regressions: dict[str, dict] = {}

    for metric in primary_metrics:
        base_vals = [s.get(metric, 0) for s in baseline.values()]
        cand_vals = [s.get(metric, 0) for s in candidate.values()]
        base_mean = sum(base_vals) / max(len(base_vals), 1)
        cand_mean = sum(cand_vals) / max(len(cand_vals), 1)
        delta = cand_mean - base_mean

        if delta < -0.001:
            improvements[metric] = {"base": base_mean, "candidate": cand_mean,
                                     "delta": delta}
        elif delta > 0.001:
            regressions[metric] = {"base": base_mean, "candidate": cand_mean,
                                    "delta": delta}

    safety_ok = True
    for metric in safety_metrics:
        base_total = sum(s.get(metric, 0) for s in baseline.values())
        cand_total = sum(s.get(metric, 0) for s in candidate.values())
        if base_total > 0 and (cand_total - base_total) / base_total > tolerance:
            safety_ok = False
            regressions[metric] = {"base": base_total, "candidate": cand_total,
                                    "delta": cand_total - base_total,
                                    "safety_violation": True}

    return {
        "improvements": improvements,
        "regressions": regressions,
        "safety_ok": safety_ok,
        "promote": len(improvements) > 0 and safety_ok and len(regressions) == 0,
    }


def evaluate_proposal(
    scenario_dir: Path,
    deltas: list[dict],
) -> dict:
    """Evaluate a doctrine proposal against the full scenario suite.

    Returns comparison result with promote=True/False.
    """
    baseline = run_suite(scenario_dir, deltas=None)
    candidate = run_suite(scenario_dir, deltas=deltas)
    return compare_metrics(baseline, candidate)
