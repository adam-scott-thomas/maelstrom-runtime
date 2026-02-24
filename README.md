# Maelstrom Runtime

This repository contains the reference implementation of the Maelstrom Runtime architecture. It demonstrates the deterministic 5-phase cognitive cycle, regime arbitration, legality deformation, bypass collapse, and regret-driven doctrine formation. Calibrated production configurations and specialist implementations are proprietary.

**v2.2.0** — Zero external dependencies. Python 3.12+ stdlib only.

## Quick Start

```bash
pip install -e .

# Run a demo scenario
python examples/demo_runner.py examples/minimal_spec.json

# Run tests
python -m pytest tests/ -q
```

## Architecture

Each simulation cycle executes five phases in sequence:

```
EVALUATE  →  GENERATE  →  SELECT  →  EXECUTE  →  REFLECT
                                                    ↓
                                              (next cycle)
```

### Regime Arbitration

Six regimes compete for control each cycle via gradient-based selection with asymmetric inertia:

| Regime    | Driver                | Character                           |
|-----------|-----------------------|-------------------------------------|
| Survival  | Threat pressure       | Crisis response, fast action        |
| Legal     | Institutional inertia | Compliance, procedural caution      |
| Moral     | Moral weight          | Conscience, identity-driven refusal |
| Economic  | Opportunity pressure  | Opportunistic, resource-capture     |
| Epistemic | Ambiguity             | Analysis paralysis, learning loops  |
| Peacetime | Default stability     | Low-stress baseline                 |

Selection: `r*(t) = argmax_r dP_r/dt` with hysteresis.

### Legality Deformation

Stressors warp transition admissibility and penalty weights:

```
A'_ij = A_ij - α·S(t)    (high stress can make transitions inadmissible)
W'_ij = W_ij + β·S(t)    (high stress increases transition cost)
```

### Bypass Collapse

Under high stress, five bypass paths collapse the deliberation loop:

| Bypass        | Path  | Trigger                            |
|---------------|-------|------------------------------------|
| Impulse       | E → X | Survival regime, high intensity    |
| Rumination    | E → R | Epistemic regime, high intensity   |
| Mania         | G → X | Economic regime, high intensity    |
| Guilt         | S → R | Moral/Legal regime, high intensity |
| Over-learning | R → G | Epistemic/Economic, high intensity |

### Doctrine Engine

Regret computation with counterfactual archive. Tracks bypassed, vetoed, and non-selected proposals. Doctrine candidates are logged but not auto-promoted in this edition.

## What's Included

- Deterministic cycle loop (structural, not calibrated)
- Regime inertia logic (generic)
- Legality deformation math (formula visible)
- Bypass path mapping (structural only)
- Regret calculation (single-cycle, no benchmark suite)
- Minimal test coverage proving determinism

## What's NOT Included

- Specialist scoring formulas
- Calibrated w/u vectors
- Full scenario suite
- Feedback rule engine thresholds
- Doctrine promotion evaluator
- Benchmark gating logic
- Production-grade API surface

## Project Layout

```
maelstrom/                Core engine
  types.py                Spec dataclasses, graph types, regime/overlay/bypass definitions
  runtime.py              Simplified _execute_cycle skeleton
  regimes.py              Hysteresis logic (no tuned params)
  legality.py             A' and W' deformation math
  bypasses.py             Collapse mapping (no calibrated thresholds)
  doctrine.py             Regret model interface (no promotion evaluator)
  overlays.py             Structural gate interface only
  stressors.py            Basic vector generation
  utils.py                Deterministic RNG, hashing, helpers
tests/                    Minimal test suite
examples/                 Demo scenario specs + runner
scripts/                  Merkle recomputation, trace export
docs/
  whitepaper.pdf          Full technical specification
  whitepaper.tex          LaTeX source
  diagrams/               Architecture diagrams (SVG)
  merkle/                 Integrity tree + OpenTimestamps proof
```

## Integrity Verification

```bash
python scripts/recompute_merkle.py
```

## Documentation

- [`docs/whitepaper.pdf`](docs/whitepaper.pdf) — Full technical specification
- [`CHANGELOG.md`](CHANGELOG.md) — Release history

## License

Proprietary — see [LICENSE](LICENSE)
