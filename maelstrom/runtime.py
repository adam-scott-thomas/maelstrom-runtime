"""Maelstrom core loop — deterministic cycle-level execution.

Implements the Deterministic Execution Block (Appendix A.3):
  1. Load inputs
  2. Initialize trace, state, C(0)
  3. For each cycle t = 1..T:
     a. Update S(t)
     b. Deform legality graph
     c. Update C(t)
     d. Compute P_r(t) and gradients
     e. Select active regime
     f. Generate proposals (all 5 specialists)
     g. Filter by overlay vetoes
     h. Evaluate bypass eligibility
     i. Select execution path
     j. Select proposals per phase
     k. Execute, emit outputs, update state
     l. Compute regret and doctrine candidates
     m. Log trace
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents import (
    generate_all_proposals,
    score_proposal_for_regime,
    select_best_proposal,
)
from .bypasses import (
    CANONICAL_PHASES,
    check_bypass_eligibility,
    determine_execution_path,
    select_bypass,
)
from .doctrine import DoctrineState, DoctrineRecord, candidate_to_record
from .feedback import compute_feedback_deltas, write_feedback_deltas
from .legality import (
    canonical_path_admissible,
    deform_all,
    legality_summary,
)
from .overlays import (
    any_coalition_veto,
    any_identity_veto,
    apply_overlays,
    coalition_drag_level,
)
from .regimes import (
    compute_all_penalties,
    compute_gradients,
    constraint_state_dict,
    initial_constraint_state,
    regime_switch_trace,
    select_active_regime,
    update_constraint_state,
)
from .spec import MaelstromSpec
from .stressors import compute_stressor_vector, stressor_dict
from .trace import CycleTrace, TraceWriter
from .utils import DeterministicRNG, hash_state


class MaelstromRuntime:
    """Deterministic simulation runtime for the Maelstrom cognitive architecture."""

    def __init__(self, spec: MaelstromSpec, output_dir: str | Path | None = None):
        self.spec = spec
        self.rng = DeterministicRNG(spec.seed)

        if output_dir is None:
            output_dir = Path("output") / spec.name.replace(" ", "_").lower()
        self.trace_writer = TraceWriter(output_dir=Path(output_dir))

        # State
        self.constraint_state = initial_constraint_state()
        self.penalty_history: list[dict[str, float]] = []
        self.prev_regime: str | None = None
        self.doctrine = DoctrineState()
        self.prev_regret: float = 0.0
        self._doctrine_records: list[DoctrineRecord] = []

    def run(self) -> dict:
        """Execute the full simulation. Returns the summary dict."""
        # Clear trace file if exists
        jsonl_path = self.trace_writer.output_dir / "trace.jsonl"
        if jsonl_path.exists():
            jsonl_path.unlink()

        for t in range(1, self.spec.total_cycles + 1):
            self._execute_cycle(t, is_final=(t == self.spec.total_cycles))

        # Write structured doctrine candidates JSONL
        self._write_doctrine_candidates_jsonl()

        # Write summary (used by feedback engine)
        summary = self.trace_writer.write_summary(
            self.spec.name, self.spec.total_cycles, self.spec.seed,
        )

        # Compute and write feedback deltas
        candidate_dicts = [r.to_dict() for r in self._doctrine_records]
        fb_deltas = compute_feedback_deltas(summary, candidate_dicts)
        write_feedback_deltas(
            fb_deltas,
            self.trace_writer.output_dir / "feedback_deltas.json",
        )

        self.trace_writer.write_human_trace()
        self.trace_writer.write_report(
            self.spec.name, self.spec.total_cycles, self.spec.seed, summary,
        )
        return summary

    def _execute_cycle(self, t: int, is_final: bool = False):
        """Execute one cycle of the Maelstrom loop."""

        # --- Step 3: Update S(t) ---
        stressor_vec = compute_stressor_vector(self.spec, t)
        s_map = stressor_dict(self.spec, stressor_vec)

        # --- Step 4: Deform legality graph ---
        deformed = deform_all(self.spec, stressor_vec)
        leg_summary = legality_summary(deformed)

        # --- Step 5: Update constraint state C(t) ---
        # (uses events from PREVIOUS cycle, already accumulated in state)
        c_state = self.constraint_state
        c_dict = constraint_state_dict(c_state)

        # --- Step 6: Compute P_r(t) and gradients ---
        penalties = compute_all_penalties(self.spec, stressor_vec, c_state)
        gradients = compute_gradients(
            penalties, self.penalty_history, window=self.spec.gradient_window,
        )

        # --- Step 7: Select active regime ---
        active_regime = select_active_regime(
            gradients,
            current_regime=self.prev_regime,
            inertia=self.spec.regime_inertia,
        )
        regime_changed = (self.prev_regime is not None and active_regime != self.prev_regime)

        # --- Regime switch decision trace ---
        switch_decision = regime_switch_trace(
            gradients, self.prev_regime, active_regime, self.spec.regime_inertia,
        )

        # --- Step 8: Generate proposals from all specialists ---
        all_proposals = generate_all_proposals(
            t, s_map, self.rng, self.prev_regret,
        )

        # --- Step 9: Filter by overlay vetoes ---
        filtered_proposals, veto_events = apply_overlays(
            self.spec.overlays, s_map, all_proposals,
        )
        veto_event_dicts = [v.to_dict() for v in veto_events]

        # Build filtered-out list for trace
        filtered_out: list[dict] = []
        for phase in CANONICAL_PHASES:
            orig_ids = {p["id"] for p in all_proposals.get(phase, [])}
            kept_ids = {p["id"] for p in filtered_proposals.get(phase, [])}
            removed_ids = orig_ids - kept_ids
            for pid in sorted(removed_ids):
                filtered_out.append({
                    "id": pid,
                    "phase": phase,
                    "reason": "overlay_veto",
                })

        # Check governance disallow (any canonical transition not admissible)
        governance_disallow = not canonical_path_admissible(deformed)

        # --- Step 10: Evaluate bypass eligibility ---
        bypass_eligibilities = check_bypass_eligibility(
            self.spec.bypasses, active_regime, s_map, deformed,
        )
        bypass_eligible_map = {e.name: e.eligible for e in bypass_eligibilities}

        # --- Step 10b: Select bypass if eligible ---
        selected_bp = select_bypass(bypass_eligibilities)

        # --- Step 11: Determine execution path ---
        execution_path, bypass_event = determine_execution_path(
            self.spec.bypasses, selected_bp,
        )

        # --- Select best proposal per executed phase ---
        selected_proposals: dict[str, str | None] = {}
        selected_action: dict[str, Any] | None = None
        executed_value = 0.0

        # Deduplicate while preserving order (e.g. over_learning has
        # "generate" twice — only the first occurrence is meaningful).
        seen_phases: set[str] = set()
        unique_path: list[str] = []
        for p in execution_path:
            if p not in seen_phases:
                seen_phases.add(p)
                unique_path.append(p)

        for phase in unique_path:
            phase_proposals = filtered_proposals.get(phase, [])
            best = select_best_proposal(phase_proposals, active_regime)
            if best:
                selected_proposals[phase] = best["id"]
                if phase == "execute":
                    selected_action = {
                        "proposal_id": best["id"],
                        "description": best["description"],
                        "phase": "execute",
                        "scores": best["scores"],
                    }
                    executed_value = score_proposal_for_regime(best, active_regime)
            else:
                selected_proposals[phase] = None

        # If execute phase was skipped (rumination / guilt), no action
        if "execute" not in execution_path:
            selected_action = None
            # Use the terminal phase's proposal value for regret baseline
            terminal_phase = execution_path[-1] if execution_path else "reflect"
            terminal_proposals = filtered_proposals.get(terminal_phase, [])
            terminal_best = select_best_proposal(terminal_proposals, active_regime)
            if terminal_best:
                executed_value = score_proposal_for_regime(terminal_best, active_regime)

        # --- Archive counterfactuals ---
        cycle_counterfactuals: list[dict] = []

        # Archive proposals from skipped phases
        skipped_phases = [p for p in CANONICAL_PHASES if p not in execution_path]
        for phase in skipped_phases:
            skipped_props = all_proposals.get(phase, [])
            entries = self.doctrine.archive_proposals(
                skipped_props, "bypassed", t, active_regime,
            )
            cycle_counterfactuals.extend(e.to_dict() for e in entries)

        # Archive non-selected proposals from executed phases
        for phase in execution_path:
            phase_proposals = filtered_proposals.get(phase, [])
            selected_id = selected_proposals.get(phase)
            not_selected = [p for p in phase_proposals if p["id"] != selected_id]
            entries = self.doctrine.archive_proposals(
                not_selected, "not_selected", t, active_regime,
            )
            cycle_counterfactuals.extend(e.to_dict() for e in entries)

        # Archive vetoed proposals
        for phase in CANONICAL_PHASES:
            orig = all_proposals.get(phase, [])
            kept_ids = {p["id"] for p in filtered_proposals.get(phase, [])}
            vetoed = [p for p in orig if p["id"] not in kept_ids]
            entries = self.doctrine.archive_proposals(
                vetoed, "vetoed", t, active_regime,
            )
            cycle_counterfactuals.extend(e.to_dict() for e in entries)

        # --- Step: Compute regret ---
        regret = self.doctrine.compute_regret(executed_value, t, active_regime)

        # --- Step: Doctrine candidates ---
        doctrine_candidates = self.doctrine.generate_doctrine_candidates(
            cycle=t,
            regret=regret,
            active_regime=active_regime,
            bypass_activated=bypass_event is not None,
            veto_events=veto_event_dicts,
            governance_disallow=governance_disallow,
            regime_switch_decision=switch_decision,
        )

        # Convert to structured records for JSONL
        for dc in doctrine_candidates:
            record = candidate_to_record(dc, active_regime)
            if record is not None:
                self._doctrine_records.append(record)

        # --- Update state for next cycle ---
        self.constraint_state = update_constraint_state(
            prev=c_state,
            governance_disallow=governance_disallow,
            identity_veto=any_identity_veto(veto_events),
            coalition_veto=any_coalition_veto(veto_events),
            coalition_drag=coalition_drag_level(veto_events),
            bypass_activated=bypass_event is not None,
            regime_changed=regime_changed,
        )
        self.penalty_history.append(penalties)
        self.prev_regime = active_regime
        self.prev_regret = regret

        # --- Compute state hash ---
        state_for_hash = {
            "cycle": t,
            "stressor_vec": [round(v, 8) for v in stressor_vec],
            "constraint_state": [round(v, 8) for v in self.constraint_state],
            "active_regime": active_regime,
            "selected_action": selected_action,
            "rng_draws": self.rng.draw_count,
        }
        s_hash = hash_state(state_for_hash)

        # --- Step 13: Log trace ---
        trace = CycleTrace(
            cycle=t,
            seed=self.spec.seed,
            stressor_vector={k: round(v, 6) for k, v in s_map.items()},
            constraint_state=c_dict,
            legality_summary=leg_summary,
            regime_penalties=penalties,
            regime_gradients=gradients,
            active_regime=active_regime,
            regime_switch_decision=switch_decision,
            proposals={
                phase: [
                    {"id": p["id"], "specialist": p["specialist"],
                     "description": p["description"], "scores": p["scores"]}
                    for p in props
                ]
                for phase, props in all_proposals.items()
            },
            filtered_proposals=filtered_out,
            overlay_veto_events=veto_event_dicts,
            bypass_eligible=bypass_eligible_map,
            bypass_activated=bypass_event.to_dict() if bypass_event else None,
            execution_path=execution_path,
            selected_proposals=selected_proposals,
            selected_action=selected_action,
            counterfactual_archive=cycle_counterfactuals,
            regret_score=regret,
            doctrine_candidates=[dc.to_dict() for dc in doctrine_candidates],
            termination_reason="completed" if is_final else None,
            state_hash=s_hash,
        )
        self.trace_writer.append(trace)

    def _write_doctrine_candidates_jsonl(self):
        """Write doctrine_candidates.jsonl — one structured record per candidate."""
        jsonl_path = self.trace_writer.output_dir / "doctrine_candidates.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for record in self._doctrine_records:
                f.write(json.dumps(record.to_dict(), separators=(",", ":")) + "\n")
