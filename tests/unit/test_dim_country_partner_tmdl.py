"""Structural checks for dim_country_partner.tmdl (issue #1 BUG-001).

Role-playing dimension that points at the same warehouse table as
dim_country (GOLD_DIM_COUNTRY) but accepts the active relationship from
every fact_*[partner_code] / [source_code], so partner-axis visuals can
display country names without USERELATIONSHIP gymnastics.

Same column shape, hierarchy, and source as dim_country — these tests
guard against drift if dim_country evolves and this clone is forgotten.
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

PRESERVED_COLUMNS = ("country_id", "country_name_zh", "area_id", "area_name")


@pytest.fixture(scope="module")
def tmdl_text() -> str:
    return load_tmdl("tables/dim_country_partner.tmdl")


@pytest.fixture(scope="module")
def dim_country_tmdl_text() -> str:
    return load_tmdl("tables/dim_country.tmdl")


@pytest.mark.parametrize("col", PRESERVED_COLUMNS)
def test_partner_clone_column_present(tmdl_text: str, col: str) -> None:
    assert column_exists(tmdl_text, col), f"column {col!r} missing"


def test_partner_clone_columns_match_dim_country(
    tmdl_text: str, dim_country_tmdl_text: str
) -> None:
    """Both tables must expose the same logical column set — drift means
    Bar/Pivot visuals using dim_country_partner will silently lose fields."""
    own_cols = set(re.findall(r"^\s{4}column\s+(\w+)\b", tmdl_text, re.MULTILINE))
    base_cols = set(
        re.findall(r"^\s{4}column\s+(\w+)\b", dim_country_tmdl_text, re.MULTILINE)
    )
    assert own_cols == base_cols, (
        f"column drift: dim_country_partner has {own_cols} vs "
        f"dim_country {base_cols}"
    )


def test_hierarchy_area_country_declared(tmdl_text: str) -> None:
    assert re.search(
        r"^\s{4}hierarchy\s+area_country_hierarchy\b", tmdl_text, re.MULTILINE
    ), "missing hierarchy area_country_hierarchy"
    assert re.search(r"\blevel\s+area\b", tmdl_text)
    assert re.search(r"\blevel\s+country\b", tmdl_text)


def test_all_columns_summarize_by_none(tmdl_text: str) -> None:
    all_columns = {
        m.group(1)
        for m in re.finditer(r"^\s{4}column\s+(\w+)\b", tmdl_text, re.MULTILINE)
    }
    with_none = columns_with_summarize_by_none(tmdl_text)
    missing = all_columns - with_none
    assert not missing, f"columns missing summarizeBy: none: {sorted(missing)}"


def test_no_duplicate_lineage_tags_inside_file(tmdl_text: str) -> None:
    tags = extract_lineage_tags(tmdl_text)
    assert len(tags) == len(set(tags)), f"duplicate lineageTag: {tags}"


def test_partition_points_at_gold_dim_country(tmdl_text: str) -> None:
    """Direct Lake clone — must reuse the same warehouse entity as
    dim_country (no separate copy of the dimension table)."""
    assert "entityName: GOLD_DIM_COUNTRY" in tmdl_text
    assert "schemaName: comtrade_ralph_dev" in tmdl_text
    assert "mode: directLake" in tmdl_text


def test_lineage_tags_distinct_from_dim_country(
    tmdl_text: str, dim_country_tmdl_text: str
) -> None:
    """No lineageTag may collide with dim_country — TMDL requires globally
    unique tags."""
    own = set(extract_lineage_tags(tmdl_text))
    base = set(extract_lineage_tags(dim_country_tmdl_text))
    assert not (own & base), f"lineageTag collision: {own & base}"
