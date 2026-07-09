# ADR 0008 — Tariff Non-Additive Policy

Status: Accepted · Date: 2026-04-20 · Phase: P3 Iter 10

## Context
`fact_tariff_rate[min|max|avg|preferential]_rate_pct` represent bounded
percentages that are already pre-aggregated (10→6 HS) in Gold. Summing them in
a report would be semantically meaningless (sum of percentages > 100%) and
averaging them across different grain subsets (country × hs vs hs only) would
produce average-of-averages artefacts.

## Decision
1. All four rate columns carry `summarizeBy: none`. This removes them from the
   implicit-measures list — users cannot drag the column onto a visual and get
   a Power BI-chosen aggregate.
2. Only four measures ship: `Avg Tariff Rate %`, `Min Tariff Rate %`,
   `Max Tariff Rate %`, `Preferential Rate %`. Each uses the matching DAX
   aggregate over its source column.
3. `tmdl_lint.py:summarizeBy-none-on-tariff` and `summarizeBy-none-on-pct`
   fail the build on any regression.
4. Any request for a "weighted tariff" measure requires joining `fact_market_*`
   (trade value) and is deferred to P2b+.

## Consequences
- Business users cannot build ad-hoc visualisations that aggregate tariff rates
  incorrectly. This is a feature, not a limitation.
- If a stakeholder insists on a SUM measure, point to this ADR and ask them to
  specify the weighting scheme; open a new ADR rather than adding the measure.

## Enforcement
- CI: `scripts/tmdl_lint.py`
- Live-model: `tests/tariff/test_tariff_non_additive_enforcement.py`
