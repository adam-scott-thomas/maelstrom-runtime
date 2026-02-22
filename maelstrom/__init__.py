"""Maelstrom Runtime — deterministic cognitive architecture simulation.

Reference implementation of the Maelstrom 5-phase deliberation loop with
regime arbitration, legality deformation, bypass collapse, and regret-driven
doctrine formation. Calibrated production configurations and specialist
implementations are proprietary.
"""
from .runtime import MaelstromRuntime
from .types import MaelstromSpec

__all__ = ["MaelstromRuntime", "MaelstromSpec"]
__version__ = "2.2.0"
