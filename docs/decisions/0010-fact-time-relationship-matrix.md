# ADR 0010 — Fact → Time-Dim Relationship Matrix

| Status | Date | Authors |
|---|---|---|
| Accepted | 2026-04-20 | P1 Iter 4 |

## Context

Spec §5.2 forbids a single merged `dim_date` m:m roll-up. Instead, two
independent time dims exist: `dim_time_year` (year grain, key=`year` INT64)
and `dim_time_month` (YYYYMM grain, key=`year_month` INT64).

Every fact table must therefore declare **exactly one** time relationship —
to year OR to month, not both, not neither. Mixing would produce ambiguous
filter context; omitting would make time slicers silent no-ops.

## Decision

| Fact (future, P2a-P4) | Grain | Time dim | Join key | Status |
|---|---|---|---|---|
| `fact_market_import_situation`    | annual          | `dim_time_year`  | `year`       | active (P2 Iter 3 2026-04-22) |
| `fact_market_import_indicators`        | annual | `dim_time_year` | `year` | **deferred** (C2 session 3 — TXN_YEAR varchar) |
| `fact_market_import_source_countries`  | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_import_demand_products`   | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_export_situation`         | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_export_product_details`   | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_industry_import`          | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_industry_source_countries` | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_industry_demand_products`  | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_product_global_import`            | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_product_global_import_sources`    | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_product_tw_export_products`       | annual | `dim_time_year` | `year` | active |
| `fact_product_tw_export_markets`        | annual | `dim_time_year` | `year` | active |
| `fact_product_tw_market_other_sources`  | annual | `dim_time_year` | `year` | active |
| `fact_product_export_situation`         | annual | `dim_time_year` | `year` | **active** (2026-06-08, #47/#59 — HS11 rebuild delivered; was BLOCKER 2026-04-22 → 2026-06-08) |
| `fact_industry_global_import`           | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_industry_import_source_countries` | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_industry_import_demand_products`  | annual | `dim_time_year` | `year` | active (P2 Iter 3 2026-04-22) |
| `fact_market_export_indicators` (P2-B Mart 1, CSV #10) | annual | `dim_time_year` | `txn_year` ← `year` | active (P2 Iter 5 2026-04-22) |
| `fact_market_export_industry` (P2-B Mart 2, CSV #13) | annual | `dim_time_year` | `txn_year` ← `year` | active (P2 Iter 6 2026-04-22) |
| `fact_market_export_industry_markets` (P2-B Mart 3, CSV #14) | annual | `dim_time_year` | `txn_year` ← `year` | active (P2 Iter 7 2026-04-22) |
| `fact_market_export_industry_products` (P2-B Mart 4, CSV #15) | annual | `dim_time_year` | `txn_year` ← `year` | active (P2 Iter 8 2026-04-22) |
| `fact_tariff_rate` (P3, existing) | annual          | `dim_time_year`  | `txn_year` ← `year` | active |
| `fact_monthly_totals` (hypothetical; only if P2+ adds a month page) | monthly | `dim_time_month` | `year_month` | hypothetical (not scheduled) |

Status legend: `active` = relationship wired on main via relationships.tmdl;
`hypothetical` = only materialises if a future scope change introduces it.
Six speculative "planned (P2a+)" placeholder rows (`fact_market_industry`,
`fact_market_product_detail`, `fact_country_*`, `fact_taiwan_*`) were
removed 2026-04-22 in the housekeeping window — none materialised under
those names; P2a-P2d delivered `fact_market_import_*` / `fact_product_*` /
`fact_industry_*` instead.

All facts currently specified are annual (see specs/gold/dimensional-model.md
§2.4 — `dim_date` mixes ANNUAL/MONTHLY but consumed marts are annual-only
through 2025). `dim_time_month` lands in P1 as a future-proofing artifact;
it has no active relationship until a monthly fact is introduced.

## Consequences

- P3 retrofit: `fact_tariff_rate.txn_year` (already int64) will gain a
  relationship to `dim_time_year.year` in P2a (not P1 — P1 Iter 5 only
  landed the live-gated validity test; the actual relationship wiring was
  deferred to P2a).
- When a new fact is added in P2a-P4, the author MUST update this ADR with
  a new row BEFORE the relationship is created. Skipping the ADR update is
  grounds for PR rejection.
- `dim_time_month` existing with no active relationship is intentional.
  Direct Lake framing costs for an unused dim are negligible (< 10 KB
  metadata). Removing it would mean re-adding it on zero notice when the
  first monthly page ships; the pre-provisioning cost is lower.
- Consumers MUST NOT create DAX calculated relationships between the two
  time dims (e.g., `year_month → year` bridging). If a report needs both
  grains, use two separate slicers, one per dim.

As of P2b Iter 1, two more rows are wired active on main: `fact_market_import_indicators` and `fact_market_import_source_countries`. Six P2b marts remain planned (Iter 2-4 will flip C4-C9 in batches).

As of P2b Iter 2, four P2b marts are wired active; four remain planned (Iter 3-4).

As of P2b Iter 3, six P2b marts wired; two remain (Iter 4: C8, C9).

P2b complete — all 8 market marts wired active. Two role-playing inactive relationships (C3 source, C8 source) present.

As of P2c Iter 1, three P2c product marts are wired active: `fact_product_global_import`, `fact_product_global_import_sources`, `fact_product_tw_export_products`. Three product marts remain planned (Iter 2: C13, C14, C15).

P2c complete — all 6 product marts wired active. Two role-playing inactive relationships (C11 source, C14 source) present. Cumulative active rows: 1 (C1) + 8 (P2b C2-C9) + 6 (P2c C10-C15) + 1 (fact_tariff_rate) = 16 active fact-time relationships on main.

As of P2d Iter 1, one P2d industry mart is wired active: `fact_industry_global_import`. Two industry marts remain planned (Iter 2: C17; Iter 3: C18).

As of P2d Iter 2, two P2d industry marts are wired active: C16 + C17. One industry mart remains planned (Iter 3: C18). One role-playing inactive relationship present (C17 source).

P2d complete — all 3 industry marts wired active. One role-playing inactive relationship (C17 source) present. Cumulative active rows: 1 (C1) + 8 (P2b C2-C9) + 6 (P2c C10-C15) + 3 (P2d C16-C18) + 1 (fact_tariff_rate) = 19 active fact-time relationships on main.

As of **Phase 2 Iter 3 (2026-04-22)**: warehouse delivered `TXN_YEAR_INT int` on 13 GOLD facts (Ask 1; verification: `status/2026-04-22_phase2_asks_verification.json`, 0 NULL / 0 mismatch / 值域 {2022, 2023, 2024, 2025}). PBI rebound `txn_year` column (string→int64, `TXN_YEAR`→`TXN_YEAR_INT`) on those 13 facts and added 13 `*_time` relationships to `dim_time_year.year`. All 13 matrix rows above flipped `deferred → active`. Remaining non-active rows: (a) `fact_market_import_indicators` still deferred — its source `GOLD_COMTRADE_MARKET_SHARE` was intentionally out of Ask 1 scope; pending a future ask; (b) `fact_product_export_situation` still BLOCKER under the C15 HS11 rebuild letter. 17 of 19 speccable fact-time relationships now active on `main`.

As of **Phase 2 Iter 5 (2026-04-22)**: new fact `fact_market_export_indicators` (P2-B Mart 1, CSV #10) added. Binds `GOLD_MARKET_EXPORT_INDICATORS` (TXN_YEAR_INT baked at source, flow='2', World-row share denominator). Grain (txn_year × reporter_code × partner_code), 3 relationships wired: reporter (active), partner (inactive role-playing), time (active). Cumulative active fact-time relationships on main: 18 = previous 17 + 1 (Mart 1). Matrix row added above.

As of **Phase 2 Iter 6-8 (2026-04-22)**: three more P2-B facts added, all binding BRIDGE-HS-chapter-fallback rebuilt marts:
- Iter 6: `fact_market_export_industry` (Mart 2, CSV #13). Grain (txn_year × reporter × industry). 3 rels: reporter (active), industry (active), time (active). No partner role-playing here.
- Iter 7: `fact_market_export_industry_markets` (Mart 3, CSV #14). Grain (txn_year × reporter × industry × partner). 4 rels: reporter (active), industry (active), partner (inactive role-playing), time (active).
- Iter 8: `fact_market_export_industry_products` (Mart 4, CSV #15). Grain (txn_year × reporter × industry × hs6). 4 rels: reporter (active), industry (active), hs6 (active to dim_hs_code), time (active).

Cumulative active fact-time relationships on main: 21 = previous 18 + 3 (Marts 2/3/4). Matrix rows added above. Remaining non-active: `fact_market_import_indicators` (deferred, C2 source out of Ask 1) + `fact_product_export_situation` (BLOCKER, C15 HS11 letter). 21 of 23 speccable fact-time relationships now active on `main`.

As of **2026-06-08 (#47 / #59)**: C15 `fact_product_export_situation` revived at HS11 grain — warehouse delivered the HS11-grain `GOLD_PRODUCT_EXPORT_SITUATION` rebuild (`taitra101git/teradata-tradedata-to-fabric-warehouse` #7/#9; business ruling @cindyzhuang4121 — HS11, **no** 2015–2021 backfill, year range 2022+). Its `_time` (→`dim_time_year.year`) + `_hs_tw` relationships are active and live-verified. Only `fact_market_import_indicators` (C2, deferred) remains non-active → **22 of 23** speccable fact-time relationships active on `main`.

## Alternatives Considered

1. **Single `dim_date` with period_type column** — rejected; spec §5.2
   explicit. Summarizing across period_types silently mixes annual and
   monthly totals, a class of bug that's hard to detect in review.
2. **dim_time_month with virtual year filter** — rejected; requires DAX
   calculated relationship forbidden under `directLakeOnly`.

## References

- Spec `docs/superpowers/specs/2026-04-20-itrade-powerbi-semantic-model-design.md` §5.2
- Gold dim spec `../specs/gold/dimensional-model.md` §2.4
- Existing ADR 0003 scope note (the P0-era stub referenced "0003-fact-time-
  relationship-matrix.md" which was never authored; 0010 fulfils that gap
  without renumbering to keep ADR numbering append-only).
