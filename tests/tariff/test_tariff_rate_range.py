"""Every rate_pct in [0, 100]; min ≤ avg ≤ max.

Live-gated — SKIPs on dev Linux host.
"""

from __future__ import annotations

from tests.tariff.conftest import requires_live_env

OUT_OF_RANGE_QUERY = """
EVALUATE
SUMMARIZE(
    FILTER(
        fact_tariff_rate,
        fact_tariff_rate[min_rate_pct] < 0
            || fact_tariff_rate[min_rate_pct] > 100
            || fact_tariff_rate[max_rate_pct] < 0
            || fact_tariff_rate[max_rate_pct] > 100
            || fact_tariff_rate[avg_rate_pct] < fact_tariff_rate[min_rate_pct]
            || fact_tariff_rate[avg_rate_pct] > fact_tariff_rate[max_rate_pct]
    ),
    fact_tariff_rate[importer_code],
    fact_tariff_rate[exporter_code],
    fact_tariff_rate[hs_code],
    fact_tariff_rate[tariff_type]
)
"""


def test_no_rows_out_of_range(dax_query):
    requires_live_env()
    rows = dax_query(OUT_OF_RANGE_QUERY)
    assert rows == [], f"{len(rows)} rows out of range; first 5: {rows[:5]}"
