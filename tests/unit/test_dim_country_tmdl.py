"""Structural checks for expanded dim_country.tmdl (P1 Iter 1).

Verifies: (a) all existing P3 columns preserved, (b) hierarchy block present,
(c) no duplicate lineageTags (enforced by tmdl_lint but double-checked here),
(d) summarizeBy: none everywhere.
"""

from __future__ import annotations

import re

import pytest

from tests.unit._tmdl_helpers import (
    column_exists,
    columns_with_summarize_by_none,
    extract_lineage_tags,
    load_tmdl,
)

P3_PRESERVED_COLUMNS = ("country_id", "country_name_zh", "area_id", "area_name")


@pytest.fixture(scope="module")
def tmdl_text() -> str:
    return load_tmdl("tables/dim_country.tmdl")


@pytest.mark.parametrize("col", P3_PRESERVED_COLUMNS)
def test_p3_columns_preserved(tmdl_text: str, col: str) -> None:
    assert column_exists(tmdl_text, col), (
        f"P3 column {col!r} missing — lineageTag block 001-005 must be preserved"
    )


def test_hierarchy_area_country_declared(tmdl_text: str) -> None:
    # TMDL syntax: "hierarchy <name>" block containing "level <level_name>" lines
    hier = re.search(r"^\s{4}hierarchy\s+area_country_hierarchy\b", tmdl_text, re.MULTILINE)
    assert hier is not None, "missing hierarchy area_country_hierarchy block"
    # Levels reference columns by name (not lineageTag)
    assert re.search(r"\blevel\s+area\b", tmdl_text), "hierarchy missing 'level area'"
    assert re.search(r"\blevel\s+country\b", tmdl_text), "hierarchy missing 'level country'"


def test_all_columns_summarize_by_none(tmdl_text: str) -> None:
    # Every `column <name>` block must have `summarizeBy: none`
    # (IDs + strings are non-additive)
    all_columns = {
        m.group(1)
        for m in re.finditer(r"^\s{4}column\s+(\w+)\b", tmdl_text, re.MULTILINE)
    }
    with_none = columns_with_summarize_by_none(tmdl_text)
    missing = all_columns - with_none
    assert not missing, f"columns missing summarizeBy: none: {sorted(missing)}"


def test_no_duplicate_lineage_tags_inside_file(tmdl_text: str) -> None:
    tags = extract_lineage_tags(tmdl_text)
    assert len(tags) == len(set(tags)), f"duplicate lineageTag in dim_country.tmdl: {tags}"
