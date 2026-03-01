"""Feedback rule engine — deterministic mapping from run outcomes to bounded parameter deltas.

Feedback rules are deterministic functions that map run outcomes to parameter
adjustments. All deltas are bounded, logged, and never modify history.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .utils import clamp


@dataclass
class FeedbackDelta:
    """A single bounded parameter adjustment."""
    parameter: str   # "W" | "A" | "inertia" | "gradient_window" | "governance_sensitivity"
    target: str      # e.g., "evaluate->generate" for transitions, "global" for scalars
    delta: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "target": self.target,
            "delta": round(self.delta, 8),
            "reason": self.reason,
        }


# Hard bounds on all deltas
DELTA_BOUNDS: dict[str, tuple[float, float]] = {
    "W": (-0.05, 0.05),
    "A": (-0.02, 0.02),
    "inertia": (-0.005, 0.005),
    "gradient_window": (-1, 1),
    "governance_sensitivity": (-0.05, 0.05),
}


def compute_feedback_deltas(
    summary: dict,
    candidates: list[dict],
) -> list[FeedbackDelta]:
    """Compute bounded parameter deltas from run outcomes.

    Rules (all deterministic, all bounded):
    1. High mean regret (>0.15) -> reduce W on select->execute
    2. Oscillation events (>0)  -> increase inertia
    3. Gov disallow loops (>0)  -> reduce governance sensitivity
    4. Veto gridlock (>2)       -> reduce W on evaluate->generate
    5. Low-conf switches (>2)   -> increase gradient window
    """
    deltas: list[FeedbackDelta] = []

    mean_regret = summary.get("mean_regret", 0.0)

    # Count candidates by trigger type
    trigger_counts: dict[str, int] = {}
    for c in candidates:
        tt = c.get("trigger_type", "unknown")
        trigger_counts[tt] = trigger_counts.get(tt, 0) + 1

    # Rule 1: High mean regret
    if mean_regret > 0.15:
        delta_w = clamp(-0.01 * mean_regret, *DELTA_BOUNDS["W"])
        deltas.append(FeedbackDelta(
            parameter="W", target="select->execute", delta=delta_w,
            reason=f"mean_regret={mean_regret:.4f}>0.15",
        ))

    # Rule 2: Oscillation
    osc_count = trigger_counts.get("oscillation", 0)
    if osc_count > 0:
        delta_i = clamp(0.001 * osc_count, *DELTA_BOUNDS["inertia"])
        deltas.append(FeedbackDelta(
            parameter="inertia", target="global", delta=delta_i,
            reason=f"oscillation_count={osc_count}",
        ))

    # Rule 3: Governance disallow loops
    gov_count = trigger_counts.get("gov_disallow_loop", 0)
    if gov_count > 0:
        delta_g = clamp(-0.01 * gov_count, *DELTA_BOUNDS["governance_sensitivity"])
        deltas.append(FeedbackDelta(
            parameter="governance_sensitivity", target="global", delta=delta_g,
            reason=f"gov_disallow_loop_count={gov_count}",
        ))

    # Rule 4: Veto gridlock
    veto_count = trigger_counts.get("veto_gridlock", 0)
    if veto_count > 2:
        delta_w = clamp(-0.005 * veto_count, *DELTA_BOUNDS["W"])
        deltas.append(FeedbackDelta(
            parameter="W", target="evaluate->generate", delta=delta_w,
            reason=f"veto_gridlock_count={veto_count}",
        ))

    # Rule 5: Low-confidence switches
    lcs_count = trigger_counts.get("low_conf_switch", 0)
    if lcs_count > 2:
        deltas.append(FeedbackDelta(
            parameter="gradient_window", target="global", delta=1,
            reason=f"low_conf_switch_count={lcs_count}",
        ))

    return deltas


def write_feedback_deltas(deltas: list[FeedbackDelta], output_path: Path) -> None:
    """Write feedback deltas to JSON file."""
    data = {
        "deltas": [d.to_dict() for d in deltas],
        "total_deltas": len(deltas),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
