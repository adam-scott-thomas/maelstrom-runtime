# Doctrine Store Schema

## Doctrine Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (e.g., `doctrine_001`) |
| `name` | string | Human-readable name (e.g., `reduce_oscillation_v1`) |
| `version` | string | Semver version of this doctrine |
| `description` | string | What this doctrine does |
| `trigger_conditions` | object | When this doctrine applies (metric thresholds) |
| `action_deltas` | object | Parameter adjustments to apply |
| `safety_constraints` | object | Bounds that must not be violated |
| `created_from_candidates` | string[] | Deterministic hashes of source candidates |

## Files

- `active.json` — Currently promoted doctrines. Applied to runs when enabled.
- `proposals.json` — Generated but not yet promoted. Awaiting evaluation.

## Promotion Rules

A proposal is promoted to active when:
1. It improves at least 1 primary metric (mean_regret, max_regret, switches)
2. It does not worsen any safety metric beyond 5% tolerance
3. It passes the full 28-scenario benchmark suite

## Example

```json
{
  "id": "doctrine_001",
  "name": "reduce_oscillation_v1",
  "version": "1.0.0",
  "description": "Increase inertia when oscillation is detected",
  "trigger_conditions": {"oscillation_count": {"min": 3}},
  "action_deltas": {"inertia_delta": 0.003},
  "safety_constraints": {"max_inertia": 0.05, "max_regret_increase": 0.02},
  "created_from_candidates": ["a1b2c3d4...", "e5f6g7h8..."]
}
```
