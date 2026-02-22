#!/usr/bin/env python3
"""Run the minimal demo scenario and export cycle results as JSON.

Usage:
    python scripts/export_demo_trace.py [output_path]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maelstrom import MaelstromRuntime, MaelstromSpec


def main():
    spec_path = Path(__file__).resolve().parent.parent / "examples" / "minimal_spec.json"
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_trace.json")

    spec = MaelstromSpec.from_json(spec_path)
    runtime = MaelstromRuntime(spec)
    summary = runtime.run()

    trace = {
        "summary": summary,
        "cycles": runtime.cycle_results,
    }

    output_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(f"Trace written to {output_path} ({len(runtime.cycle_results)} cycles)")


if __name__ == "__main__":
    main()
