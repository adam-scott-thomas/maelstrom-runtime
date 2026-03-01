"""Regime arbitration — penalty signals P_r(t) and gradient-based selection.

Whitepaper Appendix A.2:
  P_r(t) = w_r · S(t) + u_r · C(t)
  r*(t)  = argmax_r  ΔP_r/Δt

Constraint state C(t) is a 6-element NamedTuple:
  ConstraintState(governance_disallow_count, identity_veto_count,
                  coalition_veto_count, coalition_drag,
                  bypass_count, regime_age)
"""
from __future__ import annotations

from typing import NamedTuple

from .spec import MaelstromSpec
from .utils import REGIME_PRIORITY, deterministic_argmax


# ── ConstraintState NamedTuple ───────────────────────────────────────────


class ConstraintState(NamedTuple):
    governance_disallow_count: float  # recency-weighted
    identity_veto_count: float        # recency-weighted
    coalition_veto_count: float       # recency-weighted
    coalition_drag: float             # [0,1]
    bypass_count: float               # recency-weighted
    regime_age: float                 # cycles since last regime change


CONSTRAINT_NAMES = list(ConstraintState._fields)


# ── helpers ──────────────────────────────────────────────────────────────


def _dot(a: list[float], b: list[float] | tuple[float, ...]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


# ── public API ───────────────────────────────────────────────────────────


def initial_constraint_state() -> ConstraintState:
    """C(0) — all zeros."""
    return ConstraintState(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def compute_penalty(
    regime_w: list[float],
    regime_u: list[float],
    stressor_vec: list[float],
    constraint_vec: ConstraintState | list[float] | tuple[float, ...],
) -> float:
    """P_r(t) = w_r · S(t) + u_r · C(t)"""
    return _dot(regime_w, stressor_vec) + _dot(regime_u, constraint_vec)


def compute_all_penalties(
    spec: MaelstromSpec,
    stressor_vec: list[float],
    constraint_state: ConstraintState | list[float] | tuple[float, ...],
) -> dict[str, float]:
    """Compute P_r(t) for every regime."""
    result = {}
    for r in spec.regimes:
        result[r.name] = compute_penalty(r.w, r.u, stressor_vec, constraint_state)
    return result


def compute_gradients(
    current_penalties: dict[str, float],
    penalty_history: list[dict[str, float]],
    window: int = 1,
) -> dict[str, float]:
    """ΔP_r/Δt over a smoothing window.

    Whitepaper: "maximal finite-difference increase in its penalty signal
    over recent cycles."  window=1 gives raw 1-cycle delta.
    window>1 gives (P(t) - P(t-window)) / window.
    """
    if not penalty_history:
        # First cycle: gradient = penalty itself (change from 0).
        return {r: p for r, p in current_penalties.items()}

    lookback = min(window, len(penalty_history))
    past = penalty_history[-lookback]
    return {
        r: (current_penalties[r] - past.get(r, 0.0)) / lookback
        for r in current_penalties
    }


# ── inertia resolution ───────────────────────────────────────────────────


def _resolve_inertia(
    current_regime: str | None,
    inertia: float | dict[str, float],
    regimes: list[str],
) -> tuple[float, dict[str, float]]:
    """Resolve asymmetric inertia into (out_bonus, {regime: into_penalty}).

    Supports two formats:
      - float: symmetric inertia (backward compat), applied as out_of bonus only
      - dict:  keys like "default", "out_of_survival", "into_peacetime", etc.
               out_of_X = bonus for current regime X (stickiness)
               into_X   = penalty for challenger X (entry barrier)
    """
    if isinstance(inertia, (int, float)):
        return float(inertia), {}

    default = inertia.get("default", 0.0)
    out_bonus = 0.0
    if current_regime is not None:
        out_bonus = inertia.get(f"out_of_{current_regime}", default)

    into_penalties: dict[str, float] = {}
    for r in regimes:
        val = inertia.get(f"into_{r}", 0.0)
        if val > 0:
            into_penalties[r] = val

    return out_bonus, into_penalties


def _apply_inertia(
    gradients: dict[str, float],
    current_regime: str | None,
    inertia: float | dict[str, float],
) -> dict[str, float]:
    """Apply asymmetric inertia to gradient map, returning adjusted gradients."""
    adjusted = dict(gradients)
    out_bonus, into_penalties = _resolve_inertia(
        current_regime, inertia, list(gradients.keys()),
    )

    # Current regime gets stickiness bonus
    if current_regime is not None and current_regime in adjusted:
        adjusted[current_regime] = adjusted[current_regime] + out_bonus

    # Challengers face entry barrier
    for regime, penalty in into_penalties.items():
        if regime != current_regime and regime in adjusted:
            adjusted[regime] = adjusted[regime] - penalty

    return adjusted


# ── regime selection ─────────────────────────────────────────────────────


def select_active_regime(
    gradients: dict[str, float],
    current_regime: str | None = None,
    inertia: float | dict[str, float] = 0.0,
) -> str:
    """r*(t) = argmax_r ΔP_r/Δt, with asymmetric hysteresis and deterministic tie-break.

    Whitepaper S4.3: regime transitions exhibit hysteresis — entry into crisis
    regimes occurs rapidly while exit occurs slowly.

    Supports asymmetric inertia:
      - out_of_X: stickiness bonus for current regime (hard to leave)
      - into_X:   entry penalty for challengers (hard to enter)
    Survival should be easy to enter (low into_survival) and hard to leave
    (high out_of_survival). Peacetime should be moderately sticky.
    """
    adjusted = _apply_inertia(gradients, current_regime, inertia)

    regime_names = list(adjusted.keys())
    selected = deterministic_argmax(
        regime_names,
        key_fn=lambda r: adjusted[r],
        tiebreak_fn=lambda r: REGIME_PRIORITY.index(r)
            if r in REGIME_PRIORITY else 999,
    )
    return selected or "peacetime"


# ── trace metadata ───────────────────────────────────────────────────────


def regime_switch_trace(
    gradients: dict[str, float],
    current_regime: str | None,
    selected_regime: str,
    inertia: float | dict[str, float] = 0.0,
) -> dict:
    """Compute trace metadata for the regime switch decision.

    Returns dict with raw/adjusted gradients, best challenger, margin,
    and whether inertia blocked a switch.
    """
    adjusted = _apply_inertia(gradients, current_regime, inertia)

    # Find what would have won without inertia
    raw_winner = deterministic_argmax(
        list(gradients.keys()),
        key_fn=lambda r: gradients[r],
        tiebreak_fn=lambda r: REGIME_PRIORITY.index(r)
            if r in REGIME_PRIORITY else 999,
    ) or "peacetime"

    # Compute margin: how much the winner beats second place
    sorted_adjusted = sorted(adjusted.items(), key=lambda x: -x[1])
    margin = 0.0
    if len(sorted_adjusted) >= 2:
        margin = sorted_adjusted[0][1] - sorted_adjusted[1][1]

    # Determine best challenger (highest gradient that isn't current)
    best_challenger = None
    challenger_gradient = None
    if current_regime is not None:
        challengers = {r: g for r, g in adjusted.items() if r != current_regime}
        if challengers:
            best_challenger = max(challengers, key=lambda r: challengers[r])
            challenger_gradient = round(challengers[best_challenger], 8)

    # Was a switch blocked by inertia?
    blocked_by_inertia = (raw_winner != current_regime and selected_regime == current_regime)

    out_bonus, into_penalties = _resolve_inertia(
        current_regime, inertia, list(gradients.keys()),
    )

    return {
        "raw_gradients": {k: round(v, 8) for k, v in gradients.items()},
        "adjusted_gradients": {k: round(v, 8) for k, v in adjusted.items()},
        "current_regime": current_regime,
        "selected_regime": selected_regime,
        "raw_winner": raw_winner,
        "best_challenger": best_challenger,
        "challenger_gradient": challenger_gradient,
        "winner_margin": round(margin, 8),
        "out_of_bonus": round(out_bonus, 8),
        "into_penalties": {k: round(v, 8) for k, v in into_penalties.items()},
        "blocked_by_inertia": blocked_by_inertia,
    }


# ── constraint state update ─────────────────────────────────────────────


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
    """Update C(t) from prior-cycle trace events.

    Returns a new immutable ConstraintState.
    governance_disallow_count, identity_veto_count, coalition_veto_count, and
    bypass_count all use exponential recency weighting: prev * decay + new.
    regime_age resets on regime change, otherwise increments.
    """
    new_gov = prev.governance_disallow_count * decay + (1.0 if governance_disallow else 0.0)
    new_id = prev.identity_veto_count * decay + (1.0 if identity_veto else 0.0)
    new_coal = prev.coalition_veto_count * decay + (1.0 if coalition_veto else 0.0)
    new_bypass_count = prev.bypass_count * decay + (1.0 if bypass_activated else 0.0)
    new_regime_age = 0.0 if regime_changed else prev.regime_age + 1.0

    return ConstraintState(
        governance_disallow_count=new_gov,
        identity_veto_count=new_id,
        coalition_veto_count=new_coal,
        coalition_drag=coalition_drag,
        bypass_count=new_bypass_count,
        regime_age=new_regime_age,
    )


def constraint_state_dict(cs: ConstraintState) -> dict[str, float]:
    """Convert a ConstraintState to a plain dictionary."""
    return {name: cs[i] for i, name in enumerate(CONSTRAINT_NAMES)}
