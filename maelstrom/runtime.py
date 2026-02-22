"""Maelstrom core loop -- simplified deterministic cycle execution skeleton.

Implements the structural Deterministic Execution Block (Appendix A.3):
  1. Update S(t) -- stressor vector
  2. Deform legality graph (A' and W')
  3. Compute P_r(t) and gradients
  4. Select active regime
  5. Evaluate bypass eligibility
  6. Determine execution path
  7. Compute regret

This skeleton demonstrates the deterministic cycle structure without
specialist proposal generation, overlay filtering, or trace output.
Calibrated production configurations are proprietary.
"""
from __future__ import annotations

from pathlib import Path

from .bypasses import check_bypass_eligibility, determine_execution_path, select_bypass
from .doctrine import DoctrineState
from .legality import canonical_path_admissible, deform_all, legality_summary
from .regimes import (
    compute_all_penalties,
    compute_gradients,
    initial_constraint_state,
    select_active_regime,
    update_constraint_state,
)
from .stressors import compute_stressor_vector, stressor_dict
from .types import MaelstromSpec
from .utils import DeterministicRNG, hash_state


class MaelstromRuntime:
    """Deterministic simulation runtime for the Maelstrom cognitive architecture.

    This is a structural skeleton demonstrating the cycle loop, regime
    arbitration, legality deformation, bypass collapse, and regret model.
    Specialist agents, overlay filtering, trace output, and feedback
    engines are not included in this reference edition.
    """

    def __init__(self, spec: MaelstromSpec, output_dir: str | Path | None = None):
        self.spec = spec
        self.rng = DeterministicRNG(spec.seed)
        self.constraint_state = initial_constraint_state()
        self.penalty_history: list[dict[str, float]] = []
        self.prev_regime: str | None = None
        self.doctrine = DoctrineState()
        self.cycle_results: list[dict] = []

    def run(self) -> dict:
        """Execute the full simulation. Returns a summary dict."""
        for t in range(1, self.spec.total_cycles + 1):
            result = self._execute_cycle(t)
            self.cycle_results.append(result)

        return {
            "name": self.spec.name,
            "total_cycles": self.spec.total_cycles,
            "seed": self.spec.seed,
            "regime_distribution": self._regime_distribution(),
            "regret": self.doctrine.regret_summary(),
        }

    def _execute_cycle(self, t: int) -> dict:
        """Execute one cycle of the Maelstrom loop."""

        # Step 1: Update S(t)
        stressor_vec = compute_stressor_vector(self.spec, t)
        s_map = stressor_dict(self.spec, stressor_vec)

        # Step 2: Deform legality graph
        deformed = deform_all(self.spec, stressor_vec)
        leg_summary = legality_summary(deformed)

        # Step 3: Compute P_r(t) and gradients
        penalties = compute_all_penalties(
            self.spec, stressor_vec, self.constraint_state,
        )
        gradients = compute_gradients(
            penalties, self.penalty_history, window=self.spec.gradient_window,
        )

        # Step 4: Select active regime
        active_regime = select_active_regime(
            gradients,
            current_regime=self.prev_regime,
            inertia=self.spec.regime_inertia,
        )
        regime_changed = (
            self.prev_regime is not None and active_regime != self.prev_regime
        )

        # Step 5: Evaluate bypass eligibility
        bypass_eligibilities = check_bypass_eligibility(
            self.spec.bypasses, active_regime, s_map, deformed,
        )
        selected_bp = select_bypass(bypass_eligibilities)

        # Step 6: Determine execution path
        execution_path, bypass_event = determine_execution_path(
            self.spec.bypasses, selected_bp,
        )

        # Step 7: Governance disallow check
        governance_disallow = not canonical_path_admissible(deformed)

        # Update state for next cycle
        self.constraint_state = update_constraint_state(
            prev=self.constraint_state,
            governance_disallow=governance_disallow,
            identity_veto=False,
            coalition_veto=False,
            coalition_drag=0.0,
            bypass_activated=bypass_event is not None,
            regime_changed=regime_changed,
        )
        self.penalty_history.append(penalties)
        self.prev_regime = active_regime

        state_hash = hash_state({
            "cycle": t,
            "stressor_vec": [round(v, 8) for v in stressor_vec],
            "active_regime": active_regime,
            "rng_draws": self.rng.draw_count,
        })

        return {
            "cycle": t,
            "active_regime": active_regime,
            "regime_changed": regime_changed,
            "bypass": bypass_event.name if bypass_event else None,
            "execution_path": execution_path,
            "governance_disallow": governance_disallow,
            "state_hash": state_hash,
        }

    def _regime_distribution(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.cycle_results:
            regime = r["active_regime"]
            counts[regime] = counts.get(regime, 0) + 1
        return counts
