# Business CSV → Test C-代號 映射對照（草稿 v1，待 user review）

**日期**：2026-04-22
**作者**：Claude（根據 semantic model 的 fact 名稱反推）
**狀態**：**草稿，需業務/你確認每一列才能用**

## 使用方式

右欄「建議 C 代號」是 Claude 的猜測，根據 fact table 的命名（例如 `fact_market_import_situation` → 對應報表頁「全球自美國進口情勢-相關數據」）。

請你：
1. 逐列看「建議 C 代號」是否正確
2. 錯的改對
3. 標 ❓ 的是 Claude 不確定的，需要你決定
4. 確認完後回我，我去改 18 個 test 的 `GOLDEN_GLOB` 常數

---

## 一、Market 系列（15 CSV，對應 9 個 fact C1-C9）

| # | CSV 檔名 | 對應 fact table | 建議 C 代號 | 信心 |
|---|---|---|---|---|
| 1 | 市場-全球自美國進口情勢-相關指標 | fact_market_import_indicators | **C2** | 中 |
| 2 | 市場-全球自美國進口情勢-相關數據 | fact_market_import_situation | **C1** | 高 |
| 3 | 市場-全球自美國進口情勢-相關數據-進口來源國 | fact_market_import_source_countries | **C3** | 高 |
| 4 | 市場-全球自美國進口情勢-相關數據-進口來源國-需求產品 | C3 子頁（共用 C3 test）| **C3 子頁** ✅ user-confirmed 2026-04-22 | 高 |
| 5 | 市場-全球自美國進口情勢-相關數據-需求產品 | fact_market_import_demand_products | **C4** | 高 |
| 6 | 市場-全球自美國進口產業 | fact_market_industry_import | **C7** | 高 |
| 7 | 市場-全球自美國進口產業-其它進口來源國 | fact_market_industry_source_countries | **C8** | 高 |
| 8 | 市場-全球自美國進口產業-其它進口來源國-需求產品 | C9 延伸（共用 C9 test）| **C9 延伸** ✅ user-confirmed 2026-04-22 | 高 |
| 9 | 市場-全球自美國進口產業-需求產品 | fact_market_industry_demand_products | **C9** | 高 |
| 10 | 市場-美國出口至全球情勢-相關指標 | **缺 fact（fact_market_export_indicators）**| **Phase 2 backlog** per ADR 0015（待業務簽核）| — |
| 11 | 市場-美國出口至全球情勢-相關數據 | fact_market_export_situation | **C5** | 高 |
| 12 | 市場-美國出口至全球情勢-相關數據-美國出口產品細項 | fact_market_export_product_details | **C6** | 高 |
| 13 | 市場-美國出口至全球產業 | **缺 fact（fact_market_export_industry）**| **Phase 2 backlog** per ADR 0015（待業務簽核）| — |
| 14 | 市場-美國出口至全球產業-出口市場 | **缺 fact（fact_market_export_industry_markets）**| **Phase 2 backlog** per ADR 0015（待業務簽核）| — |
| 15 | 市場-美國出口至全球產業-出口產品細項 | **缺 fact（fact_market_export_industry_products）**| **Phase 2 backlog** per ADR 0015（待業務簽核）| — |

**Claude 觀察**：
- 4 & 8 是「複合頁」（同時交叉兩個維度），可能只是「相同 fact 換呈現」，不一定對應獨立 C。
- 10 「出口情勢-相關指標」可能是 C5 的 sub-page；也可能業務交了額外一份我們還沒建的 mart。
- 13-15 是「美國出口至全球產業」系列，目前 semantic model **沒有**這個 fact 家族。業務可能有多交；或未來要擴充 C21+？

---

## 二、Product 系列（7 CSV，對應 6 個 fact C10-C15）

| # | CSV 檔名 | 對應 fact table | 建議 C 代號 | 信心 |
|---|---|---|---|---|
| 16 | 產品-全球進口情勢 | fact_product_global_import | **C10** | 高 |
| 17 | 產品-全球進口情勢-趨勢分析-進口來源國 | fact_product_global_import_sources | **C11** | 高 |
| 18 | 產品-台灣出口市場 | fact_product_tw_export_markets | **C13** | 高 |
| 19 | 產品-台灣出口市場-該國其它進口來源 | fact_product_tw_market_other_sources | **C14** | 高 |
| 20 | 產品-台灣出口產品 | fact_product_tw_export_products | **C12** | 高 |
| 21 | 產品-台灣出口產品-出口市場分析 | （複合頁）可能 C12 子頁 | **❓** | 低 |
| 22 | 產品-產品出口情勢 | fact_product_export_situation | **C15** | 高 |

---

## 三、Industry 系列（4 CSV，對應 3 個 fact C16-C18）

