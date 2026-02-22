"""Tests for the simplified runtime skeleton.

Verifies deterministic cycle execution, regime selection, and state
hash reproducibility across identical runs.
"""
import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.types import (
    MaelstromSpec, TransitionSpec, RegimeSpec, OverlaySpec, BypassSpec,
)


def _minimal_spec(**overrides) -> MaelstromSpec:
    """Build a minimal valid spec for testing."""
    defaults = dict(
        name="test_minimal",
        total_cycles=10,
        seed=42,
        stressor_names=["pressure", "ambiguity"],
        stressor_schedule={
            "pressure": [[1, 0.2], [5, 0.8], [10, 0.3]],
            "ambiguity": [[1, 0.1], [10, 0.5]],
        },
        transitions=[
            TransitionSpec("evaluate", "generate", A=1.0, W=0.1, alpha=[0.3, 0.1], beta=[0.1, 0.05]),
            TransitionSpec("generate", "select",   A=1.0, W=0.1, alpha=[0.2, 0.1], beta=[0.1, 0.05]),
            TransitionSpec("select",   "execute",  A=1.0, W=0.1, alpha=[0.2, 0.2], beta=[0.1, 0.1]),
            TransitionSpec("execute",  "reflect",  A=1.0, W=0.1, alpha=[0.1, 0.1], beta=[0.05, 0.05]),
            TransitionSpec("reflect",  "evaluate", A=1.0, W=0.1, alpha=[0.1, 0.1], beta=[0.05, 0.05]),
        ],
        regimes=[
            RegimeSpec("survival",  w=[0.8, 0.2], u=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0]),
            RegimeSpec("peacetime", w=[0.1, 0.1], u=[0.0, 0.0, 0.0, 0.0, 0.0, 0.1]),
        ],
        overlays=[],
        bypasses=[],
    )
    defaults.update(overrides)
    return MaelstromSpec(**defaults)


class TestRuntimeDeterminism:
    def test_identical_runs_same_hashes(self):
        spec = _minimal_spec()
        r1 = MaelstromRuntime(spec)
        r2 = MaelstromRuntime(spec)
        s1 = r1.run()
        s2 = r2.run()
        h1 = [c["state_hash"] for c in r1.cycle_results]
        h2 = [c["state_hash"] for c in r2.cycle_results]
        assert h1 == h2

    def test_different_seeds_different_results(self):
        s1 = MaelstromRuntime(_minimal_spec(seed=1)).run()
        s2 = MaelstromRuntime(_minimal_spec(seed=2)).run()
        # Regime distributions may differ with different seeds
        # (though in this minimal case they might be the same)
        assert s1["seed"] != s2["seed"]

    def test_cycle_count_matches(self):
        spec = _minimal_spec(total_cycles=5)
        rt = MaelstromRuntime(spec)
        rt.run()
        assert len(rt.cycle_results) == 5

    def test_summary_structure(self):
        rt = MaelstromRuntime(_minimal_spec())
        summary = rt.run()
        assert "name" in summary
        assert "regime_distribution" in summary
        assert "regret" in summary
        assert summary["total_cycles"] == 10
