"""一鍵跑完全部分析：驗證 → cohort → IPT → RFM → 驅動因素 → 期望值 → REPORT.md。

用法：
    python src/run_pipeline.py                 # 全流程
    python src/run_pipeline.py --validate-only # 只跑資料驗證（Phase 1）

圖表軸標為英文（避免 matplotlib CJK 字型問題），報告本文為繁中。
"""

import math
import sys
from datetime import datetime

import duckdb
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

import params as P

ACCENT = '#0e6e5c'
INK = '#1d2422'
MUTED = '#5c6663'
GRID = '#dde3e0'
SEQ_CMAP = LinearSegmentedColormap.from_list('seq_teal', ['#f4f7f6', ACCENT])

plt.rcParams.update({
    'figure.dpi': 150,
    'axes.edgecolor': GRID,
    'axes.labelcolor': INK,
    'text.color': INK,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'axes.grid': True,
    'grid.color': GRID,
    'grid.linewidth': 0.6,
    'axes.axisbelow': True,
    'font.size': 9,
})


def load_sql(name: str) -> str:
    text = (P.SQL_DIR / name).read_text()
    return (text
            .replace('{data_dir}', str(P.DATA_DIR))
            .replace('{start}', P.WINDOW_START)
            .replace('{end}', P.WINDOW_END)
            .replace('{horizon}', str(P.REPURCHASE_HORIZON_DAYS)))


def two_prop_ztest(s1: int, n1: int, s2: int, n2: int):
    """回傳 (p1, p2, diff, ci_low, ci_high, z, p_value)。diff = p1 - p2。"""
    p1, p2 = s1 / n1, s2 / n2
    pool = (s1 + s2) / (n1 + n2)
    se_pool = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pool if se_pool else float('nan')
    p_value = math.erfc(abs(z) / math.sqrt(2))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p1 - p2
    return p1, p2, diff, diff - 1.96 * se, diff + 1.96 * se, z, p_value


def md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


# ── Phase 1：資料驗證 ──────────────────────────────────────────

def run_validation(con) -> tuple[bool, str, dict]:
    chunks = []
    for block in load_sql('01_validation.sql').split('-- @check:'):
        block = block.strip()
        if not block or block.startswith('--'):
            continue
        name, _, sql = block.partition('\n')
        if sql.strip():
            chunks.append((name.strip(), sql.strip()))

    results, notes, ok = {}, [], True
    for name, sql in chunks:
        df = con.execute(sql).df()
        results[name] = df
        status = 'INFO'
        if name.startswith('orders_rowcount'):
            status = 'PASS' if int(df.n[0]) == P.EXPECTED_ORDERS_ROWCOUNT else 'FAIL'
        elif name.startswith('order_id_unique'):
            status = 'PASS' if int(df.dup[0]) == 0 else 'FAIL'
        elif name.startswith('payment_reconciliation'):
            status = 'PASS' if float(df.diff_pct[0]) < P.PAYMENT_RECON_TOLERANCE_PCT else 'FAIL'
        elif name.startswith('delivered_missing_timestamp'):
            status = 'PASS' if int(df.n[0]) < 50 else 'WARN'
        if status == 'FAIL':
            ok = False
        print(f'[{status}] {name}')
        print(df.to_string(index=False, max_rows=30), '\n')
        notes.append(f'### {name} — {status}\n\n{md_table(df.head(30))}\n')

    P.DATA_NOTES_PATH.write_text(
        f'# DATA_NOTES — 資料驗證紀錄\n\n'
        f'> 產生時間：{datetime.now():%Y-%m-%d %H:%M}，由 `run_pipeline.py` 自動輸出。\n'
        f'> 口徑：窗口 {P.WINDOW_START} ~ {P.WINDOW_END}（左閉右開）、只留 delivered、\n'
        f'> 訂單金額 = items.price + freight_value（payments 僅對帳）。\n\n'
        + '\n'.join(notes))
    print(f'驗證紀錄已寫入 {P.DATA_NOTES_PATH.name}')
    return ok, '', results


# ── Phase 2：Cohort ───────────────────────────────────────────

