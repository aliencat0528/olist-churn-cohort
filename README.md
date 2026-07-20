# olist-churn-cohort - Olist 會員流失 Cohort 分析

用 10 萬筆巴西電商訂單回答三個預算問題：留客值不值得花錢、挽回名單給誰、哪個流失原因先修——每個分析結論都接一個金額化決策。

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 功能特色 【必要】

- **Cohort retention 分析** — 首購月同期群 × 第 N 月回購率矩陣與累積營收
- **資料驅動的流失定義** — 由回購間隔（IPT）分位數導出門檻，不拍腦袋
- **RFM 挽回名單** — R×M 分層、優先級與建議動作
- **流失驅動因素** — 延遲交貨／評分 vs 回購率，z 檢定＋信賴區間
- **挽回券期望值** — break-even uplift 計算，含「拒絕決策」情境

## 快速開始 【必要】

前置需求：Python 3.12+、Kaggle 帳號（下載資料用）。

```bash
cd olist-churn-cohort
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 預期：Successfully installed duckdb-... pandas-... matplotlib-...

# 資料（擇一）：
# a) 有 ~/.kaggle/kaggle.json：
.venv/bin/python scripts/download_data.py
# b) 手動：從 Kaggle「Brazilian E-Commerce Public Dataset by Olist」下載 zip，解壓到 data/

.venv/bin/python src/run_pipeline.py
# 預期：終端列出各 Phase 驗證結果，產出 REPORT.md 與 reports/figures/*.png
```

## 使用方式 【必要】

- 全流程重跑：`src/run_pipeline.py`（驗證 → cohort → IPT → RFM → 驅動因素 → 期望值 → 報告）
- 改商業假設（毛利率、券面額、領券率）：編輯 `src/params.py` 後重跑，報告自動更新
- 單獨看某段 SQL：`sql/` 內各檔可獨立閱讀，檔頭註明回答哪個商業問題

## 專案結構 【必要】

```
olist-churn-cohort/
├── data/                # 原始 CSV（不進 git）
├── scripts/download_data.py
├── sql/                 # 00_views → 01_validation → 02_cohort → 03_ipt → 04_rfm → 05_drivers
├── src/
│   ├── params.py        # 路徑、分析窗口、商業假設參數（單一真相來源）
│   └── run_pipeline.py  # 一鍵跑完全部
├── reports/figures/     # 圖表輸出
├── REPORT.md            # 主交付物：分析報告（pipeline 產出）
└── DATA_NOTES.md        # 資料驗證紀錄與口徑定義
```

## 測試 【必要】

```bash
.venv/bin/python src/run_pipeline.py --validate-only
# 預期：九項資料驗證全部 PASS（含 orders=99,441、customer_id vs unique_id 差異確認）
```

## 版本歷史 【必要】

### v0.1.0 (2026-07-19)

- **專案初始化** — 骨架、SQL 分析模組、pipeline、規劃書定稿

## 授權 【必要】

MIT License
