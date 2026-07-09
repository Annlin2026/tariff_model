"""Structural checks for dim_time_year.tmdl (P1 Iter 4)."""

from __future__ import annotations

import re

import pytest

from tests.unit._tmdl_helpers import (
    SEMANTIC_MODEL_DIR,
    column_exists,
    extract_lineage_tags,
    load_tmdl,
)

TMDL_RELPATH = "tables/dim_time_year.tmdl"
TMDL_PATH = SEMANTIC_MODEL_DIR / TMDL_RELPATH


@pytest.fixture(scope="module")
def tmdl_text() -> str:
    assert TMDL_PATH.exists()
    return load_tmdl(TMDL_RELPATH)


def test_year_key_column(tmdl_text: str) -> None:
    assert column_exists(tmdl_text, "year")
    block = re.search(r"^\s{4}column\s+year\b(?:\n\s{8,}.*)+", tmdl_text, re.MULTILINE)
    assert block is not None
    assert "isKey" in block.group(0)
    assert "dataType: int64" in block.group(0)


def test_year_label_column(tmdl_text: str) -> None:
    assert column_exists(tmdl_text, "year_label")


def test_bound_to_gold(tmdl_text: str) -> None:
    # Warehouse agent delivered first-class GOLD_DIM_TIME_YEAR (7 rows) on
    # 2026-04-22 addendum Phase F; interim V_DIM_TIME_YEAR view is deprecated.
    assert "entityName: GOLD_DIM_TIME_YEAR" in tmdl_text
    assert "schemaName: comtrade_ralph_dev" in tmdl_text
    assert "mode: directLake" in tmdl_text


def test_year_summarize_by_none(tmdl_text: str) -> None:
    # Summing a year INT would be meaningless
    block = re.search(r"^\s{4}column\s+year\b(?:\n\s{8,}.*)+", tmdl_text, re.MULTILINE)
    assert block is not None
    assert "summarizeBy: none" in block.group(0)


def test_no_duplicate_lineage_tags(tmdl_text: str) -> None:
    tags = extract_lineage_tags(tmdl_text)
    assert len(tags) == len(set(tags))