def run_cohort(con) -> dict:
    df = con.execute(load_sql('02_cohort.sql')).df()
    df['cohort_month'] = pd.to_datetime(df.cohort_month).dt.strftime('%Y-%m')

    counts = df.pivot(index='cohort_month', columns='month_offset', values='active_customers')
    sizes = counts[0]
    retention = counts.div(sizes, axis=0) * 100
    max_off = min(12, retention.columns.max())
    ret = retention.loc[:, retention.columns <= max_off]

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(ret.mask(ret.isna()), cmap=SEQ_CMAP, aspect='auto',
                   vmin=0, vmax=max(1.0, ret.iloc[:, 1:].max().max()))
    ax.set_xticks(range(len(ret.columns)), ret.columns)
    ax.set_yticks(range(len(ret.index)), ret.index)
    ax.set_xlabel('Months since first purchase')
    ax.set_ylabel('First-purchase cohort')
    ax.set_title('Cohort retention (% of cohort active in month N)', loc='left')
    ax.grid(False)
    for i in range(ret.shape[0]):
        for j in range(ret.shape[1]):
            v = ret.iloc[i, j]
            if pd.notna(v) and j > 0:
                ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=6, color=INK)
    fig.colorbar(im, ax=ax, shrink=0.6, label='%')
    fig.tight_layout()
    fig.savefig(P.FIG_DIR / 'cohort_retention.png')
    plt.close(fig)

    rev = df.groupby('cohort_month').revenue.sum()
    quality = pd.DataFrame({
        'cohort': sizes.index,
        'size': sizes.values.astype(int),
        'ret_m1_pct': retention[1].round(2).values if 1 in retention else None,
        'rev_per_user': (rev / sizes).round(2).values,
    })
    return {'quality': quality, 'retention_m1_avg': float(retention[1].mean())}


# ── Phase 2b：IPT 與 churn 門檻 ───────────────────────────────

def run_ipt(con) -> dict:
    s = con.execute(load_sql('03_ipt.sql')).df().ipt_days
    p50, p75, p90 = (float(s.quantile(q)) for q in (0.5, 0.75, 0.9))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(s.clip(upper=400), bins=40, color=ACCENT, edgecolor='white', linewidth=0.5)
    for v, lbl in ((p75, f'P75 = {p75:.0f}d'), (p90, f'P90 = {p90:.0f}d')):
        ax.axvline(v, color=INK, linewidth=1, linestyle='--')
        ax.text(v + 5, ax.get_ylim()[1] * 0.9, lbl, fontsize=8, color=INK)
    ax.set_xlabel('Days between consecutive purchases (clipped at 400)')
    ax.set_ylabel('Purchase pairs')
    ax.set_title('Inter-purchase time distribution (repeat buyers)', loc='left')
    fig.tight_layout()
    fig.savefig(P.FIG_DIR / 'ipt_distribution.png')
    plt.close(fig)

    return {'n_pairs': int(len(s)), 'p50': p50, 'p75': p75, 'p90': p90}


# ── Phase 3：RFM 與挽回名單 ───────────────────────────────────

def run_rfm(con, ipt: dict) -> dict:
    df = con.execute(load_sql('04_rfm.sql')).df()
    at_risk_lo, churn_lo = ipt['p75'], ipt['p90']
    df['status'] = pd.cut(df.recency_days, [-1, at_risk_lo, churn_lo, float('inf')],
                          labels=['active', 'at_risk', 'churned'])

    seg = (df.groupby(['status', 'm_quartile'], observed=True)
             .agg(customers=('customer_unique_id', 'count'), revenue=('monetary', 'sum'))
             .reset_index())
    seg['rev_share_pct'] = (100 * seg.revenue / df.monetary.sum()).round(2)

    winback = df[(df.status == 'at_risk')]
    return {
        'seg': seg,
        'status_counts': df.status.value_counts().to_dict(),
        'winback_total': int(len(winback)),
        'winback_by_tier': winback.groupby('m_quartile').agg(
            customers=('customer_unique_id', 'count'),
            avg_monetary=('monetary', 'mean')).round(2).reset_index(),
    }


# ── Phase 4：驅動因素 ─────────────────────────────────────────

