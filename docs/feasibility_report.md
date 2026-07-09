# 可行性評估報告：照 ralph_powerbi_pbij_tom_project 規格拆分 fact_tariff_rate

**日期：** 2026-07-09
**工項：** 將 `itrade_trade_model` 的 `[fact_tariff_rate]` 拆分為獨立語意模型（原擬委外，改自行執行）
**評估基準：** https://github.com/taitra101git/ralph_powerbi_pbij_tom_project （指示：不做任何優化，完全照規格）

## 結論

**可行，且已完成。** 拆分後的 `itrade_tariff_model` 已部署至
IH_DataTeam_Ann workspace 並通過 live 對標驗證（與原模型逐列一致，
444,392,932 列）。規格的核心方法論（TMDL as source of truth → make check
backpressure → fabric-cicd 部署 → REST executeQueries live 驗證）在本環境
100% 走得通；唯一走不通的是 CI/CD 全自動化那段（SP 權限，見文末註記，
本次依指示略過）。

## 規格遵循對照

| 規格元素 | 遵循方式 |
|---|---|
| TMDL 表定義（fact + 5 dims） | **原封複製**，位元相同 |
| 關聯拓撲（6 條，含 issue79/ADR 0023 角色接線） | 原封拆出子集（exporter=dim_country active、importer=dim_country_partner active、importer→dim_country inactive fallback） |
| 量測 ×4 / Tariff perspective / DirectLake DatabaseQuery | 原封複製 |
| ADR 0007/0008（grain、non-additive）| 由 tmdl_lint + 測試強制，0 violations |
| scripts/（deploy_model、wait_for_framing、fabric_dax_client、tmdl_lint、golden_compare） | **原封複製，未改一行** |
| tests/（unit + tariff 靜態 + live-gated） | 原封複製，僅模型資料夾路徑改名 |
| pyproject 依賴版本（fabric-cicd==0.1.34 等） | 完全相同 |
| Makefile backpressure（ruff+sqlfluff+tmdl-lint+pytest） | 相同，46 unit + 27 tariff 靜態全綠 |
| Ralph Loop 檔案（PROMPT.md、progress.json、fix_plan.md、status/*.json） | 依規格建立並維護 |

## 必要適配（非優化，皆為環境/範圍所迫）

1. **模型改名 `itrade_tariff_model`**（folder/.platform/database.tmdl 三處）
   — 目標 workspace 已存在 `itrade_trade_model` 與 `tariff_semantic_model`
   項目，fabric-cicd 依 displayName 比對，同名即覆蓋。新 logicalId 已產生。
2. **測試範圍縮小**：`test_partner_role_playing_relationships.py` 原斷言
   market/product/industry 關聯（不在拆分範圍），縮至本模型的
   `fact_tariff_importer_role` + `fact_tariff_importer`；政策斷言本身不變。
   其餘全模型測試（perspective 一致性、lineage 唯一、dim 結構）原樣通過。
3. **部署憑證**：`scripts/deploy_split_dev.py`（新增檔）重組規格
   `deploy_and_frame` 的完整流程（deploy → resolve → TakeOver → refresh →
   wait_for_framing），全部呼叫規格原函式，僅把 credential 換成
   `AzureCliCredential`（原因見 CI/CD 註記）。
4. **驗證憑證**：`scripts/validate_split_live.py`（新增檔）直接以 user token
   建構規格的 `FabricDAXClient` 做跨模型對標。
5. **Windows 環境**：Makefile `python3`→`python`；GNU make 4.4.1 由 winget
   安裝（規格假設 Linux/CI 環境有 make）。
6. **pyproject 加 `[tool.setuptools] packages=["scripts"]`**：本專案無規格
   repo 的 src/ 目錄，setuptools 自動探索會因多個 top-level 目錄報錯。

## 部署與驗證證據

- **部署**：fabric-cicd 0.1.34 發佈成功，dataset id
  `217458bd-40a3-4684-ab00-faa5e65232fc`，DirectLake framing 46.33 秒
  （`status/tariff_deploy_evidence.json`）
- **Live 對標**（`status/tariff_split_validation.json`，全部 match）：
  | Probe | 結果 |
  |---|---|
  | COUNTROWS(fact_tariff_rate) | 444,392,932 — 兩模型相同 |
  | 全模型 Avg/Min/Max/Pref 量測 | 7.7777 / 0.0 / 3000.0 / 1.1303 — 相同 |
  | Avg Tariff Rate % by year | 8 列逐列相同 |
  | 列級切片（出口國=美國 842、HS 800300） | 337 列全欄位逐列相同 |
- **對標對象**：原 `itrade_trade_model` @ 規格 DEV workspace（b20289d7）。
  兩模型 DirectLake 指向同一 GOLD_FACT_TARIFF_RATE，故一致性即拆分正確性。

## CI/CD 註記（本次依指示略過）

規格的 GitHub Actions / deploy_model.py 無人職守路徑需要 SP 憑證：
KV `kv-trade-intel-mcp-onb` 的 SP `taitra-mcp-fabric`（adf77db4…）**尚無**
IH_DataTeam_Ann workspace 角色（現有的 Fabric-Connector 是另一個 SP）。
日後要接 CI/CD 時，請 workspace Admin（莊世欣）將 `taitra-mcp-fabric`
加為 Member，之後即可直接用規格原生
`python -m scripts.deploy_model --workspace-id … --environment dev
--dataset-name itrade_tariff_model`，tests/tariff 的 5 個 live-gated
測試也會隨之解鎖。
