"""Tests for maelstrom_runtime.stressors — piecewise-linear stressor field S(t)."""
from __future__ import annotations

import json

import pytest

from maelstrom.spec import MaelstromSpec
from maelstrom.stressors import (
    compute_stressor_vector,
    interpolate_keyframes,
    stressor_dict,
)


# ── interpolate_keyframes ─────────────────────────────────────────────────


class TestInterpolateKeyframes:
    def test_empty_keyframes_returns_zero(self):
        assert interpolate_keyframes([], 5.0) == 0.0

    def test_before_first_keyframe(self):
        """t before the first keyframe should return the first value."""
        kf = [[10, 0.5], [20, 1.0]]
        assert interpolate_keyframes(kf, 0.0) == 0.5
        assert interpolate_keyframes(kf, 5.0) == 0.5

    def test_after_last_keyframe(self):
        """t after the last keyframe should return the last value."""
        kf = [[10, 0.5], [20, 1.0]]
        assert interpolate_keyframes(kf, 25.0) == 1.0
        assert interpolate_keyframes(kf, 100.0) == 1.0

    def test_at_exact_keyframe(self):
        """t exactly at a keyframe should return that keyframe's value."""
        kf = [[0, 0.2], [10, 0.8], [20, 0.4]]
        assert interpolate_keyframes(kf, 0.0) == 0.2
        assert interpolate_keyframes(kf, 10.0) == 0.8
        assert interpolate_keyframes(kf, 20.0) == 0.4

    def test_midpoint_interpolation(self):
        """Halfway between two keyframes should yield the average value."""
        kf = [[0, 0.0], [10, 1.0]]
        assert interpolate_keyframes(kf, 5.0) == pytest.approx(0.5)

    def test_quarter_interpolation(self):
        kf = [[0, 0.0], [10, 1.0]]
        assert interpolate_keyframes(kf, 2.5) == pytest.approx(0.25)

    def test_three_quarter_interpolation(self):
        kf = [[0, 0.0], [10, 1.0]]
        assert interpolate_keyframes(kf, 7.5) == pytest.approx(0.75)

    def test_multi_segment(self):
        """Interpolation across multiple segments."""
        kf = [[0, 0.0], [10, 1.0], [20, 0.0]]
        # First segment midpoint
        assert interpolate_keyframes(kf, 5.0) == pytest.approx(0.5)
        # Second segment midpoint
        assert interpolate_keyframes(kf, 15.0) == pytest.approx(0.5)

    def test_single_keyframe(self):
        """A single keyframe always returns its value."""
        kf = [[5, 0.7]]
        assert interpolate_keyframes(kf, 0.0) == 0.7
        assert interpolate_keyframes(kf, 5.0) == 0.7
        assert interpolate_keyframes(kf, 100.0) == 0.7

    def test_coincident_keyframes(self):
        """Two keyframes at the same cycle — early-return picks first value."""
        kf = [[5, 0.3], [5, 0.9]]
        # t <= keyframes[0][0] triggers, so first value is returned
        assert interpolate_keyframes(kf, 5.0) == 0.3


# ── Fixture: minimal scenario spec ────────────────────────────────────────


SCENARIO = {
    "name": "stressor_test",
    "total_cycles": 100,
    "seed": 42,
    "stressor_names": ["threat", "cost", "time_pressure"],
    "stressor_schedule": {
        "threat": [[0, 0.2], [50, 0.8], [100, 0.4]],
        "cost": [[0, 0.1], [100, 0.9]],
        "time_pressure": [[0, 0.5]],
    },
    "transitions": [],
    "regimes": [
        {"name": "survival", "w": [0.8, 0.1, 0.1], "u": [1.0, 0.0, 0.0]},
    ],
    "overlays": [],
    "bypasses": [],
}


@pytest.fixture
def spec(tmp_path):
    p = tmp_path / "scenario.json"
    p.write_text(json.dumps(SCENARIO), encoding="utf-8")
    return MaelstromSpec.from_json(p)