def run_drivers(con) -> dict:
    df = con.execute(load_sql('05_drivers.sql')).df()
    out = {'df': df, 'tests': []}

    def add_test(label, mask_a, mask_b, name_a, name_b):
        a, b = df[mask_a], df[mask_b]
        if len(a) < 30 or len(b) < 30:
            return
        p1, p2, diff, lo, hi, z, pv = two_prop_ztest(
            int(a.repurchased.sum()), len(a), int(b.repurchased.sum()), len(b))
        out['tests'].append({
            'factor': label, 'group_a': name_a, 'group_b': name_b,
            'n_a': len(a), 'n_b': len(b),
            'rate_a_pct': round(p1 * 100, 2), 'rate_b_pct': round(p2 * 100, 2),
            'diff_pp': round(diff * 100, 2),
            'ci95_pp': f'[{lo * 100:.2f}, {hi * 100:.2f}]',
            'p_value': f'{pv:.2g}',
            'significant': lo > 0 or hi < 0,
        })

    late = df.late_delivery.notna()
    add_test('延遲交貨', late & (df.late_delivery == 1), late & (df.late_delivery == 0),
             '延遲', '準時')
    rev = df.review_score.notna()
    add_test('首購評分', rev & (df.review_score <= 2), rev & (df.review_score >= 4),
             '1–2 分', '4–5 分')

    # robustness：同州內比較（前 5 大州），控制地區混淆
    strata = []
    for state, g in df[late].groupby('customer_state'):
        gl, go = g[g.late_delivery == 1], g[g.late_delivery == 0]
        if len(gl) >= 100 and len(go) >= 100:
            strata.append({'state': state, 'n': len(g),
                           'late_rate_pct': round(gl.repurchased.mean() * 100, 2),
                           'ontime_rate_pct': round(go.repurchased.mean() * 100, 2),
                           'diff_pp': round((gl.repurchased.mean() - go.repurchased.mean()) * 100, 2)})
    out['strata'] = (pd.DataFrame(strata).sort_values('n', ascending=False).head(5)
                     if strata else pd.DataFrame())
    return out


# ── Phase 5：期望值與 break-even ──────────────────────────────

def run_ev(drivers: dict) -> dict:
    be_pp = P.REDEEM_RATE * P.COUPON_RATE / P.GROSS_MARGIN * 100

    df = drivers['df'].copy()
    df['value_tier'] = pd.qcut(df.gmv, 4, labels=['T4 低', 'T3', 'T2', 'T1 高'])
    tier = (df.groupby('value_tier', observed=True)
              .agg(n=('repurchased', 'count'),
                   baseline_pct=('repurchased', lambda s: round(s.mean() * 100, 2)),
                   avg_gmv=('gmv', 'mean')).round(2).reset_index())

    def decide(row):
        if row.baseline_pct < be_pp:
            return '不發（基準率低於損益兩平，uplift 不可能跨過）'
        return '拒絕決策 → 建議 500 人 A/B（基準率夠高，但無 RCT 估不出真實 uplift）'

    tier['decision'] = tier.apply(decide, axis=1)

    sens = pd.DataFrame(
        [{'margin': m, **{f'redeem={r:.0%}': round(r * P.COUPON_RATE / m * 100, 2)
                          for r in (0.1, 0.2, 0.3)}}
         for m in (0.2, 0.3, 0.4)])
    return {'break_even_pp': round(be_pp, 2), 'tier': tier, 'sensitivity': sens}


# ── 報告 ──────────────────────────────────────────────────────

