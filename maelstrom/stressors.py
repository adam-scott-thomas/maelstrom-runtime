"""Stressor field S(t) -- piecewise-linear interpolation from scenario schedule.

Whitepaper S4.1 / Appendix A.1:
  S(t) is a vector-valued time series with components S_k(t) in [0,1].
  Scenarios define piecewise-linear trajectories via keyframe schedules.
"""
from __future__ import annotations

from .types import MaelstromSpec
from .utils import clamp


def interpolate_keyframes(keyframes: list[list[float]], t: float) -> float:
    """Piecewise-linear interpolation over sorted (cycle, value) pairs."""
    if not keyframes:
        return 0.0
    if t <= keyframes[0][0]:
        return keyframes[0][1]
    if t >= keyframes[-1][0]:
        return keyframes[-1][1]
    for i in range(len(keyframes) - 1):
        c0, v0 = keyframes[i]
        c1, v1 = keyframes[i + 1]
        if c0 <= t <= c1:
            if c1 == c0:
                return v1
            frac = (t - c0) / (c1 - c0)
            return v0 + frac * (v1 - v0)
    return keyframes[-1][1]


def compute_stressor_vector(spec: MaelstromSpec, t: int) -> list[float]:
    """Return S(t) as a list aligned with spec.stressor_names."""
    return [
        clamp(interpolate_keyframes(
            spec.stressor_schedule.get(name, [[0, 0.0]]), float(t),
        ))
        for name in spec.stressor_names
    ]


def stressor_dict(spec: MaelstromSpec, vec: list[float]) -> dict[str, float]:
    """Convert stressor vector to a name-keyed dict."""
    return {name: vec[i] for i, name in enumerate(spec.stressor_names)}
