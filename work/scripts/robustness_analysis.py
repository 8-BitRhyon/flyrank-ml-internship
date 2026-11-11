"""Three-period robustness for the CTR capstone.

Runs the same five-fold client-grouped comparison on three consecutive month
pairs, plus two time-forward transfers, and writes a metrics receipt and figure.

Run from the repo root:
    .venv/bin/python work/scripts/robustness_analysis.py
"""
import json
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from huggingface_hub import get_token
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

BASE = "hf://datasets/FlyRank/internship-warehouse"
KS = [50, 140, 500]
BASIC = ["ctr_pct", "avg_pos", "march_impressions_log", "position_sd", "content_age_days"]
SEED = 42
OUT = Path("work/outputs")
FIG = Path("work/figures")

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute("CREATE OR REPLACE SECRET hf (TYPE huggingface, TOKEN ?)", [get_token()])


def roll(month):
    return f"""
    WITH d AS (
        SELECT client_hash_id, content_hash_id,
               SUM(gsc_impressions) AS imp, SUM(gsc_clicks) AS clk,
               SUM(gsc_sum_position) AS ps,
               SUM(CASE WHEN gsc_avg_position > 0 THEN gsc_impressions END) AS pi,
               COUNT(*) FILTER (WHERE gsc_data_available IS TRUE) AS days_gsc,
               STDDEV_SAMP(CASE WHEN gsc_avg_position > 0 THEN gsc_avg_position END) AS pos_sd
        FROM read_parquet('{BASE}/fact_content_daily_performance/month={month}/data_0.parquet')
        GROUP BY 1, 2
    )
    SELECT client_hash_id, content_hash_id, imp, clk, days_gsc, pos_sd,
           ps / NULLIF(pi, 0) AS avg_pos,
           100.0 * clk / NULLIF(imp, 0) AS ctr_pct
    FROM d
    ORDER BY client_hash_id, content_hash_id
    """


dim = con.execute(f"""
    SELECT client_hash_id, content_hash_id, content_created_date, content_updated_date,
           content_type, main_intent, word_count, search_volume, competition, backlinks
    FROM read_parquet('{BASE}/dim_content.parquet')
""").df()

cache = {}


def month(m):
    if m not in cache:
        cache[m] = con.execute(roll(m)).df()
    return cache[m]


def build(feature_month, prior_month, label_month, as_of):
    feats = month(feature_month)
    prior = month(prior_month)
    nxt = month(label_month)

    f = feats[(feats.imp >= 500) & (feats.days_gsc >= 20) & feats.avg_pos.notna()].copy()
    f["tier"] = pd.cut(f.avg_pos, [0, 3, 10, 20, np.inf],
                       labels=["top_3", "page_1", "page_2", "deep"]).astype(str)
    thresholds = f.groupby("tier").ctr_pct.median()

    prior = prior.rename(columns={"imp": "prior_imp", "ctr_pct": "prior_ctr", "avg_pos": "prior_pos"})[
        ["client_hash_id", "content_hash_id", "prior_imp", "prior_ctr", "prior_pos"]]
    f = f.merge(prior, on=["client_hash_id", "content_hash_id"], how="left")

    nxt = nxt.rename(columns={"imp": "next_imp", "ctr_pct": "next_ctr"})
    f = f.merge(nxt[["client_hash_id", "content_hash_id", "next_imp", "next_ctr"]],
                on=["client_hash_id", "content_hash_id"], how="inner")
    f = f[(f.next_imp >= 100) & f.next_ctr.notna()].copy()
    f["label"] = (f.next_ctr < f.tier.map(thresholds)).astype(int)

    f = f.merge(dim, on=["client_hash_id", "content_hash_id"], how="left")
    f["content_age_days"] = (pd.Timestamp(as_of) - pd.to_datetime(f.content_created_date)).dt.days
    f["days_since_update"] = (pd.Timestamp(as_of) - pd.to_datetime(f.content_updated_date)).dt.days
    f["march_impressions_log"] = np.log1p(f.imp)
    f["position_sd"] = f.pos_sd.fillna(0)
    f["ctr_delta"] = f.ctr_pct - f.prior_ctr
    f["pos_delta"] = f.avg_pos - f.prior_pos
    f["imp_log_ratio"] = np.log1p(f.imp) - np.log1p(f.prior_imp)
    f["log_word_count"] = np.log1p(f.word_count)
    f["has_word_count"] = f.word_count.notna().astype(int)
    f["log_search_volume"] = np.log1p(f.search_volume)
    f["log_backlinks"] = np.log1p(f.backlinks)
    f["has_prior"] = f.prior_ctr.notna().astype(int)
    f["tier_median_ctr"] = f.tier.map(thresholds)
    f = f.sort_values(["client_hash_id", "content_hash_id"]).reset_index(drop=True)
    cats = pd.get_dummies(f[["content_type", "main_intent"]].fillna("unknown"), dtype=int)
    f = pd.concat([f.reset_index(drop=True), cats.reset_index(drop=True)], axis=1)
    return f, list(cats.columns)


