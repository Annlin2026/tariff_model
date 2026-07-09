"""Rule coverage for tmdl_lint tariff extensions (P3 Iter 3)."""

from __future__ import annotations

from scripts.tmdl_lint import lint_tmdl_text


def _tariff_fact(extra_cols: str = "") -> str:
    base = """table fact_tariff_rate
    lineageTag: 20000000-0000-4000-8000-000000000001

    column avg_rate_pct
        summarizeBy: none
"""
    return base + extra_cols


def test_missing_grain_column_flagged():
    # fact_tariff_rate without txn_year/importer_code/etc. should be flagged.
    violations = lint_tmdl_text(_tariff_fact(), "fake/fact_tariff_rate.tmdl")
    rules = {v.rule for v in violations}
    assert "fact-tariff-rate-grain-columns" in rules


def test_all_grain_columns_present_no_violation():
    full = _tariff_fact(
        """    column txn_year
        summarizeBy: none
    column importer_code
        summarizeBy: none
    column exporter_code
        summarizeBy: none
    column hs_code
        summarizeBy: none
    column tariff_type
        summarizeBy: none
"""
    )
    violations = [v for v in lint_tmdl_text(full, "fake/fact_tariff_rate.tmdl")
                  if v.rule == "fact-tariff-rate-grain-columns"]
    assert violations == []


def test_duplicate_lineage_tag_in_folder(tmp_path):
    from scripts.tmdl_lint import lint_tmdl_folder

    (tmp_path / "a.tmdl").write_text(
        "table a\n    lineageTag: 00000000-0000-4000-8000-000000000001\n",
        encoding="utf-8",
    )
    (tmp_path / "b.tmdl").write_text(
        "table b\n    lineageTag: 00000000-0000-4000-8000-000000000001\n",
        encoding="utf-8",
    )
    violations = lint_tmdl_folder(tmp_path)
    rules = {v.rule for v in violations}
    assert "lineage-tag-unique" in rules
