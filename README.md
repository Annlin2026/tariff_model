# iTrade Tariff Semantic Model（fact_tariff_rate 拆分專案）

將 `itrade_trade_model` 的 `[fact_tariff_rate]` 拆分為獨立語意模型
`itrade_tariff_model`，完全依照
[ralph_powerbi_pbij_tom_project](https://github.com/taitra101git/ralph_powerbi_pbij_tom_project)
的規格與方法論執行（TMDL as source of truth、make check backpressure、
fabric-cicd 部署、REST executeQueries live 驗證）。

**目標 workspace:** `IH_DataTeam_Ann`（aa4e76f5-3e7a-4de2-a6d5-6ab0815cbfd8）

## 模型內容（自 itrade_trade_model 原封拆出）

| 物件 | 來源 |
|---|---|
| fact_tariff_rate | GOLD_FACT_TARIFF_RATE（Direct Lake, comtrade_ralph_dev） |
| dim_country | GOLD_DIM_COUNTRY |
| dim_country_partner | GOLD_DIM_COUNTRY（role-playing 進口國軸，ADR 0023/issue79） |
| dim_hs_code | GOLD_DIM_HS_CODE |
| dim_time_year | 時間維度 |
| 關聯 ×5 | fact_tariff_importer(inactive)/exporter/importer_role/hs/time |
| 量測 ×4 | Avg/Min/Max Tariff Rate %、Preferential Rate % |
| Perspective | Tariff |

## Quickstart
```bash
pip install -e .[dev]
cp .env.example .env   # 填 SP secrets + workspace IDs
make check
```

## 部署
```bash
python -m scripts.deploy_model --workspace-id <WS_ID> --environment dev --dataset-name itrade_tariff_model
```
注意：KV 的 SP（taitra-mcp-fabric）目前**沒有**此 workspace 權限；
在 Admin 加入 SP 之前，用使用者身分（az login）呼叫
`scripts.deploy_model.deploy_and_frame(..., credential=AzureCliCredential())`。
詳見 `docs/feasibility_report.md`。

## 規格出處與偏差

規格 repo 原封複製：scripts/*、tests/*（僅模型資料夾路徑改名）、
tariff 相關 TMDL 表定義、golden CSV、tariff ADR。
偏差清單（皆為環境適配，非規格優化）記錄於 `docs/feasibility_report.md`。
