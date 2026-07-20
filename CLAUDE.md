> 繼承根目錄共用規則（Claude Code 已自動載入，勿重複讀取 ../CLAUDE.md）

# olist-churn-cohort

作品集專案三：Olist 會員流失 cohort 分析（91APP 對映）。
主軸：**每個分析結論都接一個金額化決策**。規劃書見 prepare.md 頂部連結。

## 技術棧與指令

- Python 3.12 + venv（`.venv/`），依賴見 `requirements.txt`
- 分析引擎：DuckDB（重邏輯用 SQL）＋ pandas（輕整形）＋ matplotlib（靜態圖）
- 資料下載：`python scripts/download_data.py`（需 `~/.kaggle/kaggle.json`，見 README）
- 一鍵跑 pipeline：`.venv/bin/python src/run_pipeline.py`（輸出 REPORT.md 與 reports/figures/）

## 專案規則（與根規則的差異）

- `data/` 不進 git；原始 CSV 一律視為唯讀，任何清理都在 SQL view 層做
- 金額口徑統一為 `order_items.price + freight_value`；`order_payments` 只用於對帳
- 分析窗口 2017-01 ~ 2018-08、只留 `delivered` 訂單；改動口徑必須記入 `prepare.md`
- 商業假設參數（毛利率、券面額、領券率）集中 `src/params.py`，改參數不改邏輯
- `sql/` 檔名編號即執行順序，每檔開頭註解標明回答規劃書的哪個 Q
