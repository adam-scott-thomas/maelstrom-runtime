#!/usr/bin/env python3
"""Run a Maelstrom scenario and print the summary.

Usage:
    python examples/demo_runner.py examples/minimal_spec.json
    python examples/demo_runner.py examples/meridian_v0.json
"""
import json
import sys
from pathlib import Path

# Add project root to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maelstrom import MaelstromRuntime, MaelstromSpec


def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_runner.py <spec.json>")
        sys.exit(1)

    spec_path = Path(sys.argv[1])
    spec = MaelstromSpec.from_json(spec_path)
    runtime = MaelstromRuntime(spec)
    summary = runtime.run()

    print(json.dumps(summary, indent=2))
    print(f"\nCompleted {summary['total_cycles']} cycles.")
    print(f"Regime distribution: {summary['regime_distribution']}")
    print(f"Mean regret: {summary['mean_regret']:.4f}")
    print(f"Max regret: {summary['max_regret']:.4f}")
    print(f"Switches: {summary['regime_switches']}")
    print(f"Bypasses: {summary['total_bypass_events']}")
    print(f"Vetoes: {summary['total_veto_events']}")


if __name__ == "__main__":
    main()
