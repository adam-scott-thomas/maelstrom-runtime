"""Tests for maelstrom_runtime.utils — deterministic execution utilities."""
from __future__ import annotations

import pytest

from maelstrom.utils import (
    DeterministicRNG,
    clamp,
    deterministic_argmax,
    hash_state,
    REGIME_PRIORITY,
)


# ── DeterministicRNG ──────────────────────────────────────────────────────


class TestDeterministicRNG:
    def test_same_seed_same_sequence(self):
        """Two RNGs with the same seed must produce identical sequences."""
        rng1 = DeterministicRNG(seed=42)
        rng2 = DeterministicRNG(seed=42)
        for _ in range(20):
            assert rng1.random() == rng2.random()

    def test_different_seed_different_sequence(self):
        """Different seeds should (overwhelmingly likely) differ."""
        rng1 = DeterministicRNG(seed=1)
        rng2 = DeterministicRNG(seed=2)
        values1 = [rng1.random() for _ in range(10)]
        values2 = [rng2.random() for _ in range(10)]
        assert values1 != values2

    def test_draw_count_increments(self):
        rng = DeterministicRNG(seed=0)
        assert rng.draw_count == 0
        rng.random()
        assert rng.draw_count == 1
        rng.uniform(0.0, 1.0)
        assert rng.draw_count == 2
        rng.noise()
        # noise calls uniform internally, which increments draw_count
        assert rng.draw_count == 3

    def test_noise_is_bounded(self):
        rng = DeterministicRNG(seed=99)
        for _ in range(200):
            v = rng.noise(amplitude=0.1)
            assert -0.1 <= v <= 0.1

    def test_noise_default_amplitude(self):
        rng = DeterministicRNG(seed=7)
        for _ in range(200):
            v = rng.noise()
            assert -0.05 <= v <= 0.05

    def test_state_snapshot(self):
        rng = DeterministicRNG(seed=123)
        snap = rng.state_snapshot()
        assert snap == {"seed": 123, "draw_count": 0}
        rng.random()
        rng.random()
        snap = rng.state_snapshot()
        assert snap == {"seed": 123, "draw_count": 2}

    def test_uniform_range(self):
        rng = DeterministicRNG(seed=55)
        for _ in range(100):
            v = rng.uniform(3.0, 5.0)
            assert 3.0 <= v <= 5.0


# ── clamp ─────────────────────────────────────────────────────────────────


class TestClamp:
    def test_within_range(self):
        assert clamp(0.5) == 0.5

    def test_below_lo(self):
        assert clamp(-1.0) == 0.0

    def test_above_hi(self):
        assert clamp(2.0) == 1.0

    def test_at_boundaries(self):
        assert clamp(0.0) == 0.0
        assert clamp(1.0) == 1.0

    def test_custom_bounds(self):
        assert clamp(5.0, lo=2.0, hi=8.0) == 5.0
        assert clamp(1.0, lo=2.0, hi=8.0) == 2.0
        assert clamp(10.0, lo=2.0, hi=8.0) == 8.0


# ── deterministic_argmax ─────────────────────────────────────────────────


class TestDeterministicArgmax:
    def test_picks_maximum(self):
        items = [1, 5, 3, 2]
        result = deterministic_argmax(items, key_fn=lambda x: float(x))
        assert result == 5

    def test_empty_returns_none(self):
        result = deterministic_argmax([], key_fn=lambda x: float(x))
        assert result is None

    def test_tiebreak_selects_lower_secondary(self):
        """When two items have equal primary keys, the one with the lower
        tiebreak value should be selected."""
        items = [("a", 10), ("b", 10), ("c", 5)]
        result = deterministic_argmax(
            items,
            key_fn=lambda x: float(x[1]),
            tiebreak_fn=lambda x: x[0],
        )
        # "a" < "b" so "a" wins
        assert result == ("a", 10)

    def test_single_item(self):
        result = deterministic_argmax([42], key_fn=lambda x: float(x))
        assert result == 42

    def test_negative_keys(self):
        items = [-5, -1, -3]
        result = deterministic_argmax(items, key_fn=lambda x: float(x))
        assert result == -1


# ── hash_state ────────────────────────────────────────────────────────────


class TestHashState:
    def test_deterministic(self):
        state = {"a": 1, "b": [2, 3]}
        h1 = hash_state(state)
        h2 = hash_state(state)
        assert h1 == h2

    def test_key_order_irrelevant(self):
        h1 = hash_state({"x": 1, "y": 2})
        h2 = hash_state({"y": 2, "x": 1})
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = hash_state({"a": 1})
        h2 = hash_state({"a": 2})
        assert h1 != h2

    def test_returns_hex_string(self):
        h = hash_state({"key": "value"})
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest


# ── REGIME_PRIORITY constant ──────────────────────────────────────────────


def test_regime_priority_order():
    assert REGIME_PRIORITY[0] == "survival"
    assert "peacetime" in REGIME_PRIORITY
    assert len(REGIME_PRIORITY) == 6
