"""Entry point: python -m maelstrom run <spec.json> [-o DIR] [--no-csv]"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .runtime import MaelstromRuntime
from .spec import MaelstromSpec


def _run(args):
    """Execute a simulation run."""
    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    spec = MaelstromSpec.from_json(spec_path)

    # Auto-generate timestamped output dir unless overridden
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        slug = spec.name.replace(" ", "_").lower()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output") / f"{slug}_{stamp}"

    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    summary = runtime.run()

    # CSV export (on by default)
    if not args.no_csv:
        from .export import export_csvs
        export_csvs(output_dir / "trace.jsonl", output_dir)

    # Clean summary
    dist = summary["regime_distribution"]
    total = sum(dist.values())
    regime_str = ", ".join(
        f"{r} {count * 100 // total}%"
        for r, count in sorted(dist.items(), key=lambda x: -x[1])
    )

    print(f"\nMaelstrom Runtime — {spec.name}")
    print(f"  Cycles: {spec.total_cycles}  |  Seed: {spec.seed}")
    print(f"  Regime: {regime_str}")
    print(f"  Switches: {summary['regime_switches']}  |  "
          f"Bypasses: {summary['total_bypass_events']}  |  "
          f"Vetoes: {summary['total_veto_events']}")
    print(f"  Regret: mean={summary['mean_regret']:.4f}, max={summary['max_regret']:.4f}")
    print(f"  Output: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Maelstrom Runtime — deterministic cognitive architecture simulation",
    )
    subparsers = parser.add_subparsers(dest="command")

    # `run` subcommand
    run_parser = subparsers.add_parser("run", help="Run a simulation")
    run_parser.add_argument("spec_file", help="Path to scenario spec JSON file")
    run_parser.add_argument("--output-dir", "-o", default=None,
                            help="Output directory (default: output/<name>_<timestamp>)")
    run_parser.add_argument("--no-csv", action="store_true",
                            help="Skip CSV export")

    args = parser.parse_args()

    # Backward compat: if no subcommand, treat first positional as spec_file
    if args.command is None:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            # Re-parse with spec_file as positional (legacy mode)
            legacy = argparse.ArgumentParser()
            legacy.add_argument("spec_file")
            legacy.add_argument("--output-dir", "-o", default=None)
            legacy.add_argument("--no-csv", action="store_true", default=False)
            args = legacy.parse_args()
            _run(args)
        else:
            parser.print_help()
            sys.exit(1)
    elif args.command == "run":
        _run(args)


if __name__ == "__main__":
    main()
