"""Identity and Coalition overlays -- negative-constraint veto gates.

Whitepaper S3.3:
  Identity overlay: veto based on intolerable losses / non-negotiable commitments.
  Coalition overlay: veto from multi-party constraints.
  Neither provides goals or rewards -- they define what CANNOT be done.

This module exposes the structural gate interface only. Calibrated
stressor thresholds are specified per-scenario.
"""
from __future__ import annotations

from typing import Any

from .types import OverlaySpec, VetoEvent


def _check_overlay_condition(
    overlay: OverlaySpec, stressor_map: dict[str, float],
) -> bool:
    """Return True if the overlay's veto condition is met."""
    results = [
        stressor_map.get(sname, 0.0) > threshold
        for sname, threshold in overlay.stressor_thresholds.items()
    ]
    if overlay.logic == "all":
        return all(results) and len(results) > 0
    if overlay.logic == "any":
        return any(results)
    return False


def apply_overlays(
    overlays: list[OverlaySpec],
    stressor_map: dict[str, float],
    proposals_by_phase: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], list[VetoEvent]]:
    """Filter proposals through overlay veto gates.

    Returns (filtered_proposals_by_phase, veto_events).
    """
    veto_events: list[VetoEvent] = []

    vetoed_phases: dict[str, list[OverlaySpec]] = {}
    for overlay in overlays:
        if _check_overlay_condition(overlay, stressor_map):
            for phase in overlay.affected_phases:
                vetoed_phases.setdefault(phase, []).append(overlay)

    filtered: dict[str, list[dict[str, Any]]] = {}
    for phase, proposals in proposals_by_phase.items():
        if phase in vetoed_phases:
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
            filtered[phase] = []
        else:
            filtered[phase] = list(proposals)

    return filtered, veto_events
