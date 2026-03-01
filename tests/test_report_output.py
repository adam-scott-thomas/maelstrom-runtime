"""Tests for human-readable trace and run report output files.

Design principle: test for STRUCTURE and NUMERIC EVIDENCE, not vocabulary.
We look for patterns like "+0.084200" and "0.88 > 0.85", not keywords like
"gradient" or "threshold".  This means the prose can be reworded freely
without breaking tests.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from maelstrom.runtime import MaelstromRuntime
from maelstrom.spec import MaelstromSpec

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Structural patterns (prose-independent)
RE_SIGNED_FLOAT = re.compile(r"[+-]\d+\.\d{4,}")       # +0.084200 or -0.001234
RE_COMPARISON = re.compile(r"\d+\.\d+\s*>\s*\d+\.\d+")  # 0.88 > 0.85
RE_CYCLE_HEADER = re.compile(r"^## Cycle \d+", re.MULTILINE)
RE_REGIME_LINE = re.compile(r"\*\*Regime:\*\*\s+\w+")    # **Regime:** legal ...
RE_PATH_LINE = re.compile(r"\*\*Path:\*\*\s+\w+")        # **Path:** evaluate -> ...
RE_REGRET_FLOAT = re.compile(r"\*\*Regret:\*\*\s+\d+\.\d{4}")  # **Regret:** 0.1924
RE_TABLE_ROW = re.compile(r"^\|.*\|.*\|", re.MULTILINE)  # | X | Y |
RE_TIMELINE_RUN = re.compile(r"Cycles?\s+\d+")            # Cycle 1 or Cycles 1-14


@pytest.fixture(scope="module")
def meridian_output(tmp_path_factory):
    """Run meridian_v0 and return output dir with all generated files."""
    spec = MaelstromSpec.from_json(EXAMPLES_DIR / "meridian_v0.json")
    output_dir = tmp_path_factory.mktemp("meridian_report")
    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    summary = runtime.run()
    return {"summary": summary, "output_dir": output_dir}


@pytest.fixture(scope="module")
def crucible_output(tmp_path_factory):
    """Run crucible_v0 (has bypasses + vetoes) for richer trace testing."""
    spec = MaelstromSpec.from_json(EXAMPLES_DIR / "crucible_v0.json")
    output_dir = tmp_path_factory.mktemp("crucible_report")
    runtime = MaelstromRuntime(spec, output_dir=output_dir)
    summary = runtime.run()
    return {"summary": summary, "output_dir": output_dir}


# ── trace_human.md tests ─────────────────────────────────────────────


class TestHumanTrace:

    def test_file_exists(self, meridian_output):
        path = meridian_output["output_dir"] / "trace_human.md"
        assert path.exists()

    def test_has_cycle_headers(self, meridian_output):
        """Every cycle gets a ## Cycle N header."""
        text = (meridian_output["output_dir"] / "trace_human.md").read_text()
        headers = RE_CYCLE_HEADER.findall(text)
        assert len(headers) == 48, f"Expected 48 cycle headers, found {len(headers)}"

    def test_every_cycle_has_regime_and_path(self, meridian_output):
        """Every cycle block contains a **Regime:** and **Path:** line."""
        text = (meridian_output["output_dir"] / "trace_human.md").read_text()
        assert len(RE_REGIME_LINE.findall(text)) == 48
        assert len(RE_PATH_LINE.findall(text)) == 48

    def test_regime_switch_shows_numeric_gradient(self, meridian_output):
        """Switch cycles contain signed float gradient values (structure, not prose)."""
        text = (meridian_output["output_dir"] / "trace_human.md").read_text()
        # Meridian has 4 switches. Each switch line should contain signed floats.
        assert len(RE_SIGNED_FLOAT.findall(text)) >= 4, (
            "Expected at least 4 signed-float gradient values across switch cycles"
        )

    def test_bypass_shows_numeric_intensity(self, crucible_output):
        """Bypass lines contain a numeric intensity value."""
        text = (crucible_output["output_dir"] / "trace_human.md").read_text()
        # Crucible has 27 bypass events. Each should show intensity as a float.
        bypass_blocks = [b for b in text.split("## Cycle") if "**Bypass fired:**" in b]
        assert len(bypass_blocks) >= 1, "No bypass blocks found"
        for block in bypass_blocks:
            assert re.search(r"\d+\.\d{4}", block), (
                f"Bypass block missing numeric intensity: {block[:200]}"
            )

    def test_veto_shows_threshold_comparison(self, crucible_output):
        """Veto lines contain a numeric comparison like 0.88 > 0.85."""
        text = (crucible_output["output_dir"] / "trace_human.md").read_text()
        assert RE_COMPARISON.search(text), (
            "No threshold comparison (X.XX > Y.YY) found in veto lines"
        )

    def test_regret_shows_numeric_value(self, crucible_output):
        """Non-zero regret cycles contain **Regret:** followed by a float."""
        text = (crucible_output["output_dir"] / "trace_human.md").read_text()
        matches = RE_REGRET_FLOAT.findall(text)
        assert len(matches) >= 1, "No **Regret:** lines with numeric values found"

    def test_does_not_crash_on_any_scenario(self, tmp_path_factory):
        """Human trace generation is best-effort — must never crash."""
        for jf in sorted(EXAMPLES_DIR.glob("*_v0.json")):
            spec = MaelstromSpec.from_json(jf)
            od = tmp_path_factory.mktemp(jf.stem)
            runtime = MaelstromRuntime(spec, output_dir=od)
            runtime.run()  # must not raise
            assert (od / "trace_human.md").exists(), f"{jf.stem}: trace_human.md missing"


