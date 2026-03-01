"""Specialist agents — deterministic proposal generators.

Whitepaper S2.3:
  Kestrel Adar  (Evaluate)  — clarity, risk assessment
  Dorian Vale   (Generate)  — novelty, optionality
  Helene Quatre (Select)    — defensibility, obligation
  Vance Calderon(Execute)   — tempo, closure
  Isolde Marek  (Reflect)   — coherence, improvement, blame attribution

Each specialist emits a finite set of phase-local proposals per cycle.
Proposals are deterministic given trace state + seeded RNG.
"""
from __future__ import annotations

from typing import Any

from .utils import DeterministicRNG, clamp

SCORE_DIMS = ["clarity", "novelty", "defensibility", "tempo", "coherence"]

PHASE_SPECIALIST = {
    "evaluate": "kestrel_adar",
    "generate": "dorian_vale",
    "select":   "helene_quatre",
    "execute":  "vance_calderon",
    "reflect":  "isolde_marek",
}

# Regime-based scoring weights for proposal selection.
# Higher weight = regime cares more about that dimension.
REGIME_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "survival":  {"clarity": 0.20, "novelty": 0.00, "defensibility": 0.10, "tempo": 0.60, "coherence": 0.10},
    "legal":     {"clarity": 0.10, "novelty": 0.00, "defensibility": 0.50, "tempo": 0.10, "coherence": 0.30},
    "moral":     {"clarity": 0.10, "novelty": 0.00, "defensibility": 0.30, "tempo": 0.00, "coherence": 0.60},
    "economic":  {"clarity": 0.10, "novelty": 0.30, "defensibility": 0.10, "tempo": 0.40, "coherence": 0.10},
    "epistemic": {"clarity": 0.50, "novelty": 0.20, "defensibility": 0.10, "tempo": 0.00, "coherence": 0.20},
    "peacetime": {"clarity": 0.20, "novelty": 0.10, "defensibility": 0.20, "tempo": 0.10, "coherence": 0.40},
}


def _make_proposal(
    cycle: int, phase: str, specialist: str, index: int,
    description: str, scores: dict[str, float],
) -> dict[str, Any]:
    return {
        "id": f"c{cycle:03d}_{phase}_{specialist}_{index}",
        "cycle": cycle,
        "phase": phase,
        "specialist": specialist,
        "description": description,
        "scores": {d: round(clamp(scores.get(d, 0.5)), 6) for d in SCORE_DIMS},
    }


def _s(stressor_map: dict[str, float], name: str) -> float:
    """Shorthand for stressor lookup with default 0."""
    return stressor_map.get(name, 0.0)


# ---------------------------------------------------------------------------
# Specialist implementations
# ---------------------------------------------------------------------------

def kestrel_adar_proposals(
    cycle: int, stressor_map: dict[str, float], rng: DeterministicRNG,
) -> list[dict[str, Any]]:
    """Evaluate-phase specialist: clarity and risk assessment."""
    tp = _s(stressor_map, "time_pressure")
    amb = _s(stressor_map, "ambiguity")
    threat = _s(stressor_map, "threat_level")

    return [
        _make_proposal(cycle, "evaluate", "kestrel_adar", 0,
            "thorough_assessment",
            {"clarity": 0.90 - 0.15 * tp + rng.noise(0.03),
             "novelty": 0.15 + rng.noise(0.02),
             "defensibility": 0.70 + 0.1 * amb + rng.noise(0.02),
             "tempo": 0.25 + 0.15 * tp + rng.noise(0.02),
             "coherence": 0.65 + rng.noise(0.02)}),
        _make_proposal(cycle, "evaluate", "kestrel_adar", 1,
            "rapid_triage",
            {"clarity": 0.55 + 0.1 * threat + rng.noise(0.03),
             "novelty": 0.10 + rng.noise(0.02),
             "defensibility": 0.40 + rng.noise(0.02),
             "tempo": 0.80 + rng.noise(0.02),
             "coherence": 0.35 + rng.noise(0.02)}),
        _make_proposal(cycle, "evaluate", "kestrel_adar", 2,
            "deep_analysis",
            {"clarity": 0.95 + rng.noise(0.02),
             "novelty": 0.25 + 0.1 * amb + rng.noise(0.02),
             "defensibility": 0.80 + rng.noise(0.02),
             "tempo": 0.10 + rng.noise(0.02),
             "coherence": 0.80 + rng.noise(0.02)}),
    ]


