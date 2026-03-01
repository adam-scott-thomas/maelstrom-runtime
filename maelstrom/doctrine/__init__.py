"""Doctrine formation, regret engine, and counterfactual archive.

Whitepaper S6:
  Doctrine = persistent modification of cognitive behavior from prior execution.
  Requires: trace log, unexecuted-proposal archive, counterfactual cost model,
            veto history, regret model.
  Doctrine promotion is NOT automatic in v0 — only logged as candidates.

Regret = structural comparison between realized and unrealized trajectories.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agents import SCORE_DIMS, score_proposal_for_regime
from ..utils import hash_state


@dataclass
class CounterfactualEntry:
    """An unexecuted proposal stored for post-hoc comparison."""
    proposal: dict[str, Any]
    reason: str   # "bypassed" | "vetoed" | "not_selected"
    cycle: int
    phase: str
    regime_value: float  # value under the active regime

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal["id"],
            "description": self.proposal["description"],
            "phase": self.phase,
            "reason": self.reason,
            "cycle": self.cycle,
            "regime_value": round(self.regime_value, 6),
            "scores": self.proposal["scores"],
        }


@dataclass
class DoctrineCandidate:
    """A proposed doctrine update — NOT auto-promoted in v0."""
    cycle: int
    dtype: str   # "sensitivity_adjustment" | "veto_pattern" | "regime_bias"
    description: str
    proposed_change: dict[str, Any]
    regret_triggered: bool
    promoted: bool = False

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "type": self.dtype,
            "description": self.description,
            "proposed_change": self.proposed_change,
            "regret_triggered": self.regret_triggered,
            "promoted": self.promoted,
        }


_DTYPE_TO_TRIGGER: dict[str, str] = {
    "sensitivity_adjustment": "regret_spike",
    "veto_pattern": "veto_gridlock",
    "gov_disallow_loop": "gov_disallow_loop",
    "low_conf_switch": "low_conf_switch",
    "oscillation": "oscillation",
}


@dataclass
class DoctrineRecord:
    """Structured JSONL record for doctrine candidate emission."""
    cycle: int
    regime: str
    trigger_type: str
    trigger_metrics: dict[str, float]
    proposed_action: str
    evidence: dict[str, Any]
    deterministic_hash: str

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "regime": self.regime,
            "trigger_type": self.trigger_type,
            "trigger_metrics": self.trigger_metrics,
            "proposed_action": self.proposed_action,
            "evidence": self.evidence,
            "deterministic_hash": self.deterministic_hash,
        }


def candidate_to_record(candidate: DoctrineCandidate, regime: str) -> DoctrineRecord | None:
    """Convert internal DoctrineCandidate to structured JSONL record.
    Returns None for types not in _DTYPE_TO_TRIGGER (e.g., regime_bias).
    """
    trigger_type = _DTYPE_TO_TRIGGER.get(candidate.dtype)
    if trigger_type is None:
        return None

    pc = candidate.proposed_change
    metrics: dict[str, float] = {}
    if "regret" in pc:
        metrics["regret"] = pc["regret"]
    if "veto_count" in pc:
        metrics["veto_count"] = float(pc["veto_count"])
    if "disallow_streak" in pc:
        metrics["disallow_streak"] = float(pc["disallow_streak"])
    if "margin" in pc:
        metrics["margin"] = pc["margin"]
    if "oscillation_length" in pc:
        metrics["oscillation_length"] = float(pc["oscillation_length"])

    proposed_action = pc.get("action", "unknown")
    evidence: dict[str, Any] = {"cycle_id": candidate.cycle}
    if "evidence_cycles" in pc:
        evidence["cycle_ids"] = pc["evidence_cycles"]

    record_data = {
        "cycle": candidate.cycle,
        "regime": regime,
        "trigger_type": trigger_type,
        "trigger_metrics": metrics,
        "proposed_action": proposed_action,
        "evidence": evidence,
    }
    det_hash = hash_state(record_data)

    return DoctrineRecord(**record_data, deterministic_hash=det_hash)


@dataclass
class DoctrineState:
    """Accumulates counterfactuals, regret, and doctrine candidates."""
    counterfactual_archive: list[CounterfactualEntry] = field(default_factory=list)
    regret_history: list[float] = field(default_factory=list)
    doctrine_candidates: list[DoctrineCandidate] = field(default_factory=list)
    veto_history: list[dict] = field(default_factory=list)
    governance_disallow_history: list[bool] = field(default_factory=list)
    regime_history: list[str] = field(default_factory=list)

    def archive_proposals(
        self,
        proposals: list[dict[str, Any]],
        reason: str,
        cycle: int,
        regime: str,
    ) -> list[CounterfactualEntry]:
        """Archive unexecuted proposals and return the new entries."""
        entries = []
        for p in proposals:
            entry = CounterfactualEntry(
                proposal=p,
                reason=reason,
                cycle=cycle,
                phase=p.get("phase", "unknown"),
                regime_value=score_proposal_for_regime(p, regime),
            )
            self.counterfactual_archive.append(entry)
            entries.append(entry)
        return entries

    def compute_regret(
        self,
        selected_value: float,
        cycle: int,
        regime: str,
    ) -> float:
        """Regret = max(counterfactual value this cycle) - selected value.

        Positive regret means a forgone option was better.
        """
        cycle_counterfactuals = [
            e for e in self.counterfactual_archive if e.cycle == cycle
        ]
        if not cycle_counterfactuals:
            self.regret_history.append(0.0)
            return 0.0

        max_cf_value = max(e.regime_value for e in cycle_counterfactuals)
        regret = max(0.0, max_cf_value - selected_value)
        self.regret_history.append(regret)
        return regret

    def generate_doctrine_candidates(
        self,
        cycle: int,
        regret: float,
        active_regime: str,
        bypass_activated: bool,
        veto_events: list[dict],
        *,
        governance_disallow: bool = False,
        regime_switch_decision: dict | None = None,
    ) -> list[DoctrineCandidate]:
        """Generate doctrine update candidates based on cycle events."""
        candidates: list[DoctrineCandidate] = []
        regret_threshold = 0.1

        # Record veto history
        self.veto_history.extend(veto_events)

        # Regret-based sensitivity adjustment
        if regret > regret_threshold:
            candidates.append(DoctrineCandidate(
                cycle=cycle,
                dtype="sensitivity_adjustment",
                description=f"High regret ({regret:.3f}) under {active_regime} — "
                            f"consider adjusting selection weights",
                proposed_change={
                    "regime": active_regime,
                    "regret": round(regret, 6),
                    "action": "increase_exploration_weight",
                },
                regret_triggered=True,
            ))

        # Bypass-based regime bias
        if bypass_activated:
            candidates.append(DoctrineCandidate(
                cycle=cycle,
                dtype="regime_bias",
                description=f"Bypass activated under {active_regime} — "
                            f"log for future latency-budget recalibration",
                proposed_change={
                    "regime": active_regime,
                    "action": "recalibrate_latency_budget",
                },
                regret_triggered=False,
            ))

        # Veto-pattern doctrine
        if veto_events:
            candidates.append(DoctrineCandidate(
                cycle=cycle,
                dtype="veto_pattern",
                description=f"{len(veto_events)} veto event(s) — "
                            f"record pattern for constraint learning",
                proposed_change={
                    "veto_count": len(veto_events),
                    "action": "update_constraint_sensitivity",
                },
                regret_triggered=False,
            ))

        # --- Phase 9 triggers ---

        # gov_disallow_loop: fires when 3+ consecutive governance disallows
        self.governance_disallow_history.append(governance_disallow)
        if governance_disallow:
            # Count consecutive True values at the tail
            streak = 0
            for v in reversed(self.governance_disallow_history):
                if v:
                    streak += 1
                else:
                    break
            if streak >= 3:
                candidates.append(DoctrineCandidate(
                    cycle=cycle,
                    dtype="gov_disallow_loop",
                    description=f"Governance disallow streak of {streak} cycles — "
                                f"consider reducing governance penalty",
                    proposed_change={
                        "disallow_streak": streak,
                        "action": "reduce_governance_penalty",
                    },
                    regret_triggered=False,
                ))

        # low_conf_switch: fires when regime switch has margin < 0.005
        if regime_switch_decision is not None:
            current = regime_switch_decision.get("current_regime")
            selected = regime_switch_decision.get("selected_regime")
            margin = regime_switch_decision.get("winner_margin", 1.0)
            if current is not None and current != selected and margin < 0.005:
                candidates.append(DoctrineCandidate(
                    cycle=cycle,
                    dtype="low_conf_switch",
                    description=f"Low-confidence regime switch ({current} -> {selected}, "
                                f"margin={margin:.4f}) — consider widening gradient window",
                    proposed_change={
                        "margin": margin,
                        "from_regime": current,
                        "to_regime": selected,
                        "action": "increase_gradient_window",
                    },
                    regret_triggered=False,
                ))

        # oscillation: fires when A-B-A-B-A-B pattern in last 6 regime history entries
        self.regime_history.append(active_regime)
        if len(self.regime_history) >= 6:
            last6 = self.regime_history[-6:]
            a, b = last6[0], last6[1]
            if a != b and last6 == [a, b, a, b, a, b]:
                # Compute the cycle numbers for the evidence
                evidence_cycles = list(range(
                    cycle - 5, cycle + 1,
                ))
                candidates.append(DoctrineCandidate(
                    cycle=cycle,
                    dtype="oscillation",
                    description=f"Regime oscillation detected: {a} <-> {b} over 6 cycles — "
                                f"consider increasing inertia",
                    proposed_change={
                        "oscillation_length": 6,
                        "regime_a": a,
                        "regime_b": b,
                        "action": "increase_inertia",
                        "evidence_cycles": evidence_cycles,
                    },
                    regret_triggered=False,
                ))

        self.doctrine_candidates.extend(candidates)
        return candidates

    def regret_summary(self) -> dict:
        if not self.regret_history:
            return {"mean": 0.0, "max": 0.0, "total_cycles": 0}
        return {
            "mean": round(sum(self.regret_history) / len(self.regret_history), 6),
            "max": round(max(self.regret_history), 6),
            "total_cycles": len(self.regret_history),
            "cycles_with_regret": sum(1 for r in self.regret_history if r > 0),
        }

    def counterfactual_summary(self, last_n: int = 5) -> list[dict]:
        recent = self.counterfactual_archive[-last_n:]
        return [e.to_dict() for e in recent]
