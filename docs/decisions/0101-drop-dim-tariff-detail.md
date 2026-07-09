# 0101 — 拆分模型移除 dim_tariff_detail

**日期：** 2026-07-09 ｜ **狀態：** 決定（使用者裁定）

## 背景

`dim_tariff_detail`（V_DIM_TARIFF_DETAIL 視圖，tariff_type / tariff_type_zh /
agreement_name 三欄）在模型檢視中長期掛警告，且拆分後檢查其用途：

- **報表層零引用** — grep 整個 `關稅PBI` 專案（TARIFF3.0.Report +
  TARIFF4.0.Report 全部 visuals / filters / bookmarks），`dim_tariff_detail`、
  `agreement_name`、`tariff_type` 皆 0 hit；同一 grep 對照組
  `fact_tariff_rate`/`dim_country`/`dim_hs_code` 有 106 處引用，證明掃描有效。
- **量測零依賴** — 模型 4 個量測只用 fact_tariff_rate 的 rate 欄位。

## 決定

自 `itrade_tariff_model` 移除 `dim_tariff_detail` 表、`fact_tariff_type`
關聯與 perspective 條目。**fact_tariff_rate[tariff_type] 欄位保留**（grain
的一部分，ADR 0007），日後若報表需要稅則種類軸，重新加回 dim 即可
（TMDL 在 git history 及規格 repo 都有）。

## 影響

- 關聯 6 → 5；表 6 → 5。
- 原 itrade_trade_model **不受影響**（本決定只作用於拆分模型）。
- 測試同步：test_tariff_dims_tmdl / test_tariff_perspective 改斷言「已移除」。