def dorian_vale_proposals(
    cycle: int, stressor_map: dict[str, float], rng: DeterministicRNG,
) -> list[dict[str, Any]]:
    """Generate-phase specialist: novelty and optionality."""
    opp = _s(stressor_map, "opportunity_pressure")
    nov = _s(stressor_map, "novelty_pressure")
    comp = _s(stressor_map, "competition")

    return [
        _make_proposal(cycle, "generate", "dorian_vale", 0,
            "explore_alternatives",
            {"clarity": 0.40 + rng.noise(0.03),
             "novelty": 0.85 + 0.1 * nov + rng.noise(0.02),
             "defensibility": 0.25 + rng.noise(0.02),
             "tempo": 0.50 + 0.1 * opp + rng.noise(0.02),
             "coherence": 0.30 + rng.noise(0.02)}),
        _make_proposal(cycle, "generate", "dorian_vale", 1,
            "conventional_option",
            {"clarity": 0.60 + rng.noise(0.03),
             "novelty": 0.20 + rng.noise(0.02),
             "defensibility": 0.75 + rng.noise(0.02),
             "tempo": 0.60 + rng.noise(0.02),
             "coherence": 0.65 + rng.noise(0.02)}),
        _make_proposal(cycle, "generate", "dorian_vale", 2,
            "creative_synthesis",
            {"clarity": 0.35 + rng.noise(0.03),
             "novelty": 0.95 + rng.noise(0.02),
             "defensibility": 0.20 + 0.1 * comp + rng.noise(0.02),
             "tempo": 0.45 + rng.noise(0.02),
             "coherence": 0.25 + rng.noise(0.02)}),
    ]


def helene_quatre_proposals(
    cycle: int, stressor_map: dict[str, float], rng: DeterministicRNG,
) -> list[dict[str, Any]]:
    """Select-phase specialist: defensibility and obligation."""
    mw = _s(stressor_map, "moral_weight")
    inertia = _s(stressor_map, "institutional_inertia")

    return [
        _make_proposal(cycle, "select", "helene_quatre", 0,
            "defensible_selection",
            {"clarity": 0.55 + rng.noise(0.03),
             "novelty": 0.10 + rng.noise(0.02),
             "defensibility": 0.90 + 0.05 * mw + rng.noise(0.02),
             "tempo": 0.35 + rng.noise(0.02),
             "coherence": 0.60 + rng.noise(0.02)}),
        _make_proposal(cycle, "select", "helene_quatre", 1,
            "pragmatic_choice",
            {"clarity": 0.50 + rng.noise(0.03),
             "novelty": 0.15 + rng.noise(0.02),
             "defensibility": 0.55 + rng.noise(0.02),
             "tempo": 0.75 + rng.noise(0.02),
             "coherence": 0.50 + rng.noise(0.02)}),
        _make_proposal(cycle, "select", "helene_quatre", 2,
            "comprehensive_review",
            {"clarity": 0.65 + rng.noise(0.03),
             "novelty": 0.05 + rng.noise(0.02),
             "defensibility": 0.85 + 0.05 * inertia + rng.noise(0.02),
             "tempo": 0.15 + rng.noise(0.02),
             "coherence": 0.75 + rng.noise(0.02)}),
    ]


def vance_calderon_proposals(
    cycle: int, stressor_map: dict[str, float], rng: DeterministicRNG,
) -> list[dict[str, Any]]:
    """Execute-phase specialist: tempo and closure."""
    tp = _s(stressor_map, "time_pressure")
    threat = _s(stressor_map, "threat_level")
    decay = _s(stressor_map, "resource_decay")

    return [
        _make_proposal(cycle, "execute", "vance_calderon", 0,
            "decisive_action",
            {"clarity": 0.45 + rng.noise(0.03),
             "novelty": 0.15 + rng.noise(0.02),
             "defensibility": 0.40 + rng.noise(0.02),
             "tempo": 0.90 + 0.05 * tp + rng.noise(0.02),
             "coherence": 0.30 + rng.noise(0.02)}),
        _make_proposal(cycle, "execute", "vance_calderon", 1,
            "measured_execution",
            {"clarity": 0.55 + rng.noise(0.03),
             "novelty": 0.10 + rng.noise(0.02),
             "defensibility": 0.65 + 0.1 * threat + rng.noise(0.02),
             "tempo": 0.60 + rng.noise(0.02),
             "coherence": 0.55 + rng.noise(0.02)}),
        _make_proposal(cycle, "execute", "vance_calderon", 2,
            "rapid_deployment",
            {"clarity": 0.30 + rng.noise(0.03),
             "novelty": 0.20 + rng.noise(0.02),
             "defensibility": 0.25 + rng.noise(0.02),
             "tempo": 0.95 + rng.noise(0.02),
             "coherence": 0.20 - 0.1 * decay + rng.noise(0.02)}),
    ]


