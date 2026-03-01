"""Identity and Coalition overlays — negative-constraint veto gates.

Whitepaper S3.3:
  Identity overlay: veto based on intolerable losses / non-negotiable commitments.
  Coalition overlay: veto from multi-party constraints.
  Neither provides goals or rewards — they define what CANNOT be done.
  Veto events are logged and influence doctrine formation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .spec import OverlaySpec


@dataclass
class VetoEvent:
    overlay_type: str       # "identity" | "coalition"
    description: str
    phase: str
    proposal_id: str
    stressor_state: dict[str, float]
    thresholds: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "overlay_type": self.overlay_type,
            "description": self.description,
            "phase": self.phase,
            "proposal_id": self.proposal_id,
            "stressor_state": self.stressor_state,
            "thresholds": self.thresholds,
        }


def _check_overlay_condition(
    overlay: OverlaySpec,
    stressor_map: dict[str, float],
) -> bool:
    """Return True if the overlay's veto condition is MET (proposals should be vetoed)."""
    results = []
    for sname, threshold in overlay.stressor_thresholds.items():
        val = stressor_map.get(sname, 0.0)
        results.append(val > threshold)

    if overlay.logic == "all":
        return all(results) and len(results) > 0
    elif overlay.logic == "any":
        return any(results)
    return False


def apply_overlays(
    overlays: list[OverlaySpec],
    stressor_map: dict[str, float],
    proposals_by_phase: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], list[VetoEvent]]:
    """Filter proposals through overlay veto gates.

    Returns (filtered_proposals_by_phase, veto_events).
    Proposals in vetoed phases are removed; veto events are recorded.
    """
    veto_events: list[VetoEvent] = []
    filtered: dict[str, list[dict[str, Any]]] = {}

    # Determine which phases are currently vetoed
    vetoed_phases: dict[str, list[OverlaySpec]] = {}
    for overlay in overlays:
        if _check_overlay_condition(overlay, stressor_map):
            for phase in overlay.affected_phases:
                vetoed_phases.setdefault(phase, []).append(overlay)

    for phase, proposals in proposals_by_phase.items():
        if phase in vetoed_phases:
            # All proposals in this phase are vetoed
            kept: list[dict[str, Any]] = []
            for prop in proposals:
                for overlay in vetoed_phases[phase]:
                    veto_events.append(VetoEvent(
                        overlay_type=overlay.overlay_type,
                        description=overlay.description,
                        phase=phase,
                        proposal_id=prop["id"],
                        stressor_state={
                            s: stressor_map.get(s, 0.0)
                            for s in overlay.stressor_thresholds
                        },
                        thresholds=overlay.stressor_thresholds,
                    ))
            filtered[phase] = kept  # empty — all vetoed
        else:
            filtered[phase] = list(proposals)

    return filtered, veto_events


def any_identity_veto(veto_events: list[VetoEvent]) -> bool:
    return any(v.overlay_type == "identity" for v in veto_events)


def any_coalition_veto(veto_events: list[VetoEvent]) -> bool:
    return any(v.overlay_type == "coalition" for v in veto_events)


def coalition_drag_level(veto_events: list[VetoEvent]) -> float:
    """Coalition drag = count of coalition veto events * 0.1, capped at 1.0."""
    count = sum(1 for v in veto_events if v.overlay_type == "coalition")
    return min(count * 0.1, 1.0)
