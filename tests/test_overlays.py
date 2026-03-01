"""Tests for maelstrom_runtime.overlays — Identity and Coalition veto gates."""
from __future__ import annotations

import pytest

from maelstrom.spec import OverlaySpec
from maelstrom.overlays import (
    VetoEvent,
    apply_overlays,
    any_identity_veto,
    any_coalition_veto,
    coalition_drag_level,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


def _identity_overlay(threshold: float = 0.8) -> OverlaySpec:
    """Identity overlay: veto execute phase when moral_weight exceeds threshold."""
    return OverlaySpec(
        overlay_type="identity",
        stressor_thresholds={"moral_weight": threshold},
        affected_phases=["execute"],
        description="Block execution when moral weight is too high",
        logic="all",
    )


def _coalition_overlay(
    competition_thresh: float = 0.7,
    resource_decay_thresh: float = 0.6,
) -> OverlaySpec:
    """Coalition overlay: AND-gate on competition AND resource_decay."""
    return OverlaySpec(
        overlay_type="coalition",
        stressor_thresholds={
            "competition": competition_thresh,
            "resource_decay": resource_decay_thresh,
        },
        affected_phases=["select", "execute"],
        description="Block select/execute when competition AND resource_decay exceed thresholds",
        logic="all",
    )


def _make_proposals(phase: str, count: int = 2) -> list[dict]:
    return [{"id": f"{phase}_prop_{i}", "score": 0.5 + i * 0.1} for i in range(count)]


# ── VetoEvent ────────────────────────────────────────────────────────────


class TestVetoEvent:
    def test_to_dict(self):
        ve = VetoEvent(
            overlay_type="identity",
            description="test veto",
            phase="execute",
            proposal_id="p1",
            stressor_state={"moral_weight": 0.95},
            thresholds={"moral_weight": 0.8},
        )
        d = ve.to_dict()
        assert d["overlay_type"] == "identity"
        assert d["description"] == "test veto"
        assert d["phase"] == "execute"
        assert d["proposal_id"] == "p1"
        assert d["stressor_state"] == {"moral_weight": 0.95}
        assert d["thresholds"] == {"moral_weight": 0.8}


# ── Identity overlay ────────────────────────────────────────────────────


class TestIdentityOverlay:
    def test_veto_triggers_above_threshold(self):
        """When moral_weight exceeds the identity threshold, execute-phase proposals are vetoed."""
        overlay = _identity_overlay(threshold=0.8)
        stressor_map = {"moral_weight": 0.95}
        proposals = {
            "execute": _make_proposals("execute"),
            "perceive": _make_proposals("perceive"),
        }

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        # Execute phase should be empty (vetoed)
        assert filtered["execute"] == []
        # Perceive phase should be untouched
        assert len(filtered["perceive"]) == 2
        # One veto event per vetoed proposal
        assert len(veto_events) == 2
        assert all(v.overlay_type == "identity" for v in veto_events)
        assert all(v.phase == "execute" for v in veto_events)

    def test_no_veto_below_threshold(self):
        """When moral_weight is below the identity threshold, no veto occurs."""
        overlay = _identity_overlay(threshold=0.8)
        stressor_map = {"moral_weight": 0.5}
        proposals = {
            "execute": _make_proposals("execute"),
        }

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        # No veto — proposals pass through
        assert len(filtered["execute"]) == 2
        assert veto_events == []

    def test_no_veto_at_exact_threshold(self):
        """Veto condition is strict greater-than, not >=. Exact threshold should NOT veto."""
        overlay = _identity_overlay(threshold=0.8)
        stressor_map = {"moral_weight": 0.8}
        proposals = {"execute": _make_proposals("execute")}

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        assert len(filtered["execute"]) == 2
        assert veto_events == []


# ── Coalition overlay (AND-gate) ─────────────────────────────────────────


class TestCoalitionOverlay:
    def test_and_gate_both_above_vetoes(self):
        """When BOTH competition AND resource_decay exceed thresholds, veto fires."""
        overlay = _coalition_overlay(competition_thresh=0.7, resource_decay_thresh=0.6)
        stressor_map = {"competition": 0.9, "resource_decay": 0.8}
        proposals = {
            "select": _make_proposals("select"),
            "execute": _make_proposals("execute"),
        }

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        assert filtered["select"] == []
        assert filtered["execute"] == []
        # 2 proposals x 2 phases = 4 veto events
        assert len(veto_events) == 4
        assert all(v.overlay_type == "coalition" for v in veto_events)

    def test_and_gate_partial_no_veto(self):
        """When only ONE of the AND-gate stressors exceeds threshold, no veto."""
        overlay = _coalition_overlay(competition_thresh=0.7, resource_decay_thresh=0.6)
        # competition is above, but resource_decay is below
        stressor_map = {"competition": 0.9, "resource_decay": 0.3}
        proposals = {
            "select": _make_proposals("select"),
            "execute": _make_proposals("execute"),
        }

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        assert len(filtered["select"]) == 2
        assert len(filtered["execute"]) == 2
        assert veto_events == []

    def test_or_gate_single_stressor_vetoes(self):
        """With logic='any', a single stressor exceeding threshold triggers veto."""
        overlay = OverlaySpec(
            overlay_type="coalition",
            stressor_thresholds={"competition": 0.7, "resource_decay": 0.6},
            affected_phases=["select"],
            description="OR-gate coalition veto",
            logic="any",
        )
        # Only competition is above
        stressor_map = {"competition": 0.9, "resource_decay": 0.3}
        proposals = {"select": _make_proposals("select")}

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        assert filtered["select"] == []
        assert len(veto_events) == 2


# ── Helper functions ─────────────────────────────────────────────────────


class TestHelpers:
    def test_any_identity_veto_true(self):
        events = [
            VetoEvent("identity", "desc", "execute", "p1", {}, {}),
            VetoEvent("coalition", "desc", "select", "p2", {}, {}),
        ]
        assert any_identity_veto(events) is True

    def test_any_identity_veto_false(self):
        events = [
            VetoEvent("coalition", "desc", "select", "p1", {}, {}),
        ]
        assert any_identity_veto(events) is False

    def test_any_identity_veto_empty(self):
        assert any_identity_veto([]) is False

    def test_any_coalition_veto_true(self):
        events = [
            VetoEvent("coalition", "desc", "select", "p1", {}, {}),
        ]
        assert any_coalition_veto(events) is True

    def test_any_coalition_veto_false(self):
        events = [
            VetoEvent("identity", "desc", "execute", "p1", {}, {}),
        ]
        assert any_coalition_veto(events) is False

    def test_coalition_drag_level_zero(self):
        assert coalition_drag_level([]) == 0.0

    def test_coalition_drag_level_scales(self):
        events = [
            VetoEvent("coalition", "desc", "select", f"p{i}", {}, {})
            for i in range(5)
        ]
        assert coalition_drag_level(events) == pytest.approx(0.5)

    def test_coalition_drag_level_capped(self):
        events = [
            VetoEvent("coalition", "desc", "select", f"p{i}", {}, {})
            for i in range(15)
        ]
        assert coalition_drag_level(events) == 1.0

    def test_coalition_drag_ignores_identity(self):
        events = [
            VetoEvent("identity", "desc", "execute", "p1", {}, {}),
            VetoEvent("coalition", "desc", "select", "p2", {}, {}),
        ]
        assert coalition_drag_level(events) == pytest.approx(0.1)


# ── Edge cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_overlays(self):
        """No overlays means all proposals pass through."""
        proposals = {"execute": _make_proposals("execute")}
        filtered, veto_events = apply_overlays([], {}, proposals)
        assert len(filtered["execute"]) == 2
        assert veto_events == []

    def test_empty_proposals(self):
        """No proposals means empty result even if overlays would fire."""
        overlay = _identity_overlay(threshold=0.8)
        stressor_map = {"moral_weight": 0.95}
        filtered, veto_events = apply_overlays([overlay], stressor_map, {})
        assert filtered == {}
        assert veto_events == []

    def test_missing_stressor_defaults_to_zero(self):
        """If stressor not in stressor_map, it defaults to 0.0 (below any positive threshold)."""
        overlay = _identity_overlay(threshold=0.8)
        stressor_map = {}  # moral_weight not present
        proposals = {"execute": _make_proposals("execute")}

        filtered, veto_events = apply_overlays([overlay], stressor_map, proposals)

        assert len(filtered["execute"]) == 2
        assert veto_events == []

    def test_multiple_overlays_same_phase(self):
        """Multiple overlays can veto the same phase — each generates its own events."""
        identity = _identity_overlay(threshold=0.8)
        coalition = OverlaySpec(
            overlay_type="coalition",
            stressor_thresholds={"moral_weight": 0.7},
            affected_phases=["execute"],
            description="Coalition also blocks execute",
            logic="all",
        )
        stressor_map = {"moral_weight": 0.95}
        proposals = {"execute": [{"id": "p1"}]}

        filtered, veto_events = apply_overlays(
            [identity, coalition], stressor_map, proposals,
        )

        assert filtered["execute"] == []
        # 1 proposal x 2 overlays = 2 veto events
        assert len(veto_events) == 2
        types = {v.overlay_type for v in veto_events}
        assert types == {"identity", "coalition"}
