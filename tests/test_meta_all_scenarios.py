"""Meta-test: structural invariants and schema validation for all 28 scenarios.

This module provides three layers of anti-regression protection:

1. **No-crash**: every scenario JSON loads, runs, and produces a summary.
2. **Schema stability**: every summary contains exactly the expected keys
   with the correct types.
3. **Behavioral invariants**: dominant regime matches an expected set and
   regime switches stay under a scenario-specific ceiling.

These invariants are parametrized so a single failure pinpoints which
scenario broke and why.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# -- Invariant definitions per scenario ------------------------------------
# Each entry: (expected_dominant_set, max_switches)
#   expected_dominant_set: the regime with the plurality of cycles must be
#   one of these.  max_switches: hard ceiling on regime_switches.

SCENARIO_INVARIANTS: dict[str, tuple[set[str], int]] = {
    # Existing 6
    "meridian_v0":           ({"peacetime"},                         8),
    "crucible_v0":           ({"peacetime", "moral", "epistemic"},  20),
    "slow_burn_v0":          ({"moral", "epistemic"},                8),
    "legal_trap_v0":         ({"legal"},                            15),
    "resource_collapse_v0":  ({"economic", "peacetime"},            25),
    "ambiguity_storm_v0":    ({"epistemic"},                         5),
    # Batch 1: Stress Shape
    "flashbang_v0":          ({"legal"},                             6),
    "oscillator_v0":         ({"survival", "peacetime"},            10),
    "double_peak_v0":        ({"legal"},                            10),
    "creeping_doom_v0":      ({"economic", "epistemic"},             5),
    "recovery_test_v0":      ({"legal"},                             5),
    # Batch 2: Regime Isolation
    "pure_survival_v0":      ({"survival"},                          0),
    "pure_moral_v0":         ({"moral"},                             0),
    "pure_economic_v0":      ({"economic"},                          0),
    "pure_legal_v0":         ({"legal"},                             0),
    "pure_epistemic_v0":     ({"epistemic"},                         0),
    "pure_peacetime_v0":     ({"peacetime"},                         0),
    # Batch 3: Adversarial + Bypass
    "identity_cage_v0":      ({"moral"},                             0),
    "coalition_gridlock_v0": ({"legal"},                              3),
    "governance_overreach_v0": ({"legal"},                           3),
    "impulse_storm_v0":      ({"survival"},                          0),
    "guilt_spiral_v0":       ({"epistemic", "legal"},               50),
    "over_learning_trap_v0": ({"epistemic"},                         0),
    # Batch 4: Advanced
    "black_swan_v0":         ({"peacetime", "economic", "epistemic"}, 12),
    "noise_field_v0":        ({"survival"},                           8),
    "distribution_shift_v0": ({"survival", "epistemic"},              4),
    "false_calm_v0":         ({"peacetime"},                          6),
    "constraint_collision_v0": ({"legal"},                            8),
}

# Expected summary schema: key -> expected type
SUMMARY_SCHEMA = {
    "spec_name": str,
    "total_cycles": int,
    "seed": int,
    "regime_distribution": dict,
    "regime_switches": int,
    "bypass_counts": dict,
    "total_bypass_events": int,
    "total_veto_events": int,
    "mean_regret": float,
    "max_regret": float,
    "doctrine_candidates_total": int,
}


def _run_scenario(name: str) -> dict:
    """Run a scenario by name and return its summary dict."""
    spec_path = EXAMPLES_DIR / f"{name}.json"
    spec = MaelstromSpec.from_json(spec_path)
    with tempfile.TemporaryDirectory() as td:
        runtime = MaelstromRuntime(spec, output_dir=Path(td))
        summary = runtime.run()
    return summary


# -- Discover all scenario JSON files -------------------------------------

def _discover_scenarios() -> list[str]:
    """Return sorted list of scenario names (without .json extension)."""
    return sorted(p.stem for p in EXAMPLES_DIR.glob("*_v0.json"))


ALL_SCENARIOS = _discover_scenarios()


# -- Parametrized tests ----------------------------------------------------

@pytest.fixture(scope="module", params=ALL_SCENARIOS)
def scenario_result(request):
    """Run each scenario once (module-scoped, parametrized)."""
    name = request.param
    summary = _run_scenario(name)
    return name, summary


class TestNocrash:
    """Every scenario loads, runs, and produces a non-empty summary."""

    def test_scenario_runs(self, scenario_result):
        name, summary = scenario_result
        assert summary is not None, f"{name} returned None summary"
        assert summary["total_cycles"] > 0, f"{name} ran 0 cycles"


class TestSchemaStability:
    """Every summary has the correct keys and value types."""

    def test_summary_keys_present(self, scenario_result):
        name, summary = scenario_result
        missing = set(SUMMARY_SCHEMA.keys()) - set(summary.keys())
        assert not missing, (
            f"{name} summary missing keys: {missing}"
        )

    def test_summary_value_types(self, scenario_result):
        name, summary = scenario_result
        for key, expected_type in SUMMARY_SCHEMA.items():
            if key in summary:
                actual = type(summary[key])
                assert isinstance(summary[key], expected_type), (
                    f"{name}: summary['{key}'] is {actual.__name__}, "
                    f"expected {expected_type.__name__}"
                )


class TestBehavioralInvariants:
    """Dominant regime and switch count stay within expected bounds."""

    def test_dominant_regime_matches_expected(self, scenario_result):
        name, summary = scenario_result
        if name not in SCENARIO_INVARIANTS:
            pytest.skip(f"No invariants defined for {name}")
        expected_set, _ = SCENARIO_INVARIANTS[name]
        dist = summary["regime_distribution"]
        if not dist:
            pytest.fail(f"{name} has empty regime_distribution")
        dominant = max(dist, key=dist.get)
        assert dominant in expected_set, (
            f"{name}: dominant regime '{dominant}' not in expected set "
            f"{expected_set}.  Distribution: {dist}"
        )

    def test_switches_under_threshold(self, scenario_result):
        name, summary = scenario_result
        if name not in SCENARIO_INVARIANTS:
            pytest.skip(f"No invariants defined for {name}")
        _, max_switches = SCENARIO_INVARIANTS[name]
        actual = summary["regime_switches"]
        assert actual <= max_switches, (
            f"{name}: {actual} regime switches exceeds ceiling of "
            f"{max_switches}"
        )
