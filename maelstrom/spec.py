"""Maelstrom spec dataclasses -- JSON-loadable scenario definitions.

Every field maps directly to the whitepaper's primitives (Appendix A).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TransitionSpec:
    """A single edge in the legality graph."""
    source: str
    target: str
    A: float          # base admissibility
    W: float          # base penalty weight
    alpha: list[float]  # stressor sensitivity for admissibility deformation
    beta: list[float]   # stressor sensitivity for penalty deformation


@dataclass
class RegimeSpec:
    """Penalty-signal weights for one regime."""
    name: str
    w: list[float]  # stressor weights  (dot with S(t))
    u: list[float]  # constraint-state weights (dot with C(t))


@dataclass
class OverlaySpec:
    """Identity or Coalition veto rule."""
    overlay_type: str              # "identity" | "coalition"
    stressor_thresholds: dict[str, float]
    affected_phases: list[str]
    description: str
    logic: str = "all"             # "all" = AND-gate, "any" = OR-gate


@dataclass
class BypassSpec:
    """One bypass definition.

    CRITICAL: latency_budget is per-bypass (dict keyed by regime name),
    NOT a global field on MaelstromSpec.
    """
    name: str
    source_phase: str
    target_phase: str
    collapsed_path: list[str]           # phases that ARE executed
    eligible_regimes: list[str]
    stressor_weights: dict[str, float]  # relevant stressors + their weights
    latency_budget: dict[str, float]    # regime_name -> threshold, per-bypass


@dataclass
class MaelstromSpec:
    """Complete scenario specification loaded from JSON.

    NOTE: There is NO global latency_budgets field. Each BypassSpec carries
    its own latency_budget dict.
    """
    name: str
    total_cycles: int
    seed: int
    stressor_names: list[str]
    stressor_schedule: dict[str, list[list[float]]]  # name -> [[cycle, value], ...]
    transitions: list[TransitionSpec]
    regimes: list[RegimeSpec]
    overlays: list[OverlaySpec]
    bypasses: list[BypassSpec]
    gradient_window: int = 1  # smoothing window for delta-P_r/delta-t (1 = raw delta)
    regime_inertia: float | dict[str, float] = 0.0  # hysteresis, scalar or asymmetric dict
    specialist_config: dict[str, Any] = field(default_factory=dict)

    # ---- derived helpers ----

    def stressor_index(self, name: str) -> int:
        return self.stressor_names.index(name)

    def regime_by_name(self, name: str) -> RegimeSpec:
        for r in self.regimes:
            if r.name == name:
                return r
        raise KeyError(f"Unknown regime: {name}")

    def get_transition(self, source: str, target: str) -> TransitionSpec | None:
        for t in self.transitions:
            if t.source == source and t.target == target:
                return t
        return None

    # ---- serialization ----

    @classmethod
    def from_json(cls, path: str | Path) -> MaelstromSpec:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        transitions = [
            TransitionSpec(**t) for t in d.get("transitions", [])
        ]
        regimes = [
            RegimeSpec(**r) for r in d["regimes"]
        ]
        overlays = [
            OverlaySpec(**o) for o in d.get("overlays", [])
        ]
        bypasses = [
            BypassSpec(**b) for b in d.get("bypasses", [])
        ]

        return cls(
            name=d["name"],
            total_cycles=d["total_cycles"],
            seed=d["seed"],
            stressor_names=d["stressor_names"],
            stressor_schedule=d["stressor_schedule"],
            transitions=transitions,
            regimes=regimes,
            overlays=overlays,
            bypasses=bypasses,
            gradient_window=d.get("gradient_window", 1),
            regime_inertia=d.get("regime_inertia", 0.0),
            specialist_config=d.get("specialist_config", {}),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_cycles": self.total_cycles,
            "seed": self.seed,
            "stressor_names": self.stressor_names,
            "stressor_schedule": self.stressor_schedule,
            "transitions": [
                {
                    "source": t.source,
                    "target": t.target,
                    "A": t.A,
                    "W": t.W,
                    "alpha": t.alpha,
                    "beta": t.beta,
                }
                for t in self.transitions
            ],
            "regimes": [
                {"name": r.name, "w": r.w, "u": r.u}
                for r in self.regimes
            ],
            "overlays": [
                {
                    "overlay_type": o.overlay_type,
                    "stressor_thresholds": o.stressor_thresholds,
                    "affected_phases": o.affected_phases,
                    "description": o.description,
                    "logic": o.logic,
                }
                for o in self.overlays
            ],
            "bypasses": [
                {
                    "name": b.name,
                    "source_phase": b.source_phase,
                    "target_phase": b.target_phase,
                    "collapsed_path": b.collapsed_path,
                    "eligible_regimes": b.eligible_regimes,
                    "stressor_weights": b.stressor_weights,
                    "latency_budget": b.latency_budget,
                }
                for b in self.bypasses
            ],
            "gradient_window": self.gradient_window,
            "regime_inertia": self.regime_inertia,
            "specialist_config": self.specialist_config,
        }
