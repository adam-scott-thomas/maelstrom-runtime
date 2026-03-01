"""Tests for maelstrom_runtime.spec — scenario dataclasses and JSON loading."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from maelstrom.spec import (
    BypassSpec,
    MaelstromSpec,
    OverlaySpec,
    RegimeSpec,
    TransitionSpec,
)


# ── Fixture: minimal valid scenario JSON ──────────────────────────────────

MINIMAL_SCENARIO = {
    "name": "test_scenario",
    "total_cycles": 50,
    "seed": 42,
    "stressor_names": ["threat", "cost", "time_pressure"],
    "stressor_schedule": {
        "threat": [[0, 0.2], [25, 0.8]],
        "cost": [[0, 0.1]],
        "time_pressure": [[0, 0.5]],
    },
    "transitions": [
        {
            "source": "perceive",
            "target": "evaluate",
            "A": 0.9,
            "W": 0.3,
            "alpha": [0.1, 0.0, 0.05],
            "beta": [0.0, 0.2, 0.1],
        },
        {
            "source": "evaluate",
            "target": "act",
            "A": 0.85,
            "W": 0.5,
            "alpha": [0.2, 0.1, 0.0],
            "beta": [0.1, 0.1, 0.1],
        },
    ],
    "regimes": [
        {"name": "survival", "w": [0.8, 0.1, 0.1], "u": [1.0, 0.0, 0.0]},
        {"name": "peacetime", "w": [0.1, 0.4, 0.5], "u": [0.2, 0.3, 0.5]},
    ],
    "overlays": [
        {
            "overlay_type": "identity",
            "stressor_thresholds": {"threat": 0.9},
            "affected_phases": ["act"],
            "description": "Block action under extreme threat",
            "logic": "all",
        }
    ],
    "bypasses": [
        {
            "name": "emergency_shortcut",
            "source_phase": "perceive",
            "target_phase": "act",
            "collapsed_path": ["perceive", "act"],
            "eligible_regimes": ["survival"],
            "stressor_weights": {"threat": 0.9, "time_pressure": 0.8},
            "latency_budget": {"survival": 0.3, "peacetime": 0.7},
        },
        {
            "name": "routine_skip",
            "source_phase": "perceive",
            "target_phase": "act",
            "collapsed_path": ["perceive", "act"],
            "eligible_regimes": ["peacetime"],
            "stressor_weights": {"cost": 0.5},
            "latency_budget": {"peacetime": 1.0},
        },
    ],
    "gradient_window": 3,
    "regime_inertia": 0.15,
    "specialist_config": {"inspector_depth": 2},
}


@pytest.fixture
def scenario_path(tmp_path):
    """Write the minimal scenario to a temp JSON file and return its path."""
    p = tmp_path / "scenario.json"
    p.write_text(json.dumps(MINIMAL_SCENARIO), encoding="utf-8")
    return p


# ── Loading from JSON ─────────────────────────────────────────────────────


class TestFromJson:
    def test_loads_basic_fields(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert spec.name == "test_scenario"
        assert spec.total_cycles == 50
        assert spec.seed == 42
        assert spec.stressor_names == ["threat", "cost", "time_pressure"]

    def test_transitions_loaded(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert len(spec.transitions) == 2
        t0 = spec.transitions[0]
        assert isinstance(t0, TransitionSpec)
        assert t0.source == "perceive"
        assert t0.target == "evaluate"
        assert t0.A == 0.9
        assert t0.W == 0.3

    def test_regimes_loaded(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert len(spec.regimes) == 2
        assert spec.regimes[0].name == "survival"
        assert spec.regimes[0].w == [0.8, 0.1, 0.1]

    def test_overlays_loaded(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert len(spec.overlays) == 1
        o = spec.overlays[0]
        assert isinstance(o, OverlaySpec)
        assert o.overlay_type == "identity"
        assert o.logic == "all"

    def test_bypasses_loaded(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert len(spec.bypasses) == 2
        b = spec.bypasses[0]
        assert isinstance(b, BypassSpec)
        assert b.name == "emergency_shortcut"
        assert b.source_phase == "perceive"
        assert b.target_phase == "act"

    def test_optional_fields_defaults(self, tmp_path):
        """When optional fields are missing, defaults should apply."""
        minimal = {
            "name": "bare",
            "total_cycles": 10,
            "seed": 1,
            "stressor_names": ["s1"],
            "stressor_schedule": {"s1": [[0, 0.5]]},
            "transitions": [],
            "regimes": [{"name": "peacetime", "w": [1.0], "u": [1.0]}],
        }
        p = tmp_path / "bare.json"
        p.write_text(json.dumps(minimal), encoding="utf-8")
        spec = MaelstromSpec.from_json(p)
        assert spec.overlays == []
        assert spec.bypasses == []
        assert spec.gradient_window == 1
        assert spec.regime_inertia == 0.0
        assert spec.specialist_config == {}


# ── Bypass latency_budget (per-bypass, NOT global) ────────────────────────


class TestBypassLatencyBudget:
    def test_each_bypass_has_latency_budget(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        for b in spec.bypasses:
            assert hasattr(b, "latency_budget")
            assert isinstance(b.latency_budget, dict)

    def test_latency_budget_values(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        emergency = spec.bypasses[0]
        assert emergency.latency_budget == {"survival": 0.3, "peacetime": 0.7}
        routine = spec.bypasses[1]
        assert routine.latency_budget == {"peacetime": 1.0}

    def test_no_global_latency_budgets_on_spec(self, scenario_path):
        """MaelstromSpec must NOT have a global latency_budgets field."""
        spec = MaelstromSpec.from_json(scenario_path)
        assert not hasattr(spec, "latency_budgets")


# ── Helper methods ────────────────────────────────────────────────────────


class TestHelpers:
    def test_stressor_index(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        assert spec.stressor_index("threat") == 0
        assert spec.stressor_index("cost") == 1
        assert spec.stressor_index("time_pressure") == 2

    def test_stressor_index_unknown_raises(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        with pytest.raises(ValueError):
            spec.stressor_index("nonexistent")

    def test_regime_by_name(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        r = spec.regime_by_name("survival")
        assert r.name == "survival"
        assert r.w == [0.8, 0.1, 0.1]

    def test_regime_by_name_unknown_raises(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        with pytest.raises(KeyError):
            spec.regime_by_name("nonexistent")

    def test_get_transition_found(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        t = spec.get_transition("perceive", "evaluate")
        assert t is not None
        assert t.A == 0.9

    def test_get_transition_not_found(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        t = spec.get_transition("act", "perceive")
        assert t is None


# ── to_dict / roundtrip ──────────────────────────────────────────────────


class TestToDict:
    def test_to_dict_roundtrips(self, scenario_path, tmp_path):
        """Load from JSON, to_dict(), write, reload — should be equivalent."""
        spec1 = MaelstromSpec.from_json(scenario_path)
        d = spec1.to_dict()

        # Write the dict back to JSON
        roundtrip_path = tmp_path / "roundtrip.json"
        roundtrip_path.write_text(json.dumps(d), encoding="utf-8")

        spec2 = MaelstromSpec.from_json(roundtrip_path)

        assert spec2.name == spec1.name
        assert spec2.total_cycles == spec1.total_cycles
        assert spec2.seed == spec1.seed
        assert spec2.stressor_names == spec1.stressor_names
        assert len(spec2.transitions) == len(spec1.transitions)
        assert len(spec2.regimes) == len(spec1.regimes)
        assert len(spec2.overlays) == len(spec1.overlays)
        assert len(spec2.bypasses) == len(spec1.bypasses)
        assert spec2.gradient_window == spec1.gradient_window
        assert spec2.regime_inertia == spec1.regime_inertia

    def test_to_dict_bypass_has_latency_budget(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        d = spec.to_dict()
        for b in d["bypasses"]:
            assert "latency_budget" in b
            assert isinstance(b["latency_budget"], dict)

    def test_to_dict_no_global_latency_budgets(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        d = spec.to_dict()
        assert "latency_budgets" not in d

    def test_to_dict_structure(self, scenario_path):
        spec = MaelstromSpec.from_json(scenario_path)
        d = spec.to_dict()
        assert d["name"] == "test_scenario"
        assert "transitions" in d
        assert "regimes" in d
        assert "overlays" in d
        assert "bypasses" in d