| # | CSV 檔名 | 對應 fact table | 建議 C 代號 | 信心 |
|---|---|---|---|---|
| 23 | 產業-全球進口情勢 | fact_industry_global_import | **C16** | 高 |
| 24 | 產業-全球進口情勢-進口來源國 | fact_industry_import_source_countries | **C17** | 高 |
| 25 | 產業-全球進口情勢-進口來源國-需求產品 | （複合頁）可能 C17 子頁 or C18 延伸 | **❓** | 低 |
| 26 | 產業-全球進口情勢-需求產品 | fact_industry_import_demand_products | **C18** | 高 |

---

## 四、Tariff（關稅）— 2026-04-22 業務補交「樣本」

業務 2026-04-22 補交 5 個檔（xlsx + png）：
- `Tariff-1-China出口800300到各國MFN關稅稅率.xlsx` → `tariff_cn_800300_golden.csv`
- `Tariff-4-United States of America出口800300到各國MFN關稅稅率.xlsx` → `tariff_us_800300_golden.csv`
- `Tariff-5-United Kingdom出口800300到各國MFN關稅稅率.xlsx` → `tariff_gb_800300_golden.csv`
- `Tariff-2-關稅畫面.png`（報表截圖，參考用）
- `Tariff-3-多對多sample_800300.xlsx`（多對多關聯性 sample，暫不建 test）

**範圍**：樣本 (spot check)，HS 800300 × 3 reporters。**Phase 1 tariff 驗證就以此樣本為準**（業務 2026-04-22 sign-off）。
**Test**：`tests/tariff/test_tariff_golden_csv.py` 改成 parametrise 3 reporter，DAX 加 `exporter_code` + `hs_code` filter。
**xlsx→csv**：`scripts/convert_tariff_xlsx_to_csv.py`（idempotent，xlsx 更新時重跑）。

**MFN / 有效稅率 / 優惠差距的 DAX 欄位對應（待業務確認）**：
- `MFN稅率%` → 現暫對 `Max Tariff Rate %`
- `有效關稅率%` → 現暫對 `Avg Tariff Rate %`
- `優惠差距%` → 對 `Preferential Rate %`

如業務有標準定義，改 DAX_TEMPLATE 一行即可。

---

## 五、總計 & 對應關係

| 模組 | Claude 要的 test 數 | 實際 CSV 數 | 主要對應 | 複合/延伸 | 無對應 |
|---|---|---|---|---|---|
| Market (C1-C9) | 9 | 15 | 9 | 2 (#4, #8) | 4 (#10, #13, #14, #15) |
| Product (C10-C15) | 6 | 7 | 6 | 1 (#21) | 0 |
| Industry (C16-C18) | 3 | 4 | 3 | 1 (#25) | 0 |
| Tariff | 3（parametrise）| 3 golden CSV（從 xlsx 轉）| 3 | 0 | 0 — 樣本已交 |
| **合計** | **21** | **29**（26 + 3 tariff）| **21** | **4** | **4**（Phase 2 backlog per ADR 0015）|

---

## 六、你要決定的 4 件事

### 決定 1：複合頁（#4 / #8 / #21 / #25）怎麼處理？

這 4 個 CSV 檔名有兩個維度組合（例如「進口來源國 + 需求產品」）。建議選：
- **(a)** 不建 test，當成「業務額外交付，做參考不 validate」
- **(b)** 建新 test（例如 C3-extended、C8-extended），但需要新 DAX
- **(c)** 指派給其中一個現有 C（例如 #4 → C3 or C4，測 subset column）

### 決定 2：「美國出口至全球產業」系列（#13 / #14 / #15）怎麼處理？

這三份 CSV 對應的 fact table 目前**沒有建**（C1-C9 裡找不到匹配）。選項：
- **(a)** 業務多交的，跳過不理（最簡單）
- **(b)** spec scope 擴充 → 建 C21/C22/C23 新 mart（這會是 P2b extension，工作量大）
- **(c)** 寄信問業務「這三份是不是多給的？還是預計要支援？」

### 決定 3：「出口情勢-相關指標」（#10）

可能是 C5 變體，也可能是新的 mart。選：
- **(a)** 歸成 C5 的第二份 CSV（test 支援多 CSV glob）
- **(b)** 跳過
- **(c)** 問業務

### 決定 4：Tariff CSV 要怎麼追？

- 寄信問業務？
- 在其他資料夾找過？
- 先保留 test SKIP？

---

## 附件：test 端 glob 如果採用

確認後，我會把 18 個 test 的 `GOLDEN_GLOB` 改成能 match 中文檔名，例如：

```python
# 改前
GOLDEN_GLOB = "market_c1_*_golden.csv"

# 改後
GOLDEN_GLOB = "市場-全球自美國進口情勢-相關數據-下載csv檔.csv"
# 或保持 glob 形式
GOLDEN_GLOB = "市場-全球自美國進口情勢-相關數據-下載csv檔*.csv"
```

由於業務檔名固定（不太會再換），硬編檔名比 glob 更穩；但加 `*` glob 仍可容忍業務未來加版本號。
