"""Tests for CSV export from trace.jsonl."""
import csv
import json
from pathlib import Path

from maelstrom.export import export_csvs
from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec

from tests.conftest import make_minimal_spec


def _run_and_export(tmp_path: Path) -> tuple[dict, Path]:
    """Run a minimal simulation and export CSVs."""
    spec_dict = make_minimal_spec()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec_dict))
    spec = MaelstromSpec.from_json(spec_path)
    out = tmp_path / "out"
    runtime = MaelstromRuntime(spec, output_dir=out)
    summary = runtime.run()
    export_csvs(out / "trace.jsonl", out)
    return summary, out


class TestExportCSVs:
    def test_all_csvs_created(self, tmp_path):
        _, out = _run_and_export(tmp_path)
        for name in ["regimes.csv", "bypasses.csv", "vetoes.csv", "regret.csv"]:
            assert (out / name).exists(), f"{name} not found"

    def test_regimes_csv_row_count(self, tmp_path):
        summary, out = _run_and_export(tmp_path)
        with open(out / "regimes.csv") as f:
            rows = list(csv.reader(f))
        assert rows[0][0] == "cycle"  # header
        assert len(rows) == summary["total_cycles"] + 1  # header + data

    def test_regimes_csv_has_all_penalty_columns(self, tmp_path):
        _, out = _run_and_export(tmp_path)
        with open(out / "regimes.csv") as f:
            header = next(csv.reader(f))
        for r in ["survival", "legal", "moral", "economic", "epistemic", "peacetime"]:
            assert f"penalty_{r}" in header
            assert f"gradient_{r}" in header

    def test_regret_csv_row_count(self, tmp_path):
        summary, out = _run_and_export(tmp_path)
        with open(out / "regret.csv") as f:
            rows = list(csv.reader(f))
        assert len(rows) == summary["total_cycles"] + 1

    def test_bypasses_csv_header_only_when_no_bypasses(self, tmp_path):
        _, out = _run_and_export(tmp_path)
        with open(out / "bypasses.csv") as f:
            rows = list(csv.reader(f))
        # Minimal spec may or may not have bypasses — at minimum, header exists
        assert rows[0] == ["cycle", "bypass_name", "stressor_intensity", "regime", "skipped_phases"]

    def test_export_idempotent(self, tmp_path):
        """Running export twice produces identical files."""
        _, out = _run_and_export(tmp_path)
        first = (out / "regimes.csv").read_text()
        export_csvs(out / "trace.jsonl", out)
        second = (out / "regimes.csv").read_text()
        assert first == second
