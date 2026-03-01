"""Bypass dynamics -- adaptive substitutions that collapse deliberative phases.

Whitepaper S5:
  Impulse:       Evaluate -> Execute       (survival)
  Rumination:    Evaluate -> Reflect        (epistemic)
  Mania:         Generate -> Execute        (economic)
  Guilt:         Select   -> Reflect        (moral, legal)
  Over-learning: Reflect  -> Generate       (epistemic, economic)

CRITICAL: Each BypassSpec carries its own latency_budget dict (regime -> threshold).
There is NO global latency_budgets on MaelstromSpec.
Bypass eligibility uses current-cycle signals and per-bypass regime-specific latency budget.
At most one bypass per cycle.
"""
from __future__ import annotations

from dataclasses import dataclass

from .legality import DeformedTransition
from .spec import BypassSpec

CANONICAL_PHASES = ["evaluate", "generate", "select", "execute", "reflect"]

# For each bypass, the canonical transitions it replaces
# (used to compare penalty of bypass vs canonical sub-path).
BYPASS_REPLACES: dict[str, list[str]] = {
    "impulse":       ["evaluate->generate", "generate->select", "select->execute"],
    "rumination":    ["evaluate->generate", "generate->select", "select->execute", "execute->reflect"],
    "mania":         ["generate->select", "select->execute"],
    "guilt":         ["select->execute", "execute->reflect"],
    "over_learning": [],  # Over-learning adds phases, doesn't replace
}


@dataclass
class BypassEligibility:
    name: str
    eligible: bool
    transition_admissible: bool
    stressor_intensity: float
    latency_budget: float
    regime: str
    penalty_saving: float  # positive means bypass is cheaper than canonical sub-path


@dataclass
class BypassEvent:
    name: str
    collapsed_path: list[str]
    skipped_phases: list[str]
    stressor_intensity: float
    regime: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "collapsed_path": self.collapsed_path,
            "skipped_phases": self.skipped_phases,
            "stressor_intensity": round(self.stressor_intensity, 6),
            "regime": self.regime,
        }


def _compute_bypass_intensity(
    bypass: BypassSpec,
    stressor_map: dict[str, float],
) -> float:
    """Weighted sum of relevant stressors for bypass eligibility."""
    total = 0.0
    for sname, weight in bypass.stressor_weights.items():
        total += weight * stressor_map.get(sname, 0.0)
    return total


def check_bypass_eligibility(
    bypasses: list[BypassSpec],
    active_regime: str,
    stressor_map: dict[str, float],
    deformed: dict[str, DeformedTransition],
) -> list[BypassEligibility]:
    """Evaluate eligibility for all bypasses.

    A bypass is eligible when:
      1. Active regime is in the bypass's eligible_regimes
      2. Weighted stressor intensity > per-bypass regime latency budget
      3. Bypass transition is admissible (A' > 0)
    """
    results = []

    for bp in bypasses:
        # Per-bypass latency budget for the active regime
        budget = bp.latency_budget.get(active_regime, 1.0)

        regime_ok = active_regime in bp.eligible_regimes
        intensity = _compute_bypass_intensity(bp, stressor_map)
        exceeds_budget = intensity > budget

        t_key = f"{bp.source_phase}->{bp.target_phase}"
        dt = deformed.get(t_key)
        t_admissible = dt is not None and dt.admissible

        eligible = regime_ok and exceeds_budget and t_admissible

        # Compute penalty saving: canonical sub-path penalty - bypass transition penalty
        bypass_penalty = dt.W_prime if dt else float("inf")
        replaced_keys = BYPASS_REPLACES.get(bp.name, [])
        canonical_sub_penalty = sum(
            deformed[k].W_prime for k in replaced_keys if k in deformed
        )
        # For over_learning (adds phases), penalty saving is the urgency excess
        # above the latency budget -- it fires when reprocessing pressure is high.
        if not replaced_keys:
            penalty_saving = intensity - budget if exceeds_budget else 0.0
        else:
            penalty_saving = canonical_sub_penalty - bypass_penalty

        results.append(BypassEligibility(
            name=bp.name,
            eligible=eligible,
            transition_admissible=t_admissible,
            stressor_intensity=intensity,
            latency_budget=budget,
            regime=active_regime,
            penalty_saving=penalty_saving,
        ))

    return results


def select_bypass(
    eligibilities: list[BypassEligibility],
) -> BypassEligibility | None:
    """Select the best eligible bypass (largest penalty saving), or None."""
    eligible = [e for e in eligibilities if e.eligible and e.penalty_saving > 0]
    if not eligible:
        return None
    # Sort by penalty saving descending, then by name for deterministic tiebreak
    eligible.sort(key=lambda e: (-e.penalty_saving, e.name))
    return eligible[0]


def determine_execution_path(
    bypasses: list[BypassSpec],
    selected_bypass: BypassEligibility | None,
) -> tuple[list[str], BypassEvent | None]:
    """Return the phases to execute and the bypass event (if any).

    Canonical path: [evaluate, generate, select, execute, reflect]
    """
    if selected_bypass is None:
        return list(CANONICAL_PHASES), None

    bp_spec = None
    for b in bypasses:
        if b.name == selected_bypass.name:
            bp_spec = b
            break

    if bp_spec is None:
        return list(CANONICAL_PHASES), None

    skipped = [p for p in CANONICAL_PHASES if p not in bp_spec.collapsed_path]
    event = BypassEvent(
        name=bp_spec.name,
        collapsed_path=bp_spec.collapsed_path,
        skipped_phases=skipped,
        stressor_intensity=selected_bypass.stressor_intensity,
        regime=selected_bypass.regime,
    )
    return list(bp_spec.collapsed_path), event
