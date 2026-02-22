"""Bypass dynamics -- adaptive substitutions that collapse deliberative phases.

Whitepaper S5:
  Impulse:       Evaluate -> Execute       (survival)
  Rumination:    Evaluate -> Reflect        (epistemic)
  Mania:         Generate -> Execute        (economic)
  Guilt:         Select   -> Reflect        (moral, legal)
  Over-learning: Reflect  -> Generate       (epistemic, economic)

At most one bypass per cycle. Eligibility requires regime match, stressor
intensity exceeding a per-bypass per-regime latency budget, and transition
admissibility in the deformed graph. Calibrated latency budgets are
specified per-scenario and are not included in this reference edition.
"""
from __future__ import annotations

from dataclasses import dataclass

from .types import BypassEvent, BypassSpec, DeformedTransition, CANONICAL_PHASES


@dataclass
class BypassEligibility:
    name: str
    eligible: bool
    transition_admissible: bool
    stressor_intensity: float
    latency_budget: float
    regime: str


def _compute_bypass_intensity(
    bypass: BypassSpec, stressor_map: dict[str, float],
) -> float:
    """Weighted sum of relevant stressors for bypass eligibility."""
    return sum(
        weight * stressor_map.get(sname, 0.0)
        for sname, weight in bypass.stressor_weights.items()
    )


def check_bypass_eligibility(
    bypasses: list[BypassSpec],
    active_regime: str,
    stressor_map: dict[str, float],
    deformed: dict[str, DeformedTransition],
) -> list[BypassEligibility]:
    """Evaluate eligibility for all bypasses."""
    results = []
    for bp in bypasses:
        budget = bp.latency_budget.get(active_regime, 1.0)
        regime_ok = active_regime in bp.eligible_regimes
        intensity = _compute_bypass_intensity(bp, stressor_map)
        t_key = f"{bp.source_phase}->{bp.target_phase}"
        dt = deformed.get(t_key)
        t_admissible = dt is not None and dt.admissible

        results.append(BypassEligibility(
            name=bp.name,
            eligible=regime_ok and intensity > budget and t_admissible,
            transition_admissible=t_admissible,
            stressor_intensity=intensity,
            latency_budget=budget,
            regime=active_regime,
        ))
    return results


def select_bypass(
    eligibilities: list[BypassEligibility],
) -> BypassEligibility | None:
    """Select the best eligible bypass (highest intensity), or None."""
    eligible = [e for e in eligibilities if e.eligible]
    if not eligible:
        return None
    eligible.sort(key=lambda e: (-e.stressor_intensity, e.name))
    return eligible[0]


def determine_execution_path(
    bypasses: list[BypassSpec],
    selected_bypass: BypassEligibility | None,
) -> tuple[list[str], BypassEvent | None]:
    """Return the phases to execute and the bypass event (if any)."""
    if selected_bypass is None:
        return list(CANONICAL_PHASES), None

    bp_spec = next((b for b in bypasses if b.name == selected_bypass.name), None)
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
