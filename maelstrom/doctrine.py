"""Doctrine formation -- regret model interface.

Whitepaper S6:
  Doctrine = persistent modification of cognitive behavior from prior execution.
  Regret = structural comparison between realized and unrealized trajectories.

This module provides the regret computation interface and doctrine candidate
data structures. The promotion evaluator and benchmark gating logic are
not included in this reference edition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import hash_state


@dataclass
class CounterfactualEntry:
    """An unexecuted proposal stored for post-hoc comparison."""
    proposal: dict[str, Any]
    reason: str     # "bypassed" | "vetoed" | "not_selected"
    cycle: int
    phase: str
    regime_value: float


@dataclass
class DoctrineCandidate:
    """A proposed doctrine update -- NOT auto-promoted."""
    cycle: int
    dtype: str
    description: str
    proposed_change: dict[str, Any]
    regret_triggered: bool


@dataclass
class DoctrineRecord:
    """Structured record for doctrine candidate emission."""
    cycle: int
    regime: str
    trigger_type: str
    trigger_metrics: dict[str, float]
    proposed_action: str
    evidence: dict[str, Any]
    deterministic_hash: str


@dataclass
class DoctrineState:
    """Accumulates counterfactuals, regret, and doctrine candidates across a run."""
    counterfactual_archive: list[CounterfactualEntry] = field(default_factory=list)
    regret_history: list[float] = field(default_factory=list)
    doctrine_candidates: list[DoctrineCandidate] = field(default_factory=list)

    def archive_proposals(
        self,
        proposals: list[dict[str, Any]],
        reason: str,
        cycle: int,
        regime_value_fn: Any = None,
    ) -> list[CounterfactualEntry]:
        """Archive unexecuted proposals for counterfactual analysis."""
        entries = []
        for p in proposals:
            entry = CounterfactualEntry(
                proposal=p,
                reason=reason,
                cycle=cycle,
                phase=p.get("phase", "unknown"),
                regime_value=regime_value_fn(p) if regime_value_fn else 0.0,
            )
            self.counterfactual_archive.append(entry)
            entries.append(entry)
        return entries

    def compute_regret(
        self, selected_value: float, cycle: int,
    ) -> float:
        """Regret = max(counterfactual value this cycle) - selected value."""
        cycle_cfs = [e for e in self.counterfactual_archive if e.cycle == cycle]
        if not cycle_cfs:
            self.regret_history.append(0.0)
            return 0.0
        max_cf = max(e.regime_value for e in cycle_cfs)
        regret = max(0.0, max_cf - selected_value)
        self.regret_history.append(regret)
        return regret

    def regret_summary(self) -> dict:
        if not self.regret_history:
            return {"mean": 0.0, "max": 0.0, "total_cycles": 0}
        return {
            "mean": round(sum(self.regret_history) / len(self.regret_history), 6),
            "max": round(max(self.regret_history), 6),
            "total_cycles": len(self.regret_history),
            "cycles_with_regret": sum(1 for r in self.regret_history if r > 0),
        }