def p_at(scores, labels, k):
    order = np.argsort(-np.asarray(scores))
    return float(np.asarray(labels)[order[:k]].mean())


def cv(frame, rich):
    Xb = frame[BASIC].fillna(0)
    Xr = frame[rich].fillna(0)
    y = frame.label
    g = frame.client_hash_id
    rule = ((frame.tier_median_ctr - frame.ctr_pct).clip(lower=0) * frame.imp / 100).to_numpy()
    rows = []
    for tr, te in GroupKFold(n_splits=5).split(Xb, y, groups=g):
        yt = y.iloc[te].to_numpy()
        rec = {"rule": {k: p_at(rule[te], yt, k) for k in KS}}
        for name, X in [("basic", Xb), ("rich", Xr)]:
            model = HistGradientBoostingClassifier(max_iter=300, random_state=SEED)
            model.fit(X.iloc[tr], y.iloc[tr])
            s = model.predict_proba(X.iloc[te])[:, 1]
            rec[name] = {k: p_at(s, yt, k) for k in KS}
        rows.append(rec)
    return {name: {str(k): float(np.mean([r[name][k] for r in rows])) for k in KS}
            for name in ["rule", "basic", "rich"]}


p1, cats = build("2026-01", "2025-12", "2026-02", "2026-01-31")
p2, _ = build("2026-02", "2026-01", "2026-03", "2026-02-28")
p3, _ = build("2026-03", "2026-02", "2026-04", "2026-03-31")
RICH = BASIC + ["ctr_delta", "pos_delta", "imp_log_ratio", "prior_ctr", "prior_pos",
                "log_word_count", "has_word_count", "log_search_volume", "competition",
                "log_backlinks", "days_since_update", "has_prior"] + cats

results = {
    "2026-01 into 2026-02": cv(p1, RICH),
    "2026-02 into 2026-03": cv(p2, RICH),
    "2026-03 into 2026-04": cv(p3, RICH),
}

transfers = {}
for label, train, test in [("Jan-Feb into Feb-Mar", p1, p2), ("Feb-Mar into Mar-Apr", p2, p3)]:
    model = HistGradientBoostingClassifier(max_iter=300, random_state=SEED).fit(
        train[RICH].fillna(0), train.label
    )
    s = model.predict_proba(test[RICH].fillna(0))[:, 1]
    rule = ((test.tier_median_ctr - test.ctr_pct).clip(lower=0) * test.imp / 100).to_numpy()
    yt = test.label.to_numpy()
    transfers[label] = {
        "rows": int(len(test)),
        "rule": {str(k): p_at(rule, yt, k) for k in KS},
        "rich": {str(k): p_at(s, yt, k) for k in KS},
    }

fig, ax = plt.subplots(figsize=(8, 4.4))
periods = list(results.keys())
x = np.arange(len(periods))
for i, name in enumerate(["rule", "basic", "rich"]):
    vals = [results[p][name]["140"] for p in periods]
    ax.bar(x + (i - 1) * 0.26, vals, 0.26, label=name,
           color={"rule": "#c00000", "basic": "#7f7f7f", "rich": "#1f4e79"}[name])
ax.set_xticks(x)
ax.set_xticklabels(["Jan to Feb", "Feb to Mar", "Mar to Apr"])
ax.set_ylim(0.90, 1.01)
ax.set_ylabel("precision@140")
ax.set_title("Three consecutive periods, five-fold grouped CV")
ax.legend()
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / "three_periods.png", dpi=150)
plt.close(fig)

payload = {"periods": results, "time_forward": transfers}
(OUT / "robustness_metrics.json").write_text(json.dumps(payload, indent=2) + "\n")

print(json.dumps(payload, indent=2))
