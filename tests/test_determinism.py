"""Integration tests: deterministic execution guarantees.

The Maelstrom Runtime must produce byte-identical traces given the same
seed and spec.  These tests verify that the deterministic execution block
(Appendix A.3) is faithfully implemented.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _run_meridian(output_dir: Path, seed_override: int | None = None) -> dict:
    """Helper: load meridian_v0.json, optionally override seed, run, return summary."""
    spec_path = EXAMPLES_DIR / "meridian_v0.json"
    spec = MaelstromSpec.from_json(spec_path)
    if seed_override is not None:
        spec = MaelstromSpec(
            name=spec.name,
            total_cycles=spec.total_cycles,
            seed=seed_override,
            stressor_names=spec.stressor_names,
            stressor_schedule=spec.stressor_schedule,
            transitions=spec.transitions,
            regimes=spec.regimes,
            overlays=spec.overlays,
            bypasses=spec.bypasses,
            gradient_window=spec.gradient_window,
            regime_inertia=spec.regime_inertia,
            specialist_config=spec.specialist_config,
        )
    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    return runtime.run()


def _read_trace(output_dir: Path) -> list[dict]:
    """Read all cycle records from trace.jsonl."""
    records = []
    trace_path = output_dir / "trace.jsonl"
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


# -- Tests ------------------------------------------------------------------


def test_identical_traces_same_seed(tmp_path):
    """Two runs with same seed produce byte-identical traces."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"

    _run_meridian(dir_a)
    _run_meridian(dir_b)

    trace_a = (dir_a / "trace.jsonl").read_text(encoding="utf-8")
    trace_b = (dir_b / "trace.jsonl").read_text(encoding="utf-8")

    assert trace_a == trace_b, "Two runs with the same seed produced different traces"


def test_different_seeds_different_traces(tmp_path):
    """Different seeds produce different state hashes."""
    dir_a = tmp_path / "seed_42"
    dir_b = tmp_path / "seed_99"

    _run_meridian(dir_a, seed_override=42)
    _run_meridian(dir_b, seed_override=99)

    traces_a = _read_trace(dir_a)
    traces_b = _read_trace(dir_b)

    # Both runs should complete the same number of cycles
    assert len(traces_a) == len(traces_b)

    # At least one cycle should differ in state hash
    hashes_a = [t["state_hash"] for t in traces_a]
    hashes_b = [t["state_hash"] for t in traces_b]
    assert hashes_a != hashes_b, "Different seeds produced identical state hash sequences"


def test_state_hashes_evolve(tmp_path):
    """State hashes change across cycles."""
    dir_out = tmp_path / "evolve"
    _run_meridian(dir_out)

    traces = _read_trace(dir_out)
    hashes = [t["state_hash"] for t in traces]

    # All hashes should be valid hex strings
    for h in hashes:
        assert isinstance(h, str)
        assert len(h) == 64

    # There must be at least some distinct hashes (state evolves)
    unique_hashes = set(hashes)
    assert len(unique_hashes) > 1, "All cycles produced the same state hash"

    # In fact, every cycle should produce a unique hash (since cycle number
    # is part of the hashed state)
    assert len(unique_hashes) == len(hashes), \
        "Some cycles share state hashes despite different cycle numbers"


def test_rng_draw_count_deterministic(tmp_path):
    """RNG draw count identical across runs."""
    dir_a = tmp_path / "rng_a"
    dir_b = tmp_path / "rng_b"

    _run_meridian(dir_a)
    _run_meridian(dir_b)

    traces_a = _read_trace(dir_a)
    traces_b = _read_trace(dir_b)

    # The state_hash incorporates rng_draws, so identical hashes imply
    # identical draw counts.  But let's also check that the rng_draws
    # value in the hash input is consistent by verifying per-cycle hashes.
    for ta, tb in zip(traces_a, traces_b):
        assert ta["state_hash"] == tb["state_hash"], (
            f"Cycle {ta['cycle']}: state hashes diverged "
            f"({ta['state_hash'][:12]}... vs {tb['state_hash'][:12]}...)"
        )
