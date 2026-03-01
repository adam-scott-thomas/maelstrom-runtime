"""Backward-compatibility re-exports.

Types are now defined in their respective modules (spec.py, regimes.py,
overlays.py, bypasses.py, legality.py, utils.py). This module re-exports
them so that existing code importing from maelstrom.types still works.
"""
from .spec import (
    TransitionSpec,
    RegimeSpec,
    OverlaySpec,
    BypassSpec,
    MaelstromSpec,
)
from .legality import DeformedTransition
from .regimes import ConstraintState, CONSTRAINT_NAMES
from .overlays import VetoEvent
from .bypasses import BypassEvent, CANONICAL_PHASES
from .utils import REGIME_PRIORITY

__all__ = [
    "TransitionSpec",
    "DeformedTransition",
    "RegimeSpec",
    "ConstraintState",
    "CONSTRAINT_NAMES",
    "REGIME_PRIORITY",
    "CANONICAL_PHASES",
    "OverlaySpec",
    "VetoEvent",
    "BypassSpec",
    "BypassEvent",
    "MaelstromSpec",
]
