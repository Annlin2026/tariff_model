"""Structural checks for expanded dim_hs_code.tmdl (P1 Iter 2)."""

from __future__ import annotations

import re

import pytest

from tests.unit._tmdl_helpers import column_exists, extract_lineage_tags, load_tmdl

P3_PRESERVED = (
    "hs_code", "hs_code_zh", "hs_code_group", "industry_id", "industry_name",
)
P1_ADDED = ("hs2_code", "hs4_code")
# Issue #1 BUG-002 (2026-05-06): HS2 / HS4 zh names exposed for label visuals.
ISSUE1_BUG002_ADDED = (
    ("hs2_nm_zh", "HS2_NM_ZH"),
    ("hs4_nm_zh", "HS4_NM_ZH"),
)
# Issue #48 (2026-06-02): single-field slicer display "code - 中文名" for the
# 多國關稅比較 report. DirectLake can't host a DAX calc column, so the combined
# string is materialised at gold (GOLD_DIM_HS_CODE, warehouse repo
# alwaysmycute/myp#19) and surfaced here as sourceColumn HS_CODE_COMBINED.
ISSUE48_COMBINED_ADDED = (("hs_code_combined", "HS_CODE_COMBINED"),)


@pytest.fixture(scope="module")
def tmdl_text() -> str:
    return load_tmdl("tables/dim_hs_code.tmdl")


@pytest.mark.parametrize("col", P3_PRESERVED)
def test_p3_columns_preserved(tmdl_text: str, col: str) -> None:
    assert column_exists(tmdl_text, col), f"P3 column {col!r} missing"


@pytest.mark.parametrize("col,source", [("hs2_code", "HS2_CODE"), ("hs4_code", "HS4_CODE")])
def test_p1_columns_added(tmdl_text: str, col: str, source: str) -> None:
    assert column_exists(tmdl_text, col, source=source), (
        f"P1 column {col!r} missing or not mapped to sourceColumn {source}"
    )


@pytest.mark.parametrize("col,source", list(ISSUE1_BUG002_ADDED))
def test_issue1_bug002_zh_columns_added(tmdl_text: str, col: str, source: str) -> None:
    """Issue #1 BUG-002: HS2 and HS4 ZH name columns must be exposed."""
    assert column_exists(tmdl_text, col, source=source), (
        f"BUG-002 column {col!r} missing or not mapped to sourceColumn {source}"
    )


@pytest.mark.parametrize("col,source", list(ISSUE48_COMBINED_ADDED))
def test_issue48_combined_column_added(tmdl_text: str, col: str, source: str) -> None:
    """Issue #48: HS_CODE_COMBINED display column for the 多國關稅比較 HS slicer."""
    assert column_exists(tmdl_text, col, source=source), (
        f"#48 column {col!r} missing or not mapped to sourceColumn {source}"
    )


def test_hierarchy_hs_declared(tmdl_text: str) -> None:
    assert re.search(r"^\s{4}hierarchy\s+hs_code_hierarchy\b", tmdl_text, re.MULTILINE)
    assert re.search(r"\blevel\s+hs2\b", tmdl_text), "hierarchy missing level hs2"
    assert re.search(r"\blevel\s+hs4\b", tmdl_text), "hierarchy missing level hs4"
    assert re.search(r"\blevel\s+hs6\b", tmdl_text), "hierarchy missing level hs6"


def test_no_duplicate_lineage_tags(tmdl_text: str) -> None:
    tags = extract_lineage_tags(tmdl_text)
    assert len(tags) == len(set(tags)), f"duplicate lineageTag: {tags}"
