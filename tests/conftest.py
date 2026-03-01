"""Shared fixtures for Maelstrom Runtime tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def make_minimal_spec(overlays=None) -> dict:
    """Create a valid spec dict with 3 stressors, 10 transitions, 6 regimes,
    and 5 bypasses (each with per-bypass latency_budget dicts).

    Parameters
    ----------
    overlays : list[dict] | None
        Optional overlay definitions to inject.  Defaults to no overlays.

    Returns
    -------
    dict
        A JSON-serializable spec dict ready for ``MaelstromSpec.from_json``
        or direct construction.
    """
    stressor_names = ["time_pressure", "threat_level", "moral_weight"]

    stressor_schedule = {
        "time_pressure": [[1, 0.10], [25, 0.80], [50, 0.10]],
        "threat_level":  [[1, 0.05], [25, 0.70], [50, 0.05]],
        "moral_weight":  [[1, 0.30], [25, 0.60], [50, 0.30]],
    }

    # 5 canonical transitions + 5 bypass transitions = 10 total
    transitions = [
        # --- 5 canonical (evaluate->generate->select->execute->reflect->evaluate) ---
        {
            "source": "evaluate", "target": "generate",
            "A": 1.0, "W": 0.10,
            "alpha": [0.02, 0.01, 0.01],
            "beta":  [0.04, 0.02, 0.02],
        },
        {
            "source": "generate", "target": "select",
            "A": 1.0, "W": 0.10,
            "alpha": [0.02, 0.01, 0.02],
            "beta":  [0.03, 0.02, 0.03],
        },
        {
            "source": "select", "target": "execute",
            "A": 1.0, "W": 0.10,
            "alpha": [0.03, 0.02, 0.03],
            "beta":  [0.05, 0.03, 0.04],
        },
        {
            "source": "execute", "target": "reflect",
            "A": 1.0, "W": 0.10,
            "alpha": [0.01, 0.01, 0.01],
            "beta":  [0.02, 0.02, 0.02],
        },
        {
            "source": "reflect", "target": "evaluate",
            "A": 1.0, "W": 0.05,
            "alpha": [0.01, 0.00, 0.01],
            "beta":  [0.01, 0.01, 0.01],
        },
        # --- 5 bypass transitions ---
        {
            "source": "evaluate", "target": "execute",
            "A": 0.40, "W": 0.55,
            "alpha": [0.01, 0.01, 0.00],
            "beta":  [0.01, 0.01, 0.01],
        },
        {
            "source": "evaluate", "target": "reflect",
            "A": 0.35, "W": 0.60,
            "alpha": [0.00, 0.00, 0.01],
            "beta":  [0.01, 0.01, 0.01],
        },
        {
            "source": "generate", "target": "execute",
            "A": 0.40, "W": 0.50,
            "alpha": [0.01, 0.00, 0.00],
            "beta":  [0.01, 0.01, 0.01],
        },
        {
            "source": "select", "target": "reflect",
            "A": 0.35, "W": 0.55,
            "alpha": [0.00, 0.01, 0.01],
            "beta":  [0.01, 0.01, 0.02],
        },
        {
            "source": "reflect", "target": "generate",
            "A": 0.30, "W": 0.65,
            "alpha": [0.00, 0.00, 0.01],
            "beta":  [0.01, 0.01, 0.01],
        },
    ]

    # 6 regimes: survival, legal, moral, economic, epistemic, peacetime
    regimes = [
        {"name": "survival",  "w": [0.40, 0.40, 0.20], "u": [0.20, 0.10, 0.05, 0.05, 0.10, 0.02]},
        {"name": "legal",     "w": [0.10, 0.10, 0.80], "u": [0.30, 0.20, 0.15, 0.10, 0.05, 0.02]},
        {"name": "moral",     "w": [0.05, 0.15, 0.80], "u": [0.10, 0.30, 0.15, 0.10, 0.05, 0.02]},
        {"name": "economic",  "w": [0.20, 0.10, 0.70], "u": [0.05, 0.05, 0.10, 0.30, 0.10, 0.02]},
        {"name": "epistemic", "w": [0.10, 0.10, 0.80], "u": [0.05, 0.05, 0.05, 0.05, 0.20, 0.02]},
        {"name": "peacetime", "w": [0.10, 0.10, 0.80], "u": [0.05, 0.05, 0.05, 0.15, 0.10, 0.02]},
    ]

    latency_budget_all = {
        "survival": 0.30, "legal": 0.45, "moral": 0.40,
        "economic": 0.35, "epistemic": 0.40, "peacetime": 0.70,
    }

    bypasses = [
        {
            "name": "impulse",
            "source_phase": "evaluate",
            "target_phase": "execute",
            "collapsed_path": ["evaluate", "execute", "reflect"],
            "eligible_regimes": ["survival"],
            "stressor_weights": {"time_pressure": 0.5, "threat_level": 0.5},
            "latency_budget": dict(latency_budget_all),
        },
        {
            "name": "rumination",
            "source_phase": "evaluate",
            "target_phase": "reflect",
            "collapsed_path": ["evaluate", "reflect"],
            "eligible_regimes": ["epistemic"],
            "stressor_weights": {"time_pressure": 0.3, "threat_level": 0.3, "moral_weight": 0.4},
            "latency_budget": dict(latency_budget_all),
        },
        {
            "name": "mania",
            "source_phase": "generate",
            "target_phase": "execute",
            "collapsed_path": ["evaluate", "generate", "execute", "reflect"],
            "eligible_regimes": ["economic"],
            "stressor_weights": {"time_pressure": 0.4, "threat_level": 0.3, "moral_weight": 0.3},
            "latency_budget": dict(latency_budget_all),
        },
        {
            "name": "guilt",
            "source_phase": "select",
            "target_phase": "reflect",
            "collapsed_path": ["evaluate", "generate", "select", "reflect"],
            "eligible_regimes": ["moral", "legal"],
            "stressor_weights": {"moral_weight": 0.6, "time_pressure": 0.4},
            "latency_budget": dict(latency_budget_all),
        },
        {
            "name": "over_learning",
            "source_phase": "reflect",
            "target_phase": "generate",
            "collapsed_path": ["evaluate", "generate", "select", "execute", "reflect", "generate"],
            "eligible_regimes": ["epistemic", "economic"],
            "stressor_weights": {"time_pressure": 0.3, "threat_level": 0.3, "moral_weight": 0.4},
            "latency_budget": dict(latency_budget_all),
        },
    ]

    return {
        "name": "minimal_test",
        "total_cycles": 50,
        "seed": 42,
        "stressor_names": stressor_names,
        "stressor_schedule": stressor_schedule,
        "transitions": transitions,
        "regimes": regimes,
        "overlays": overlays if overlays is not None else [],
        "bypasses": bypasses,
        "gradient_window": 2,
        "regime_inertia": {"default": 0.005},
        "specialist_config": {},
    }


@pytest.fixture
def minimal_spec_dict():
    """Return a minimal spec dict with no overlays."""
    return make_minimal_spec()


@pytest.fixture
def minimal_spec(tmp_path):
    """Return a MaelstromSpec loaded from the minimal spec dict."""
    d = make_minimal_spec()
    p = tmp_path / "minimal.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return MaelstromSpec.from_json(p)


@pytest.fixture
def meridian_spec_path():
    """Return path to the meridian_v0.json example."""
    return EXAMPLES_DIR / "meridian_v0.json"


@pytest.fixture
def crucible_spec_path():
    """Return path to the crucible_v0.json example."""
    return EXAMPLES_DIR / "crucible_v0.json"
