"""Tests for basic regret computation."""
import pytest

from maelstrom.doctrine import DoctrineState, CounterfactualEntry


class TestRegretComputation:
    def test_zero_regret_when_best(self):
        ds = DoctrineState()
        ds.archive_proposals(
            [{"id": "p1", "phase": "execute", "scores": {}}],
            "not_selected", cycle=1,
            regime_value_fn=lambda p: 0.5,
        )
        regret = ds.compute_regret(0.8, cycle=1)
        assert regret == 0.0

    def test_positive_regret_when_worse(self):
        ds = DoctrineState()
        ds.archive_proposals(
            [{"id": "p1", "phase": "execute", "scores": {}}],
            "vetoed", cycle=1,
            regime_value_fn=lambda p: 0.9,
        )
        regret = ds.compute_regret(0.3, cycle=1)
        assert regret == pytest.approx(0.6)

    def test_no_counterfactuals_zero_regret(self):
        ds = DoctrineState()
        regret = ds.compute_regret(0.5, cycle=1)
        assert regret == 0.0

    def test_regret_history_accumulates(self):
        ds = DoctrineState()
        ds.compute_regret(0.5, cycle=1)
        ds.compute_regret(0.3, cycle=2)
        assert len(ds.regret_history) == 2

    def test_regret_summary(self):
        ds = DoctrineState()
        ds.regret_history = [0.0, 0.1, 0.2, 0.0, 0.3]
        s = ds.regret_summary()
        assert s["mean"] == pytest.approx(0.12)
        assert s["max"] == pytest.approx(0.3)
        assert s["cycles_with_regret"] == 3
