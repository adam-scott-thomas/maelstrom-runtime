"""Legality graph deformation -- A'_ij and W'_ij per cycle.

Whitepaper Appendix A.1:
  A'_ij(t) = A_ij - alpha_ij . S(t)
  W'_ij(t) = W_ij + beta_ij  . S(t)
  Transitions with A'_ij(t) <= 0 are procedurally disallowed.
"""
from __future__ import annotations

from .types import DeformedTransition, MaelstromSpec, TransitionSpec


def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def deform_transition(
    t_spec: TransitionSpec, stressor_vec: list[float],
) -> DeformedTransition:
    """Compute A' and W' for one transition given S(t)."""
    a_prime = t_spec.A - _dot(t_spec.alpha, stressor_vec)
    w_prime = t_spec.W + _dot(t_spec.beta, stressor_vec)
    return DeformedTransition(
        source=t_spec.source,
        target=t_spec.target,
        A_prime=a_prime,
        W_prime=max(w_prime, 0.0),
        admissible=a_prime > 0,
    )


def deform_all(
    spec: MaelstromSpec, stressor_vec: list[float],
) -> dict[str, DeformedTransition]:
    """Deform every transition in the legality graph. Keyed by 'source->target'."""
    return {
        f"{dt.source}->{dt.target}": dt
        for t_spec in spec.transitions
        for dt in [deform_transition(t_spec, stressor_vec)]
    }


def legality_summary(deformed: dict[str, DeformedTransition]) -> dict[str, dict]:
    """Trace-friendly summary of the deformed legality graph."""
    return {
        key: {
            "A_prime": round(dt.A_prime, 6),
            "W_prime": round(dt.W_prime, 6),
            "admissible": dt.admissible,
        }
        for key, dt in deformed.items()
    }


def canonical_path_admissible(deformed: dict[str, DeformedTransition]) -> bool:
    """Check if all canonical loop transitions are admissible."""
    canonical_keys = [
        "evaluate->generate", "generate->select", "select->execute",
        "execute->reflect", "reflect->evaluate",
    ]
    return all(
        deformed.get(k, DeformedTransition("", "", 0, 0, False)).admissible
        for k in canonical_keys
    )


def canonical_path_penalty(deformed: dict[str, DeformedTransition]) -> float:
    """Sum of W' for canonical loop transitions E->G->S->X->R->E."""
    canonical_keys = [
        "evaluate->generate", "generate->select", "select->execute",
        "execute->reflect", "reflect->evaluate",
    ]
    return sum(deformed[k].W_prime for k in canonical_keys if k in deformed)
