"""Structural checks for the three Tariff dim TMDL files.

We don't need a live model to assert these — just parse the raw .tmdl text.
Live-model DAX checks land in Iter 5+.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEF = REPO_ROOT / "semantic_model" / "itrade_tariff_model.SemanticModel" / "definition"
TABLES = DEF / "tables"


@pytest.mark.parametrize(
    "table_file,entity_name,schema_name",
    [
        ("dim_country.tmdl", "GOLD_DIM_COUNTRY", "comtrade_ralph_dev"),
        # dim_hs_code rebound 2026-04-22 to first-class GOLD_DIM_HS_CODE
        # (warehouse Phase F addendum delivered 6,885 rows — interim V_DIM_HS_CODE view deprecated).
        ("dim_hs_code.tmdl", "GOLD_DIM_HS_CODE", "comtrade_ralph_dev"),
        # dim_tariff_detail bound to V_DIM_TARIFF_DETAIL view (PBI-owned bridge
        # per warehouse agent P1.4 response 2026-04-22 — warehouse explicitly
        # declined to build first-class GOLD_DIM_TARIFF_DETAIL for Phase 1).
        # View derives 106 distinct TARIFF_TYPE rows from GOLD_FACT_TARIFF_DUTY_DETAILS.
        ("dim_tariff_detail.tmdl", "V_DIM_TARIFF_DETAIL", "comtrade_ralph_dev"),
    ],
)
def test_dim_table_exists_and_points_at_gold(table_file, entity_name, schema_name):
    path = TABLES / table_file
    assert path.exists(), f"{table_file} missing"
    text = path.read_text(encoding="utf-8")
    assert f"entityName: {entity_name}" in text, f"{table_file} must bind to {entity_name}"
    assert f"schemaName: {schema_name}" in text, f"{table_file} must bind to {schema_name}"
    assert "mode: directLake" in text, f"{table_file} must use Direct Lake"


def test_spike_minimal_removed():
    assert not (TABLES / "_spike_minimal.tmdl").exists(), (
        "_spike_minimal.tmdl should have been removed in P3 Iter 1"
    )
