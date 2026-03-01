"""Deterministic execution utilities.

All randomness is seeded and recorded. Provides deterministic tie-breaking
and state hashing for trace verification.
"""
from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Callable, Sequence, TypeVar

T = TypeVar("T")

REGIME_PRIORITY = ["survival", "legal", "moral", "economic", "epistemic", "peacetime"]


class DeterministicRNG:
    """Seeded RNG wrapper that records all draws for reproducibility."""

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.draw_count = 0

    def random(self) -> float:
        self.draw_count += 1
        return self.rng.random()

    def uniform(self, a: float, b: float) -> float:
        self.draw_count += 1
        return self.rng.uniform(a, b)

    def noise(self, amplitude: float = 0.05) -> float:
        """Small deterministic perturbation for tie-breaking."""
        return self.uniform(-amplitude, amplitude)

    def state_snapshot(self) -> dict:
        return {"seed": self.seed, "draw_count": self.draw_count}


def deterministic_argmax(
    items: Sequence[T],
    key_fn: Callable[[T], float],
    tiebreak_fn: Callable[[T], Any] | None = None,
) -> T | None:
    """Select item with maximum key, breaking ties deterministically."""
    if not items:
        return None
    decorated = []
    for item in items:
        primary = key_fn(item)
        secondary = tiebreak_fn(item) if tiebreak_fn else 0
        decorated.append((primary, secondary, item))
    decorated.sort(key=lambda x: (-x[0], x[1]))
    return decorated[0][2]


def hash_state(state_dict: dict) -> str:
    """Produce deterministic SHA-256 hash of a state dictionary."""
    serialized = json.dumps(state_dict, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
