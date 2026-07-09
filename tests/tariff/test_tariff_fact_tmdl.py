"""Structural checks for fact_tariff_rate.tmdl."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FACT = (REPO_ROOT / "semantic_model" / "itrade_tariff_model.SemanticModel"
        / "definition" / "tables" / "fact_tariff_rate.tmdl")


@pytest.fixture(scope="module")
def fact_text() -> str:
    assert FACT.exists(), "fact_tariff_rate.tmdl missing"
    return FACT.read_text(encoding="utf-8")


def test_binds_to_gold(fact_text):
    assert "entityName: GOLD_FACT_TARIFF_RATE" in fact_text
    assert "schemaName: comtrade_ralph_dev" in fact_text
    assert "mode: directLake" in fact_text


@pytest.mark.parametrize(
    "col",
    ["txn_year", "importer_code", "exporter_code", "hs_code", "tariff_type",
     "min_rate_pct", "max_rate_pct", "avg_rate_pct", "preferential_pct"],
)
def test_has_required_column(fact_text, col):
    assert f"column {col}" in fact_text


@pytest.mark.parametrize(
    "col",
    ["min_rate_pct", "max_rate_pct", "avg_rate_pct", "preferential_pct"],
)
def test_rate_columns_summarize_none(fact_text, col):
    idx = fact_text.index(f"column {col}")
    window = fact_text[idx:idx + 400]
    assert "summarizeBy: none" in window, f"{col} must be summarizeBy: none"
