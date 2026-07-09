import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FACT = (REPO_ROOT / "semantic_model" / "itrade_tariff_model.SemanticModel"
        / "definition" / "tables" / "fact_tariff_rate.tmdl")
TRANSLATIONS = REPO_ROOT / "semantic_model" / "translations" / "zh-TW.json"


def test_measures_declared():
    text = FACT.read_text(encoding="utf-8")
    for m in ("Avg Tariff Rate %", "Min Tariff Rate %",
              "Max Tariff Rate %", "Preferential Rate %"):
        assert f"measure '{m}'" in text or f'measure "{m}"' in text


@pytest.mark.parametrize(
    "col",
    ["avg_rate_pct", "min_rate_pct", "max_rate_pct", "preferential_pct"],
)
def test_no_sum_over_rate_column(col):
    text = FACT.read_text(encoding="utf-8")
    assert f"SUM(fact_tariff_rate[{col}])" not in text


def test_zh_translation_covers_tariff_terms():
    data = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    for zh in ("平均關稅率%", "最低關稅率%", "最高關稅率%", "優惠稅率%"):
        assert zh in data, f"missing zh header {zh!r}"
