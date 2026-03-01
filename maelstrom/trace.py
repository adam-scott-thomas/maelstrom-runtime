"""Trace-first logging — every cycle emits a complete JSON record.

Outputs:
  trace.jsonl       — one JSON object per cycle, append-only
  summary.json      — high-level run summary
  trace_human.md    — optional readable narrative
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CycleTrace:
    """Complete trace record for one cycle."""
    cycle: int
    seed: int
    stressor_vector: dict[str, float]
    constraint_state: dict[str, float]
    legality_summary: dict[str, dict]
    regime_penalties: dict[str, float]
    regime_gradients: dict[str, float]
    active_regime: str
    regime_switch_decision: dict | None      # inertia trace: margins, blocked, etc.
    proposals: dict[str, list[dict]]        # phase -> proposals
    filtered_proposals: list[dict]           # {id, reason, phase}
    overlay_veto_events: list[dict]
    bypass_eligible: dict[str, bool]
    bypass_activated: dict | None
    execution_path: list[str]
    selected_proposals: dict[str, str | None]  # phase -> proposal_id
    selected_action: dict | None
    counterfactual_archive: list[dict]
    regret_score: float
    doctrine_candidates: list[dict]
    termination_reason: str | None
    state_hash: str

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "seed": self.seed,
            "stressor_vector": self.stressor_vector,
            "constraint_state": self.constraint_state,
            "legality_summary": self.legality_summary,
            "regime_penalties": {k: round(v, 6) for k, v in self.regime_penalties.items()},
            "regime_gradients": {k: round(v, 6) for k, v in self.regime_gradients.items()},
            "active_regime": self.active_regime,
            "regime_switch_decision": self.regime_switch_decision,
            "proposals": self.proposals,
            "filtered_proposals": self.filtered_proposals,
            "overlay_veto_events": self.overlay_veto_events,
            "bypass_eligible": self.bypass_eligible,
            "bypass_activated": self.bypass_activated,
            "execution_path": self.execution_path,
            "selected_proposals": self.selected_proposals,
            "selected_action": self.selected_action,
            "counterfactual_archive": self.counterfactual_archive,
            "regret_score": round(self.regret_score, 6),
            "doctrine_candidates": self.doctrine_candidates,
            "termination_reason": self.termination_reason,
            "state_hash": self.state_hash,
        }


@dataclass
class TraceWriter:
    """Manages trace output files."""
    output_dir: Path
    traces: list[CycleTrace] = field(default_factory=list)

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def append(self, trace: CycleTrace):
        self.traces.append(trace)
        # Append to JSONL immediately for crash-safety
        jsonl_path = self.output_dir / "trace.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict(), separators=(",", ":")) + "\n")

    def write_summary(self, spec_name: str, total_cycles: int, seed: int):
        """Write summary.json after run completes."""
        regime_counts: dict[str, int] = {}
        bypass_counts: dict[str, int] = {}
        total_regret = 0.0
        veto_count = 0
        regime_switches = 0
        prev_regime = None

        for t in self.traces:
            r = t.active_regime
            regime_counts[r] = regime_counts.get(r, 0) + 1
            if prev_regime is not None and r != prev_regime:
                regime_switches += 1
            prev_regime = r

            if t.bypass_activated:
                bname = t.bypass_activated.get("name", "unknown")
                bypass_counts[bname] = bypass_counts.get(bname, 0) + 1

            total_regret += t.regret_score
            veto_count += len(t.overlay_veto_events)

        summary = {
            "spec_name": spec_name,
            "total_cycles": total_cycles,
            "seed": seed,
            "regime_distribution": regime_counts,
            "regime_switches": regime_switches,
            "bypass_counts": bypass_counts,
            "total_bypass_events": sum(bypass_counts.values()),
            "total_veto_events": veto_count,
            "mean_regret": round(total_regret / max(len(self.traces), 1), 6),
            "max_regret": round(max((t.regret_score for t in self.traces), default=0.0), 6),
            "doctrine_candidates_total": sum(
                len(t.doctrine_candidates) for t in self.traces
            ),
        }

        summary_path = self.output_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

    def write_human_trace(self):
        """Write trace_human.md — readable narrative of the run.

        Best-effort: never crashes.  All dict lookups use .get() with fallbacks.
        """
        md_path = self.output_dir / "trace_human.md"
        lines = ["# Maelstrom Trace — Human-Readable Narrative\n"]

        prev_regime = None
        for t in self.traces:
            lines.append(f"## Cycle {t.cycle}")

            # -- Regime line with switch/stable/blocked explanation --
            rsd = t.regime_switch_decision if t.regime_switch_decision else {}
            adj_grads = rsd.get("adjusted_gradients", {})
            raw_grads = rsd.get("raw_gradients", {})

            if prev_regime is None:
                lines.append(f"**Regime:** {t.active_regime} (initial)")
            elif t.active_regime != prev_regime:
                winner_grad = adj_grads.get(t.active_regime, 0.0)
                loser_grad = adj_grads.get(prev_regime, 0.0)
                margin = rsd.get("winner_margin", 0.0)
                lines.append(
                    f"**Regime:** {t.active_regime} (switched from {prev_regime})"
                )
                confidence = " — LOW CONFIDENCE SWITCH" if margin < 0.005 else ""
                lines.append(
                    f"  Reason: {t.active_regime} gradient "
                    f"{winner_grad:+.6f} exceeded {prev_regime} "
                    f"{loser_grad:+.6f} (margin {margin:.6f}){confidence}"
                )
            elif rsd.get("blocked_by_inertia", False):
                raw_winner = rsd.get("raw_winner", "?")
                out_bonus = rsd.get("out_of_bonus", 0.0)
                lines.append(
                    f"**Regime:** {t.active_regime} (stable — inertia blocked "
                    f"{raw_winner})"
                )
                lines.append(
                    f"  {raw_winner} raw gradient "
                    f"{raw_grads.get(raw_winner, 0.0):+.6f} vs "
                    f"{t.active_regime} "
                    f"{raw_grads.get(t.active_regime, 0.0):+.6f}, "
                    f"but out_of bonus {out_bonus:+.6f} held"
                )
            else:
                lines.append(f"**Regime:** {t.active_regime} (stable)")

            # -- Top stressors --
            s_vec = t.stressor_vector if t.stressor_vector else {}
            sorted_s = sorted(s_vec.items(), key=lambda x: -x[1])
            top3 = sorted_s[:3]
            if top3:
                stressor_str = ", ".join(f"{k}={v:.2f}" for k, v in top3)
                lines.append(f"**Top stressors:** {stressor_str}")

            # -- Governance disallow --
            leg = t.legality_summary if t.legality_summary else {}
            inadmissible = [
                edge for edge, info in leg.items()
                if isinstance(info, dict) and not info.get("admissible", True)
            ]
            if inadmissible:
                lines.append(
                    f"**Governance disallow:** {', '.join(inadmissible)} "
                    f"inadmissible (A' <= 0)"
                )

            # -- Bypass --
            bp = t.bypass_activated if t.bypass_activated else None
            if bp:
                skipped = bp.get("skipped_phases", [])
                intensity = bp.get("stressor_intensity", 0.0)
                lines.append(
                    f"**Bypass fired:** {bp.get('name', '?')} "
                    f"(intensity {intensity:.4f}, "
                    f"skipped {' -> '.join(skipped) if skipped else 'none'})"
                )

            # -- Vetoes --
            veto_events = t.overlay_veto_events if t.overlay_veto_events else []
            if veto_events:
                by_type: dict[str, list[dict]] = {}
                for v in veto_events:
                    by_type.setdefault(v.get("overlay_type", "?"), []).append(v)
                for otype, events in by_type.items():
                    sample = events[0]
                    thresh = sample.get("thresholds", {})
                    state = sample.get("stressor_state", {})
                    thresh_str = ", ".join(
                        f"{s} {state.get(s, 0.0):.2f} > {th}"
                        for s, th in thresh.items()
                    )
                    lines.append(
                        f"**Veto:** {len(events)} {otype} veto(s) on "
                        f"{sample.get('phase', '?')} ({thresh_str})"
                    )

            # -- Path --
            path = t.execution_path if t.execution_path else []
            lines.append(f"**Path:** {' -> '.join(path) if path else '(empty)'}")

            # -- Action --
            action = t.selected_action if t.selected_action else None
            if action:
                lines.append(
                    f"**Action:** {action.get('description', 'none')}"
                )
            elif "execute" not in (t.execution_path or []):
                lines.append("**Action:** *(skipped — execute not in path)*")

            # -- Regret + doctrine --
            if t.regret_score > 0:
                lines.append(f"**Regret:** {t.regret_score:.4f}")
            candidates = t.doctrine_candidates if t.doctrine_candidates else []
            for dc in candidates:
                lines.append(
                    f"  Doctrine candidate: [{dc.get('type', '?')}] "
                    f"{dc.get('description', '')}"
                )

            lines.append("")
            prev_regime = t.active_regime

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_report(self, spec_name: str, total_cycles: int, seed: int, summary: dict):
        """Write report.md — one-page run summary.

        Best-effort: never crashes.  All dict lookups use .get() with fallbacks.
        """
        report_path = self.output_dir / "report.md"
        lines = [f"# Run Report: {spec_name}\n"]

        # -- Summary table --
        dist = summary.get("regime_distribution", {})
        lines.append("## Summary\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Cycles | {total_cycles} |")
        lines.append(f"| Seed | {seed} |")
        # Count switch attempts and blocks from trace data
        switch_attempts = 0
        inertia_blocks = 0
        governance_disallow_cycles = 0
        for t in self.traces:
            rsd = t.regime_switch_decision if t.regime_switch_decision else {}
            if rsd.get("raw_winner") and rsd.get("raw_winner") != t.active_regime:
                switch_attempts += 1
            if rsd.get("blocked_by_inertia", False):
                inertia_blocks += 1
            leg = t.legality_summary if t.legality_summary else {}
            if any(
                isinstance(info, dict) and not info.get("admissible", True)
                for info in leg.values()
            ):
                governance_disallow_cycles += 1

        # Mean margin of actual switches
        switch_margins = []
        prev_r = None
        for t in self.traces:
            if prev_r is not None and t.active_regime != prev_r:
                rsd = t.regime_switch_decision if t.regime_switch_decision else {}
                switch_margins.append(rsd.get("winner_margin", 0.0))
            prev_r = t.active_regime
        mean_margin = sum(switch_margins) / max(len(switch_margins), 1)

        lines.append(f"| Regime Switches | {summary.get('regime_switches', 0)} |")
        lines.append(f"| Mean Switch Margin | {mean_margin:.6f} |")
        lines.append(f"| Switch Attempts | {switch_attempts} |")
        lines.append(f"| Blocked by Inertia | {inertia_blocks} |")
        lines.append(f"| Governance Disallow Cycles | {governance_disallow_cycles} |")
        lines.append(f"| Bypasses | {summary.get('total_bypass_events', 0)} |")
        lines.append(f"| Vetoes | {summary.get('total_veto_events', 0)} |")
        lines.append(f"| Mean Regret | {summary.get('mean_regret', 0.0):.4f} |")
        lines.append(f"| Max Regret | {summary.get('max_regret', 0.0):.4f} |")
        lines.append(f"| Doctrine Candidate Events | {summary.get('doctrine_candidates_total', 0)} |")
        lines.append("")

        # -- Regime distribution --
        lines.append("## Regime Distribution\n")
        if dist:
            max_count = max(dist.values())
            for regime, count in sorted(dist.items(), key=lambda x: -x[1]):
                pct = count * 100 // max(total_cycles, 1)
                bar_len = (count * 40) // max(max_count, 1)
                bar = "#" * bar_len
                lines.append(f"  {regime:12s} {bar:40s} {count:3d} ({pct}%)")
        else:
            lines.append("*No regime data.*")
        lines.append("")

        # -- Regime timeline --
        lines.append("## Regime Timeline\n")
        if self.traces:
            runs: list[tuple[str, int, int]] = []
            run_start = 1
            run_regime = self.traces[0].active_regime
            for t in self.traces[1:]:
                if t.active_regime != run_regime:
                    runs.append((run_regime, run_start, t.cycle - 1))
                    run_start = t.cycle
                    run_regime = t.active_regime
            runs.append((run_regime, run_start, self.traces[-1].cycle))
            for regime, start, end in runs:
                if start == end:
                    lines.append(f"  Cycle {start}: {regime}")
                else:
                    lines.append(f"  Cycles {start}-{end}: {regime}")
        else:
            lines.append("*No trace data.*")
        lines.append("")

        # -- Top regret cycles --
        lines.append("## Top Regret Cycles\n")
        regret_cycles = [
            (t.cycle, t.regret_score, t.active_regime,
             t.bypass_activated, t.overlay_veto_events)
            for t in self.traces if t.regret_score > 0
        ]
        regret_cycles.sort(key=lambda x: -x[1])
        top5 = regret_cycles[:5]
        if top5:
            lines.append("| Cycle | Regret | Regime | Events |")
            lines.append("|-------|--------|--------|--------|")
            for cycle, regret, regime, bp, vetoes in top5:
                events = []
                if bp:
                    events.append(f"bypass:{bp.get('name', '?')}")
                if vetoes:
                    events.append(f"{len(vetoes)} veto(s)")
                event_str = ", ".join(events) if events else "—"
                lines.append(
                    f"| {cycle} | {regret:.4f} | {regime} | {event_str} |"
                )
        else:
            lines.append("*No regret recorded.*")
        lines.append("")

        # -- Bypass breakdown --
        bp_counts = summary.get("bypass_counts", {})
        lines.append("## Bypass Events\n")
        if bp_counts:
            for name, count in sorted(bp_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {name}: {count}")
        else:
            lines.append("*No bypasses fired.*")
        lines.append("")

        # -- Veto breakdown --
        lines.append("## Veto Events\n")
        if summary.get("total_veto_events", 0) > 0:
            veto_by_type: dict[str, int] = {}
            for t in self.traces:
                for v in (t.overlay_veto_events or []):
                    vtype = v.get("overlay_type", "unknown")
                    veto_by_type[vtype] = veto_by_type.get(vtype, 0) + 1
            for vtype, count in sorted(veto_by_type.items(), key=lambda x: -x[1]):
                lines.append(f"  {vtype}: {count}")
        else:
            lines.append("*No vetoes fired.*")
        lines.append("")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
