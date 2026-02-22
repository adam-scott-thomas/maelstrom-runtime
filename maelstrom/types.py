"""Core type definitions for the Maelstrom runtime.

Provides the dataclass-based specification model, transition graph types,
regime definitions, overlay rules, and bypass path specifications. Every
field maps directly to the whitepaper's primitives (Appendix A).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple


# ── Legality graph ───────────────────────────────────────────────────────


@dataclass
class TransitionSpec:
    """A single edge in the legality graph."""
    source: str
    target: str
    A: float            # base admissibility
    W: float            # base penalty weight
    alpha: list[float]  # stressor sensitivity for admissibility deformation
    beta: list[float]   # stressor sensitivity for penalty deformation


@dataclass
class DeformedTransition:
    """A legality-graph edge after stressor deformation."""
    source: str
    target: str
    A_prime: float
    W_prime: float
    admissible: bool


# ── Regime arbitration ───────────────────────────────────────────────────


@dataclass
class RegimeSpec:
    """Penalty-signal weights for one regime."""
    name: str
    w: list[float]  # stressor weights  (dot with S(t))
    u: list[float]  # constraint-state weights (dot with C(t))


class ConstraintState(NamedTuple):
    """C(t) — 6-element constraint state vector."""
    governance_disallow_count: float
    identity_veto_count: float
    coalition_veto_count: float
    coalition_drag: float
    bypass_count: float
    regime_age: float


CONSTRAINT_NAMES = list(ConstraintState._fields)

REGIME_PRIORITY = [
    "survival", "legal", "moral", "economic", "epistemic", "peacetime",
]

CANONICAL_PHASES = ["evaluate", "generate", "select", "execute", "reflect"]


# ── Overlay vetoes ───────────────────────────────────────────────────────


@dataclass
class OverlaySpec:
    """Identity or Coalition veto rule."""
    overlay_type: str                       # "identity" | "coalition"
    stressor_thresholds: dict[str, float]
    affected_phases: list[str]
    description: str
    logic: str = "all"                      # "all" = AND, "any" = OR


@dataclass
class VetoEvent:
    """Record of a single overlay veto."""
    overlay_type: str
    description: str
    phase: str
    proposal_id: str
    stressor_state: dict[str, float]
    thresholds: dict[str, float]


# ── Bypass paths ─────────────────────────────────────────────────────────


@dataclass
class BypassSpec:
    """One bypass definition with per-regime latency budget."""
    name: str
    source_phase: str
    target_phase: str
    collapsed_path: list[str]
    eligible_regimes: list[str]
    stressor_weights: dict[str, float]
    latency_budget: dict[str, float]    # regime_name -> threshold


@dataclass
class BypassEvent:
    """Record of an activated bypass."""
    name: str
    collapsed_path: list[str]
    skipped_phases: list[str]
    stressor_intensity: float
    regime: str


# ── Full scenario spec ───────────────────────────────────────────────────


@dataclass
class MaelstromSpec:
    """Complete scenario specification loaded from JSON."""
    name: str
    total_cycles: int
    seed: int
    stressor_names: list[str]
    stressor_schedule: dict[str, list[list[float]]]
    transitions: list[TransitionSpec]
    regimes: list[RegimeSpec]
    overlays: list[OverlaySpec]
    bypasses: list[BypassSpec]
    gradient_window: int = 1
    regime_inertia: float | dict[str, float] = 0.0
    specialist_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> MaelstromSpec:
        path = Path(path).resolve()
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        return cls(
            name=d["name"],
            total_cycles=d["total_cycles"],
            seed=d["seed"],
            stressor_names=d["stressor_names"],
            stressor_schedule=d["stressor_schedule"],
            transitions=[TransitionSpec(**t) for t in d.get("transitions", [])],
            regimes=[RegimeSpec(**r) for r in d["regimes"]],
            overlays=[OverlaySpec(**o) for o in d.get("overlays", [])],
            bypasses=[BypassSpec(**b) for b in d.get("bypasses", [])],
            gradient_window=d.get("gradient_window", 1),
            regime_inertia=d.get("regime_inertia", 0.0),
            specialist_config=d.get("specialist_config", {}),
        )
