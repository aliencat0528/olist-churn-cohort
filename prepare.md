# Prepare — olist-churn-cohort 決策記錄

> 記錄規則繼承根 `prepare.md`，此處只寫差異。編號前綴 `OC-`。
> 完整規劃書（商業問題、方法、Phase、人為接軌點）：
> https://claude.ai/code/artifact/6e4157f2-4692-44ad-a785-421e24d904c1

---

## 決策日誌（新的在上）

### OC-003 · 2026-07-20
- **決策**：資料先用 GitHub 鏡像（spdrio/Brazilian-E-Commerce-Public-Dataset-by-Olist，8 CSV，缺 geolocation——本專案不用該表）
- **依據**：本機無 Kaggle 憑證（H1）；鏡像資料通過全部驗證（orders=99,441、97.02% delivered、id 差異 99,441/96,096 皆與官方文件一致）
- **待辦**：正式投遞作品前，用 Kaggle 官方重新下載核對一次（download_data.py 已備好）
- **附帶口徑**：付款對帳門檻 1.0% → 1.5%（實測差 1.033%：payment_value 含分期利息、取消單有付款無 items）

### OC-002 · 2026-07-19
- **決策**：churn 定義採「回購者 IPT（inter-purchase time）P75/P90 分位數」導出天數門檻
- **落地細節**：實跑定案（2026-07-20）——預警線 P75 = 168 天、流失線 P90 = 275 天
  （n=2,219 組回購對，中位數 69 天）；90 天回購率為驅動因素分析的統一 outcome
- **棄選**：固定 30/60/90 天拍腦袋門檻（無資料依據）；ML churn 模型（樣本薄、犧牲可解釋性）

### OC-001 · 2026-07-19 · ← D-001
- **決策**：工具鏈 DuckDB + pandas + matplotlib；主交付物 `REPORT.md`（非 notebook / dashboard）
- **落地細節**：SQL 檔編號即執行順序；商業假設參數集中 `src/params.py`；
  分析窗口 2017-01 ~ 2018-08、只留 delivered、金額口徑 items.price + freight
- **人為接軌點**：H1 Kaggle 憑證、H2 商業參數、H3 PR merge、H4 報告內化、H5 部署（見規劃書 §10）

---

## 待討論事項

（無——資料來源議題已轉為 OC-003）
