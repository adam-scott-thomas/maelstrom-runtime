"""Regime arbitration -- penalty signals P_r(t) and gradient-based selection.

Whitepaper Appendix A.2:
  P_r(t) = w_r . S(t) + u_r . C(t)
  r*(t)  = argmax_r  dP_r/dt

Regime selection uses asymmetric inertia (hysteresis): entering a regime
has different friction than leaving it. Calibrated inertia values are
specified per-scenario and are not included in this reference edition.
"""
from __future__ import annotations

from .types import ConstraintState, MaelstromSpec, REGIME_PRIORITY
from .utils import deterministic_argmax


def _dot(a: list[float], b: list[float] | tuple[float, ...]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def initial_constraint_state() -> ConstraintState:
    """C(0) -- all zeros."""
    return ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def compute_penalty(
    regime_w: list[float],
    regime_u: list[float],
    stressor_vec: list[float],
    constraint_vec: ConstraintState | list[float] | tuple[float, ...],
) -> float:
    """P_r(t) = w_r . S(t) + u_r . C(t)"""
    return _dot(regime_w, stressor_vec) + _dot(regime_u, constraint_vec)


def compute_all_penalties(
    spec: MaelstromSpec,
    stressor_vec: list[float],
    constraint_state: ConstraintState,
) -> dict[str, float]:
    """Compute P_r(t) for every regime."""
    return {
        r.name: compute_penalty(r.w, r.u, stressor_vec, constraint_state)
        for r in spec.regimes
    }


def compute_gradients(
    current_penalties: dict[str, float],
    penalty_history: list[dict[str, float]],
    window: int = 1,
) -> dict[str, float]:
    """dP_r/dt over a smoothing window."""
    if not penalty_history:
        return dict(current_penalties)
    lookback = min(window, len(penalty_history))
    past = penalty_history[-lookback]
    return {
        r: (current_penalties[r] - past.get(r, 0.0)) / lookback
        for r in current_penalties
    }


def select_active_regime(
    gradients: dict[str, float],
    current_regime: str | None = None,
    inertia: float | dict[str, float] = 0.0,
) -> str:
    """r*(t) = argmax_r dP_r/dt, with asymmetric hysteresis."""
    adjusted = _apply_inertia(gradients, current_regime, inertia)
    selected = deterministic_argmax(
        list(adjusted.keys()),
        key_fn=lambda r: adjusted[r],
        tiebreak_fn=lambda r: REGIME_PRIORITY.index(r)
            if r in REGIME_PRIORITY else 999,
    )
    return selected or "peacetime"


def _apply_inertia(
    gradients: dict[str, float],
    current_regime: str | None,
    inertia: float | dict[str, float],
) -> dict[str, float]:
    """Apply asymmetric inertia to gradient map."""
    adjusted = dict(gradients)

    if isinstance(inertia, (int, float)):
        if current_regime and current_regime in adjusted:
            adjusted[current_regime] += float(inertia)
        return adjusted

    default = inertia.get("default", 0.0)
    if current_regime and current_regime in adjusted:
        adjusted[current_regime] += inertia.get(
            f"out_of_{current_regime}", default,
        )

    for regime in list(adjusted):
        into_val = inertia.get(f"into_{regime}", 0.0)
        if into_val > 0 and regime != current_regime:
            adjusted[regime] -= into_val

    return adjusted


def update_constraint_state(
    prev: ConstraintState,
    governance_disallow: bool,
    identity_veto: bool,
    coalition_veto: bool,
    coalition_drag: float,
    bypass_activated: bool,
    regime_changed: bool,
    decay: float = 0.8,
) -> ConstraintState:
    """Update C(t) from prior-cycle events with exponential recency weighting."""
    return ConstraintState(
        governance_disallow_count=prev.governance_disallow_count * decay + (1.0 if governance_disallow else 0.0),
        identity_veto_count=prev.identity_veto_count * decay + (1.0 if identity_veto else 0.0),
        coalition_veto_count=prev.coalition_veto_count * decay + (1.0 if coalition_veto else 0.0),
        coalition_drag=coalition_drag,
        bypass_count=prev.bypass_count * decay + (1.0 if bypass_activated else 0.0),
        regime_age=0.0 if regime_changed else prev.regime_age + 1.0,
    )
