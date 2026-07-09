"""Implicit SUM should not be available on *_rate_pct columns.

With `summarizeBy=none`, attempting to visualise an implicit aggregate on
fact_tariff_rate[avg_rate_pct] in Power BI shows BLANK. The DAX equivalent is
that the only legal aggregation is the explicit measure we ship.
"""

from __future__ import annotations

from tests.tariff.conftest import requires_live_env


def test_avg_tariff_rate_pct_column_summarize_none_in_metadata(dax_query):
    requires_live_env()
    rows = dax_query(
        "EVALUATE FILTER("
        "SELECTCOLUMNS(INFO.COLUMNS(), \"t\", [TableID], \"n\", [ExplicitName], "
        "\"s\", [SummarizeBy]),"
        "[n] = \"avg_rate_pct\" || [n] = \"min_rate_pct\" || "
        "[n] = \"max_rate_pct\" || [n] = \"preferential_pct\")"
    )
    assert rows, "INFO.COLUMNS returned no rows for rate_pct columns"
    for r in rows:
        # SummarizeBy = 1 is 'none' in the TMSL numeric enum.
        assert r.get("[s]") == 1, (
            f"column {r.get('[n]')} has SummarizeBy={r.get('[s]')}; expected 1 (none)"
        )


def test_explicit_measure_returns_value(dax_query):
    requires_live_env()
    rows = dax_query("EVALUATE ROW(\"m\", [Avg Tariff Rate %])")
    assert rows[0].get("[m]") is not None
