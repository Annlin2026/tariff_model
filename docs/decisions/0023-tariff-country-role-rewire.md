# ADR 0023 — Tariff Country-Role Rewire (exporter = dim_country, importer = dim_country_partner)

Status: Accepted · Date: 2026-07-07 · Trigger: issue #79

## Context

The production tariff report (`taitra101git/Tariff_PBI`, TARIFF4.0 「單一產品全球關稅總覽」)
binds `dim_country` as the **出口國** slicer and `dim_country_partner` as the
**進口國** rows. The model, however, still carried the P3 Iter 4 wiring:

- `fact_tariff_importer` (importer_code → dim_country) **active**
- `fact_tariff_exporter` (exporter_code → dim_country) **inactive**
- no relationship at all from `fact_tariff_rate` to `dim_country_partner`

Two visible defects followed (issue #79): the 出口國 slicer actually filtered
tariff rows as the *importer* (selecting 臺灣 showed Taiwan's own import
tariffs, e.g. 40% / 2026 for HS 030910), and the 進口國 column had no filter
effect at all, so the same wrong number repeated for every one of 200+ rows.

The exporter role was a *known deferral*, not an oversight — the P3 5x5 perf
test docstring recorded "exporter-role … requires role-playing country dim …
off by design in Iter 4". Issue #1 (BUG-001) later introduced exactly that
role-playing dim (`dim_country_partner`) for ten other facts, but
`fact_tariff_rate` never got its counterpart relationship.

Data was verified healthy before rewiring: `exporter_code=490` returns 139
importers with varied rates (ITC MacMap MFN agreement 99%+ on overlapping
markets); `importer_code` values are 100% contained in
`dim_country_partner[country_id]`, `exporter_code` 100% in
`dim_country[country_id]`, both keys unique, both sides `string`.

## Decision

Adopt the same partner-role pattern the other ten facts use:

| Relationship | Wiring | State |
|---|---|---|
| `fact_tariff_exporter` | exporter_code → dim_country | **active** (was inactive) |
| `fact_tariff_importer` | importer_code → dim_country | **inactive** (was active; kept as USERELATIONSHIP fallback, per BUG-001 policy) |
| `fact_tariff_importer_role` | importer_code → dim_country_partner | **new, active** |

`dim_country_partner` is added to the `Tariff` perspective so the importer
axis is reachable in tariff-scoped views.

Semantics after the rewire: `dim_country` = 出口國 axis, `dim_country_partner`
= 進口國 axis — matching the shipped report bindings, so the report needs **no
rebinding**. Note this means dim_country's role for tariff (exporter) differs
from the market facts (reporter/importer); the model-wide invariant is
"dim_country carries the page's main slicer, dim_country_partner the
counterpart axis", not a fixed trade direction.

## Consequences

- Report-layer HOTFIX measures added under #79 (`TREATAS` on
  exporter_code/importer_code with `REMOVEFILTERS` on both dims) remain
  correct during the transition — they bypass relationships and re-apply the
  equivalent filters — so deploy order does not matter. After this model fix
  reaches PROD, the TARIFF4.0 report should drop those extension measures and
  bind the plain model measures (`Max/Min/Avg Tariff Rate %`,
  `Preferential Rate %`) directly.
- Any future DAX needing "tariffs this country *imposes*" (importer semantics
  on dim_country) must use `USERELATIONSHIP(fact_tariff_rate[importer_code],
  dim_country[country_id])` — the inactive relationship is retained for
  exactly this.
- The F64 5x5 perf baseline keeps its thresholds: the query shape (one active
  one-direction relationship) is unchanged; only the business meaning of the
  dim_country axis flipped. Docstring updated in place.
- Live regression surface checked: the 15-case measure-scope gate's tariff
  case and the adhoc TW→Italy lookups filter raw fact columns
  (`fact_tariff_rate[importer_code]` / `[exporter_code]`) and are
  relationship-independent; live relationship presence tests only assert
  names, and both legacy names survive.
