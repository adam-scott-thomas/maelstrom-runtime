"""CSV export — stdlib-only flat-file extraction from trace.jsonl.

Produces:
  regimes.csv   — one row per cycle (regime, penalties, gradients)
  bypasses.csv  — one row per bypass event (sparse)
  vetoes.csv    — one row per veto event (sparse)
  regret.csv    — one row per cycle (regret score, doctrine count)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REGIME_NAMES = ["survival", "legal", "moral", "economic", "epistemic", "peacetime"]


def export_csvs(trace_path: Path, output_dir: Path) -> list[Path]:
    """Read trace.jsonl and write 4 CSV files. Returns list of created paths."""
    traces = _load_traces(trace_path)
    if not traces:
        return []

    paths = [
        _write_regimes(traces, output_dir),
        _write_bypasses(traces, output_dir),
        _write_vetoes(traces, output_dir),
        _write_regret(traces, output_dir),
    ]
    return paths


def _load_traces(trace_path: Path) -> list[dict]:
    records = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_regimes(traces: list[dict], output_dir: Path) -> Path:
    path = output_dir / "regimes.csv"
    penalty_cols = [f"penalty_{r}" for r in REGIME_NAMES]
    gradient_cols = [f"gradient_{r}" for r in REGIME_NAMES]
    header = ["cycle", "active_regime"] + penalty_cols + gradient_cols + ["regime_changed"]

    prev_regime = None
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for t in traces:
            regime = t["active_regime"]
            changed = prev_regime is not None and regime != prev_regime
            row = [
                t["cycle"],
                regime,
                *[round(t["regime_penalties"].get(r, 0.0), 6) for r in REGIME_NAMES],
                *[round(t["regime_gradients"].get(r, 0.0), 6) for r in REGIME_NAMES],
                changed,
            ]
            writer.writerow(row)
            prev_regime = regime
    return path


def _write_bypasses(traces: list[dict], output_dir: Path) -> Path:
    path = output_dir / "bypasses.csv"
    header = ["cycle", "bypass_name", "stressor_intensity", "regime", "skipped_phases"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for t in traces:
            bp = t.get("bypass_activated")
            if bp:
                writer.writerow([
                    t["cycle"],
                    bp["name"],
                    bp.get("stressor_intensity", ""),
                    bp.get("regime", ""),
                    ";".join(bp.get("skipped_phases", [])),
                ])
    return path


def _write_vetoes(traces: list[dict], output_dir: Path) -> Path:
    path = output_dir / "vetoes.csv"
    header = ["cycle", "overlay_type", "phase", "proposal_id", "description"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for t in traces:
            for v in t.get("overlay_veto_events", []):
                writer.writerow([
                    t["cycle"],
                    v.get("overlay_type", ""),
                    v.get("phase", ""),
                    v.get("proposal_id", ""),
                    v.get("description", ""),
                ])
    return path


def _write_regret(traces: list[dict], output_dir: Path) -> Path:
    path = output_dir / "regret.csv"
    header = ["cycle", "regret_score", "doctrine_candidate_count"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for t in traces:
            writer.writerow([
                t["cycle"],
                round(t.get("regret_score", 0.0), 6),
                len(t.get("doctrine_candidates", [])),
            ])
    return path
