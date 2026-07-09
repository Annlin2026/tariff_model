# ADR 0007 — Tariff Grain and Non-Additive Aggregation Policy

Status: Accepted · Date: 2026-04-20 · Phase: P3 Iter 2

## Context
Gold `GOLD_FACT_TARIFF_RATE` aggregates raw 10-digit HS rates up to HS6 using
`AVG(MIN_RATE)`, `AVG(MAX_RATE)`, `AVG(PREFERENTIAL)`. Row-level values are
therefore already averages across 10-digit siblings; *further* aggregation in
the semantic model (e.g. `SUM`/`AVG` at report level) would produce
arithmetically meaningless numbers (avg-of-avgs, sum-of-percentages).

## Decision
1. Grain is `(TXN_YEAR, IMPORTER_CODE, EXPORTER_CODE, HS_CODE, TARIFF_TYPE)`.
   `HS_CODE` holds the HS6 value (Gold drops 10→6 via `LEFT(HS_CODE_10, 6)`).
2. All four rate columns (`min_rate_pct`, `max_rate_pct`, `avg_rate_pct`,
   `preferential_pct`) are `summarizeBy = none`. TMDL lint enforces this
   (`summarizeBy-none-on-tariff` + `summarizeBy-none-on-pct`).
3. DAX measures for reporting use `MIN`, `MAX`, `AVERAGE` at row-context level
   only. No SUM measure is exposed. See Iter 5.
4. Cross-grain ratios (e.g. "weighted rate by trade value") are **out of scope**
   for P3 — they require joining value facts (P2b+). A future weighted-rate
   measure will appear once `fact_market_*` lands.

## Consequences
- Users slicing tariff by year-only, country-only, or HS-only will see row-level
  MIN/MAX/AVG of the exposed grain subset — which is the correct semantic.
- Attempting `SUM(avg_rate_pct)` in DAX returns BLANK (summarizeBy=none).
  Iter 10 asserts this behaviour.
- If business requests a "total tariff rate" visual, **do not add a SUM
  measure** — push back to clarify which weighting scheme they want, then
  re-evaluate in P4 or a post-P3 iteration.
- **Storage convention — rates are stored as percent literals** (e.g. `5.00`
  means 5%), per Gold `GOLD_FACT_TARIFF_RATE` DDL (`DECIMAL(10,6)` with `%`
  semantics). TMDL measures therefore use `formatString: 0.00"%"` (literal
  percent sign, no auto-multiply), NOT `formatString: 0.00%` which would
  multiply by 100 and render `5.00` as `"500.00%"`. Iter 7's
  `min_rate_pct ∈ [0, 100]` range test corroborates this convention.
- **`Preferential Rate %` uses AVERAGE** (not MIN/MAX). Preferential tariffs
  are typically queried as "the rate", not as extremes; exposing only an
  AVERAGE measure prevents semantically-questionable Min/Max visuals. If a
  future stakeholder requests those, document rationale before adding.