# ── compute_stressor_vector ───────────────────────────────────────────────


class TestComputeStressorVector:
    def test_at_cycle_zero(self, spec):
        vec = compute_stressor_vector(spec, 0)
        assert vec == pytest.approx([0.2, 0.1, 0.5])

    def test_at_final_cycle(self, spec):
        vec = compute_stressor_vector(spec, 100)
        assert vec == pytest.approx([0.4, 0.9, 0.5])

    def test_midpoint_interpolation(self, spec):
        vec = compute_stressor_vector(spec, 25)
        # threat: 0.2 + 25/50 * (0.8 - 0.2) = 0.2 + 0.3 = 0.5
        # cost: 0.1 + 25/100 * (0.9 - 0.1) = 0.1 + 0.2 = 0.3
        # time_pressure: constant 0.5
        assert vec == pytest.approx([0.5, 0.3, 0.5])

    def test_vector_length_matches_stressor_names(self, spec):
        vec = compute_stressor_vector(spec, 10)
        assert len(vec) == len(spec.stressor_names)

    def test_clamped_to_zero_one(self, tmp_path):
        """Values exceeding [0,1] should be clamped."""
        scenario = {
            "name": "clamp_test",
            "total_cycles": 10,
            "seed": 1,
            "stressor_names": ["x"],
            "stressor_schedule": {
                "x": [[0, -0.5], [10, 1.5]],
            },
            "transitions": [],
            "regimes": [{"name": "peacetime", "w": [1.0], "u": [1.0]}],
            "overlays": [],
            "bypasses": [],
        }
        p = tmp_path / "clamp.json"
        p.write_text(json.dumps(scenario), encoding="utf-8")
        cspec = MaelstromSpec.from_json(p)

        # At cycle 0: raw = -0.5, clamped to 0.0
        vec0 = compute_stressor_vector(cspec, 0)
        assert vec0[0] == 0.0

        # At cycle 10: raw = 1.5, clamped to 1.0
        vec10 = compute_stressor_vector(cspec, 10)
        assert vec10[0] == 1.0

    def test_missing_stressor_defaults_to_zero(self, tmp_path):
        """A stressor name missing from the schedule should default to 0.0."""
        scenario = {
            "name": "missing_test",
            "total_cycles": 10,
            "seed": 1,
            "stressor_names": ["present", "absent"],
            "stressor_schedule": {
                "present": [[0, 0.5]],
                # "absent" intentionally missing from schedule
            },
            "transitions": [],
            "regimes": [{"name": "peacetime", "w": [1.0, 1.0], "u": [1.0, 1.0]}],
            "overlays": [],
            "bypasses": [],
        }
        p = tmp_path / "missing.json"
        p.write_text(json.dumps(scenario), encoding="utf-8")
        mspec = MaelstromSpec.from_json(p)

        vec = compute_stressor_vector(mspec, 5)
        assert vec[0] == pytest.approx(0.5)
        assert vec[1] == 0.0  # defaults to [[0, 0.0]]


# ── stressor_dict ─────────────────────────────────────────────────────────


class TestStressorDict:
    def test_returns_named_dict(self, spec):
        vec = compute_stressor_vector(spec, 0)
        d = stressor_dict(spec, vec)
        assert isinstance(d, dict)
        assert set(d.keys()) == {"threat", "cost", "time_pressure"}
        assert d["threat"] == pytest.approx(0.2)
        assert d["cost"] == pytest.approx(0.1)
        assert d["time_pressure"] == pytest.approx(0.5)

    def test_dict_matches_vector_order(self, spec):
        vec = [0.1, 0.2, 0.3]
        d = stressor_dict(spec, vec)
        assert d["threat"] == 0.1
        assert d["cost"] == 0.2
        assert d["time_pressure"] == 0.3