def isolde_marek_proposals(
    cycle: int, stressor_map: dict[str, float], rng: DeterministicRNG,
    regret_prev: float = 0.0,
) -> list[dict[str, Any]]:
    """Reflect-phase specialist: coherence, improvement, blame attribution."""
    fc = _s(stressor_map, "failure_count")
    amb = _s(stressor_map, "ambiguity")

    return [
        _make_proposal(cycle, "reflect", "isolde_marek", 0,
            "coherence_review",
            {"clarity": 0.55 + rng.noise(0.03),
             "novelty": 0.10 + rng.noise(0.02),
             "defensibility": 0.60 + rng.noise(0.02),
             "tempo": 0.20 + rng.noise(0.02),
             "coherence": 0.90 + rng.noise(0.02)}),
        _make_proposal(cycle, "reflect", "isolde_marek", 1,
            "blame_attribution",
            {"clarity": 0.50 + rng.noise(0.03),
             "novelty": 0.05 + rng.noise(0.02),
             "defensibility": 0.75 + 0.1 * fc + rng.noise(0.02),
             "tempo": 0.15 + rng.noise(0.02),
             "coherence": 0.70 + rng.noise(0.02)}),
        _make_proposal(cycle, "reflect", "isolde_marek", 2,
            "lesson_extraction",
            {"clarity": 0.45 + 0.1 * amb + rng.noise(0.03),
             "novelty": 0.30 + 0.15 * regret_prev + rng.noise(0.02),
             "defensibility": 0.50 + rng.noise(0.02),
             "tempo": 0.10 + rng.noise(0.02),
             "coherence": 0.85 + rng.noise(0.02)}),
    ]


# Registry: phase -> generator function
SPECIALIST_GENERATORS = {
    "evaluate": kestrel_adar_proposals,
    "generate": dorian_vale_proposals,
    "select":   helene_quatre_proposals,
    "execute":  vance_calderon_proposals,
    "reflect":  isolde_marek_proposals,
}


def generate_all_proposals(
    cycle: int,
    stressor_map: dict[str, float],
    rng: DeterministicRNG,
    regret_prev: float = 0.0,
) -> dict[str, list[dict[str, Any]]]:
    """Generate proposals from all 5 specialists."""
    result: dict[str, list[dict[str, Any]]] = {}
    for phase in ["evaluate", "generate", "select", "execute", "reflect"]:
        gen_fn = SPECIALIST_GENERATORS[phase]
        if phase == "reflect":
            result[phase] = gen_fn(cycle, stressor_map, rng, regret_prev)
        else:
            result[phase] = gen_fn(cycle, stressor_map, rng)
    return result


def score_proposal_for_regime(
    proposal: dict[str, Any], regime: str,
) -> float:
    """Compute regime-weighted value of a proposal (higher = better)."""
    weights = REGIME_SCORE_WEIGHTS.get(regime, REGIME_SCORE_WEIGHTS["peacetime"])
    scores = proposal["scores"]
    return sum(weights[d] * scores.get(d, 0.0) for d in SCORE_DIMS)


def select_best_proposal(
    proposals: list[dict[str, Any]], regime: str,
) -> dict[str, Any] | None:
    """Select the proposal with highest regime-weighted score."""
    if not proposals:
        return None
    scored = [(score_proposal_for_regime(p, regime), p["id"], p) for p in proposals]
    scored.sort(key=lambda x: (-x[0], x[1]))  # descending score, ascending id
    return scored[0][2]
