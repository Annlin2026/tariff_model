"""Live cross-model validation: itrade_tariff_model vs itrade_trade_model.

Runs identical DAX on the freshly split model (IH_DataTeam_Ann workspace) and
the original itrade_trade_model (canonical DEV workspace per spec .env.example)
via REST executeQueries, using the spec's FabricDAXClient constructed with a
user token (AzureCliCredential) because the KV SP has no role on the target
workspace. Every probe must match exactly — the split is a subset copy, not a
redesign.

Probes (kept ≤ 10 calls/min/user REST throttle):
  1. COUNTROWS(fact_tariff_rate)
  2. Avg/Min/Max/Preferential measures, model-wide
  3. Avg Tariff Rate % by txn_year
  4. Golden-CSV spot check: HS 800300 MFN avg by importer for exporter=US

Writes status/tariff_split_validation.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from azure.identity import AzureCliCredential

from scripts.fabric_dax_client import FabricDAXClient

REPO_ROOT = Path(__file__).resolve().parent.parent
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"

SPLIT_WS = "aa4e76f5-3e7a-4de2-a6d5-6ab0815cbfd8"  # IH_DataTeam_Ann
SPLIT_DS = "itrade_tariff_model"
ORIG_WS = "b20289d7-86a9-46f9-8603-60b58c69df07"  # spec DEV workspace
ORIG_DS = "itrade_trade_model"

PROBES: dict[str, str] = {
    "rowcount": 'EVALUATE ROW("n", COUNTROWS(fact_tariff_rate))',
    "measures_modelwide": (
        'EVALUATE ROW("avg", [Avg Tariff Rate %], "min", [Min Tariff Rate %], '
        '"max", [Max Tariff Rate %], "pref", [Preferential Rate %])'
    ),
    "avg_by_year": (
        "EVALUATE SUMMARIZECOLUMNS(dim_time_year[year], "
        '"avg", [Avg Tariff Rate %])'
    ),
    # Row-level slice: exporter=US(842, Comtrade code) HS 800300 — same slice
    # the golden CSV covers (tariff_us_800300_golden.csv); full column dump so
    # every row must match across models.
    "rowlevel_us_800300": (
        "EVALUATE SELECTCOLUMNS("
        "FILTER(fact_tariff_rate, "
        'fact_tariff_rate[hs_code] = "800300" '
        '&& fact_tariff_rate[exporter_code] = "842"), '
        '"year", fact_tariff_rate[txn_year], '
        '"importer", fact_tariff_rate[importer_code], '
        '"ttype", fact_tariff_rate[tariff_type], '
        '"avg", fact_tariff_rate[avg_rate_pct], '
        '"min", fact_tariff_rate[min_rate_pct], '
        '"max", fact_tariff_rate[max_rate_pct], '
        '"pref", fact_tariff_rate[preferential_pct])'
    ),
}


def _normalise(rows: list[dict]) -> list[tuple]:
    """Order-independent, key-name-independent row comparison.

    executeQueries prefixes column keys with the table name, so the same
    SUMMARIZECOLUMNS returns e.g. `dim_time_year[year]` from both models —
    keys match here, but sort by values to ignore row order. None sorts first.
    """
    return sorted(
        (tuple(r.values()) for r in rows),
        key=lambda t: tuple((v is not None, str(v)) for v in t),
    )


def _rows_equal(a: list[tuple], b: list[tuple], rel_tol: float = 1e-9) -> bool:
    """Exact match for non-floats; isclose for floats (Direct Lake segment
    ordering can flip the last bits of AVERAGE aggregations)."""
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b, strict=True):
        if len(ra) != len(rb):
            return False
        for va, vb in zip(ra, rb, strict=True):
            if isinstance(va, float) and isinstance(vb, float):
                if not math.isclose(va, vb, rel_tol=rel_tol, abs_tol=1e-9):
                    return False
            elif va != vb:
                return False
    return True


def main() -> None:
    token = AzureCliCredential().get_token(PBI_SCOPE).token
    split = FabricDAXClient(workspace_id=SPLIT_WS, dataset_name=SPLIT_DS, _token=token)
    orig = FabricDAXClient(workspace_id=ORIG_WS, dataset_name=ORIG_DS, _token=token)

    report: dict = {"split_model": SPLIT_DS, "orig_model": ORIG_DS, "probes": {}}
    all_match = True
    for name, dax in PROBES.items():
        s_rows = split.query(dax)
        o_rows = orig.query(dax)
        # empty-vs-empty is vacuous, not a pass — every probe must return data
        match = bool(s_rows) and _rows_equal(_normalise(s_rows), _normalise(o_rows))
        all_match &= match
        report["probes"][name] = {
            "match": match,
            "split_rows": len(s_rows),
            "orig_rows": len(o_rows),
            "split_sample": s_rows[:3],
            "orig_sample": o_rows[:3],
        }
        print(f"[{'OK' if match else 'MISMATCH'}] {name}: "
              f"split={len(s_rows)} rows, orig={len(o_rows)} rows")

    report["all_match"] = all_match
    out = REPO_ROOT / "status" / "tariff_split_validation.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"validation report → {out}")
    sys.exit(0 if all_match else 1)


if __name__ == "__main__":
    main()