def write_report(val, cohort, ipt, rfm, drivers, ev):
    t = drivers['tests']
    late = next((x for x in t if x['factor'] == '延遲交貨'), None)
    if late:
        verdict = ('統計顯著' if late['significant'] else
                   '**不顯著**——資料不支持「延遲交貨導致不回購」的直覺敘事，'
                   '止血預算不應先押在物流改善上')
        late_line = (f"延遲交貨客的 {P.REPURCHASE_HORIZON_DAYS} 天回購率 {late['rate_a_pct']}%，"
                     f"準時客 {late['rate_b_pct']}%（差 {late['diff_pp']}pp，"
                     f"95% CI {late['ci95_pp']}；{verdict}）")
    else:
        late_line = '樣本不足'

    repeat = next((v for k, v in val.items() if k.startswith('repeat_rate')), None)
    repeat_pct = float(repeat.repeat_pct[0]) if repeat is not None else float('nan')

    md = f"""# Olist 會員流失 Cohort 分析報告

> 產生：{datetime.now():%Y-%m-%d %H:%M} · pipeline 自動輸出，數字口徑見 DATA_NOTES.md
> 商業假設（可在 src/params.py 調整後重跑）：毛利率 {P.GROSS_MARGIN:.0%}、
> 券面額 {P.COUPON_RATE:.0%}、領券率 {P.REDEEM_RATE:.0%}

## TL;DR — 給主管的三個決策建議

| # | 決策 | 依據 |
|---|------|------|
| 1 | **流失定義定為 {ipt['p90']:.0f} 天未回購**（回購預警線 {ipt['p75']:.0f} 天） | 回購者間隔分布 P90／P75（n={ipt['n_pairs']} 組回購對） |
| 2 | **挽回名單 {rfm['winback_total']:,} 人**（處於預警帶），依價值分四級 | RFM 分層，見下表 |
| 3 | **發券決策：見各價值層判定**——損益兩平需要 uplift ≥ {ev['break_even_pp']}pp | break-even 分析＋敏感度表 |

**一個要先講的事實**：本平台窗口內回購客僅 {repeat_pct:.1f}%。這不是經營失敗——
Olist 是低頻 marketplace，正確的 KPI 是回購週期與 {P.REPURCHASE_HORIZON_DAYS} 天回購率，
不是月留存（詳見附錄「方法與限制」）。

## Q1 · 客人多久回來一次？

回購間隔中位數 {ipt['p50']:.0f} 天、P75 = {ipt['p75']:.0f} 天、P90 = {ipt['p90']:.0f} 天。

![IPT](reports/figures/ipt_distribution.png)

**營運定義**：超過 P75（{ipt['p75']:.0f} 天）未回購 → 進入預警帶；
超過 P90（{ipt['p90']:.0f} 天）→ 視為流失。

## Q2 · 哪個月加入的客人品質好？

平均次月回購率 {cohort['retention_m1_avg']:.2f}%。Cohort 矩陣：

![Cohort](reports/figures/cohort_retention.png)

各 cohort 規模與人均營收：

{md_table(cohort['quality'])}

## Q3 · 挽回名單（RFM）

窗口末快照的客戶狀態：活躍 {rfm['status_counts'].get('active', 0):,} ·
預警 {rfm['status_counts'].get('at_risk', 0):,} · 流失 {rfm['status_counts'].get('churned', 0):,}

預警帶（at_risk）依價值層的名單：

{md_table(rfm['winback_by_tier'])}

## Q4 · 流失驅動因素

{md_table(pd.DataFrame(t))}

重點：{late_line}。

同州內分層（控制地區混淆的 robustness check）：

{md_table(drivers['strata']) if len(drivers['strata']) else '（樣本不足）'}

> **限制**：觀察性資料，以上為相關而非因果。延遲訂單可能同時集中在
> 特定地區／品類；分層後方向若一致，才值得投資改善物流。

## Q5 · 挽回券期望值

損益兩平條件：uplift × 毛利 ≥ 領券率 × 券面額
→ **需要 uplift ≥ {ev['break_even_pp']}pp** 才回本（當前假設下）。

各價值層判定（baseline = 首購後 {P.REPURCHASE_HORIZON_DAYS} 天回購率，作為 uplift 天花板的代理）：

{md_table(ev['tier'])}

Break-even uplift（pp）對假設的敏感度：

{md_table(ev['sensitivity'])}

> 「拒絕決策」不是沒有答案——是這份資料（無隨機實驗）誠實的極限。
> 下一步是小規模 A/B，或見作品集專案一（uplift modeling）。

## 附錄 · 方法與限制

- **customer_id 每單一新值**，全文以 customer_unique_id 為人；驗證見 DATA_NOTES.md
- 窗口 {P.WINDOW_START} ~ {P.WINDOW_END}、只留 delivered；晚期 cohort 觀察期右側截斷
- 回購率極低（{repeat_pct:.1f}%）使 IPT 為倖存者樣本；churn 門檻應隨資料更新滾動重估
- 不建 ML churn 模型：回購正例太少、特徵為單次快照，規則分層已達可行動精度且可解釋
"""
    P.REPORT_PATH.write_text(md)
    print(f'報告已寫入 {P.REPORT_PATH.name}')


def main() -> int:
    P.FIG_DIR.mkdir(parents=True, exist_ok=True)
    if not any(P.DATA_DIR.glob('olist_*.csv')):
        print('data/ 沒有 CSV。先跑 scripts/download_data.py（或手動下載，見 README）')
        return 1

    con = duckdb.connect()
    con.execute(load_sql('00_views.sql'))

    ok, _, val = run_validation(con)
    if not ok:
        print('驗證有 FAIL 項目，停止。修正資料或口徑後重跑。')
        return 1
    if '--validate-only' in sys.argv:
        print('驗證全數通過（--validate-only 模式結束）')
        return 0

    cohort = run_cohort(con)
    ipt = run_ipt(con)
    rfm = run_rfm(con, ipt)
    drivers = run_drivers(con)
    ev = run_ev(drivers)
    write_report(val, cohort, ipt, rfm, drivers, ev)
    print('全流程完成：REPORT.md + reports/figures/*.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
