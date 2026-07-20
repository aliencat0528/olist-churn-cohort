"""全專案參數的單一真相來源。

商業假設區（H2 人為接軌點）：Olist 資料沒有成本欄位，
毛利率／券面額／領券率是商業判斷值——改完數字重跑 pipeline，報告自動更新。
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / 'data'
SQL_DIR = PROJECT_ROOT / 'sql'
FIG_DIR = PROJECT_ROOT / 'reports' / 'figures'
REPORT_PATH = PROJECT_ROOT / 'REPORT.md'
DATA_NOTES_PATH = PROJECT_ROOT / 'DATA_NOTES.md'

# 分析窗口（左閉右開）：2016 年資料稀疏、2018-09 之後不完整（陷阱 #2）
WINDOW_START = '2017-01-01'
WINDOW_END = '2018-09-01'

# 回購觀察期（天）：驅動因素分析與挽回名單的統一 outcome
REPURCHASE_HORIZON_DAYS = 90

# ── 商業假設（標明「假設」，非資料推得）────────────────
GROSS_MARGIN = 0.30   # 毛利率
COUPON_RATE = 0.10    # 券面額 = 客單價的 10%
REDEEM_RATE = 0.20    # 發出後被使用的比率

# 驗證期望值
EXPECTED_ORDERS_ROWCOUNT = 99441
# 全表對帳實測差 1.03%：payment_value 含分期利息，且 canceled/unavailable
# 訂單有付款紀錄但無 items。屬資料特性非損壞，門檻放至 1.5% 並在 DATA_NOTES 記錄
PAYMENT_RECON_TOLERANCE_PCT = 1.5
