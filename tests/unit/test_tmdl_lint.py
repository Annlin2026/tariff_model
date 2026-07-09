"""Unit tests for tmdl_lint summarizeBy rules."""

from __future__ import annotations

from pathlib import Path

from scripts.tmdl_lint import LintViolation, lint_tmdl_folder, lint_tmdl_text


def test_summarize_by_sum_on_pct_column_fails() -> None:
    tmdl = """\
table fact_market_foo
    column share_pct
        dataType: double
        summarizeBy: sum
"""
    violations = lint_tmdl_text(tmdl, file_path="x.tmdl")
    assert any(
        v.rule == "summarizeBy-none-on-pct" for v in violations
    ), f"expected violation; got {violations}"


def test_summarize_by_none_on_pct_column_passes() -> None:
    tmdl = """\
table fact_market_foo
    column share_pct
        dataType: double
        summarizeBy: none
"""
    assert lint_tmdl_text(tmdl, file_path="x.tmdl") == []


def test_summarize_by_sum_on_tariff_rate_fails() -> None:
    tmdl = """\
table fact_tariff_rate
    column avg_rate_pct
        dataType: double
        summarizeBy: sum
"""
    violations = lint_tmdl_text(tmdl, file_path="x.tmdl")
    assert any(
        v.rule == "summarizeBy-none-on-tariff" for v in violations
    )


def test_folder_scan_returns_violations(tmp_path: Path) -> None:
    folder = tmp_path / "definition" / "tables"
    folder.mkdir(parents=True)
    (folder / "fact.tmdl").write_text(
        "table fact_market_x\n    column share_pct\n        summarizeBy: average\n",
        encoding="utf-8",
    )
    violations = lint_tmdl_folder(tmp_path / "definition")
    assert len(violations) == 1
    assert violations[0].rule == "summarizeBy-none-on-pct"
    assert isinstance(violations[0], LintViolation)