# ── report.md tests ──────────────────────────────────────────────────


class TestReport:

    def test_file_exists(self, meridian_output):
        path = meridian_output["output_dir"] / "report.md"
        assert path.exists()

    def test_has_scenario_name(self, meridian_output):
        text = (meridian_output["output_dir"] / "report.md").read_text()
        assert "Meridian" in text

    def test_has_summary_table_with_rows(self, meridian_output):
        """Report contains a markdown table with at least 5 data rows."""
        text = (meridian_output["output_dir"] / "report.md").read_text()
        table_rows = RE_TABLE_ROW.findall(text)
        # Header + separator + at least 5 data rows = 7+ matches
        assert len(table_rows) >= 7, (
            f"Expected >= 7 table rows, found {len(table_rows)}"
        )

    def test_has_regime_timeline(self, meridian_output):
        """Report includes a regime timeline with cycle ranges."""
        text = (meridian_output["output_dir"] / "report.md").read_text()
        assert RE_TIMELINE_RUN.search(text), (
            "No timeline entries (Cycle N or Cycles N-M) found"
        )

    def test_has_regret_section_with_numbers(self, crucible_output):
        """Report has a regret section containing numeric regret values."""
        text = (crucible_output["output_dir"] / "report.md").read_text()
        # Crucible has regret — report should have a table with float values
        regret_section = text.split("Regret")
        assert len(regret_section) >= 2, "No 'Regret' section header found"
        assert re.search(r"\d+\.\d{4}", regret_section[1]), (
            "Regret section has no numeric values"
        )

    def test_has_bypass_section(self, crucible_output):
        """Report has a bypass section with at least one count."""
        text = (crucible_output["output_dir"] / "report.md").read_text()
        # Look for "name: N" pattern in bypass section
        assert re.search(r"\w+:\s+\d+", text), (
            "No 'name: count' entries found in report"
        )

    def test_has_veto_section(self, crucible_output):
        """Report has a veto section with at least one count."""
        text = (crucible_output["output_dir"] / "report.md").read_text()
        # Crucible has 54 veto events
        assert re.search(r"(identity|coalition):\s+\d+", text), (
            "No veto type counts found in report"
        )

    def test_does_not_crash_on_any_scenario(self, tmp_path_factory):
        """Report generation is best-effort — must never crash."""
        for jf in sorted(EXAMPLES_DIR.glob("*_v0.json")):
            spec = MaelstromSpec.from_json(jf)
            od = tmp_path_factory.mktemp(f"report_{jf.stem}")
            runtime = MaelstromRuntime(spec, output_dir=od)
            runtime.run()
            assert (od / "report.md").exists(), f"{jf.stem}: report.md missing"
