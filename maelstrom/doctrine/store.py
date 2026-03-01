"""Doctrine store — persistent named, versioned policy objects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_STORE_DIR = Path(__file__).parent


@dataclass
class Doctrine:
    """A named, versioned policy object."""
    id: str
    name: str
    version: str
    description: str
    trigger_conditions: dict[str, Any]
    action_deltas: dict[str, Any]
    safety_constraints: dict[str, Any]
    created_from_candidates: list[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "trigger_conditions": self.trigger_conditions,
            "action_deltas": self.action_deltas,
            "safety_constraints": self.safety_constraints,
            "created_from_candidates": self.created_from_candidates,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Doctrine:
        return cls(
            id=d["id"],
            name=d["name"],
            version=d["version"],
            description=d["description"],
            trigger_conditions=d["trigger_conditions"],
            action_deltas=d["action_deltas"],
            safety_constraints=d["safety_constraints"],
            created_from_candidates=d["created_from_candidates"],
        )


def load_active(path: Path | None = None) -> list[Doctrine]:
    """Load active (promoted) doctrines."""
    path = path or (_STORE_DIR / "active.json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [Doctrine.from_dict(d) for d in data.get("doctrines", [])]


def save_active(doctrines: list[Doctrine], path: Path | None = None) -> None:
    """Save active doctrines."""
    path = path or (_STORE_DIR / "active.json")
    data = {"doctrines": [d.to_dict() for d in doctrines], "version": "1.0.0"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_proposals(path: Path | None = None) -> list[Doctrine]:
    """Load proposed (not yet promoted) doctrines."""
    path = path or (_STORE_DIR / "proposals.json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [Doctrine.from_dict(d) for d in data.get("proposals", [])]


def save_proposals(proposals: list[Doctrine], path: Path | None = None) -> None:
    """Save doctrine proposals."""
    path = path or (_STORE_DIR / "proposals.json")
    data = {"proposals": [d.to_dict() for d in proposals], "version": "1.0.0"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
