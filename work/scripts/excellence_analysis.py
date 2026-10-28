"""Excellence analysis for the FlyRank capstone.

Builds the rich feature frame, runs five-fold grouped CV for the rule, the basic
model, and the rich model, repeats on an earlier period, runs a client bootstrap,
and writes metrics plus figures.

Run from the repo root:
    .venv/bin/python work/scripts/excellence_analysis.py
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
KS = [25, 50, 100, 140, 250, 500, 1000, 2000, 5000]
BASIC = ["ctr_pct", "avg_pos", "march_impressions_log", "position_sd", "content_age_days"]
SEED = 42
OUT = Path("work/outputs")
FIG = Path("work/figures")
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

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


late, cat_cols = build("2026-03", "2026-02", "2026-04", "2026-03-31")
early, _ = build("2026-01", "2025-12", "2026-02", "2026-01-31")

RICH = BASIC + ["ctr_delta", "pos_delta", "imp_log_ratio", "prior_ctr", "prior_pos",
                "log_word_count", "has_word_count", "log_search_volume", "competition",
                "log_backlinks", "days_since_update", "has_prior"] + cat_cols


def p_at(scores, labels, k):
    order = np.argsort(-np.asarray(scores))
    return float(np.asarray(labels)[order[:k]].mean())


def rule_score(frame):
    return ((frame.tier_median_ctr - frame.ctr_pct).clip(lower=0) * frame.imp / 100).to_numpy()


def cv_curve(frame, label):
    """Five-fold grouped CV for the rule, basic, and rich models."""
    Xb = frame[BASIC].fillna(0)
    Xr = frame[RICH].fillna(0)
    y = frame.label
    g = frame.client_hash_id
    rule = rule_score(frame)
    folds = []
    oof = {"rule": rule.copy(), "basic": np.zeros(len(frame)), "rich": np.zeros(len(frame))}
    for tr, te in GroupKFold(n_splits=5).split(Xb, y, groups=g):
        yt = y.iloc[te].to_numpy()
        rec = {}
        for name, X in [("basic", Xb), ("rich", Xr)]:
            model = HistGradientBoostingClassifier(max_iter=300, random_state=SEED)
            model.fit(X.iloc[tr], y.iloc[tr])
            s = model.predict_proba(X.iloc[te])[:, 1]
            oof[name][te] = s
            rec[name] = {k: p_at(s, yt, k) for k in KS}
        rec["rule"] = {k: p_at(rule[te], yt, k) for k in KS}
        folds.append(rec)
    summary = {}
    for name in ["rule", "basic", "rich"]:
        summary[name] = {
            str(k): {
                "mean": float(np.mean([f[name][k] for f in folds])),
                "sd": float(np.std([f[name][k] for f in folds])),
            }
            for k in KS
        }
    return summary, oof, folds


late_cv, late_oof, _ = cv_curve(late, "late")
early_cv, early_oof, _ = cv_curve(early, "early")

# Time-forward: train on the early period, test on the late period.
Xr_late = late[RICH].fillna(0)
Xb_late = late[BASIC].fillna(0)
forward = {}
for name, Xtr, Xte in [("basic", early[BASIC].fillna(0), Xb_late),
                       ("rich", early[RICH].fillna(0), Xr_late)]:
    model = HistGradientBoostingClassifier(max_iter=300, random_state=SEED)
    model.fit(Xtr, early.label)
    s = model.predict_proba(Xte)[:, 1]
    forward[name] = {str(k): p_at(s, late.label.to_numpy(), k) for k in KS}
forward["rule"] = {str(k): p_at(rule_score(late), late.label.to_numpy(), k) for k in KS}

# Client bootstrap on out-of-fold predictions.
rng = np.random.default_rng(SEED)
clients = late.client_hash_id.to_numpy()
y_late = late.label.to_numpy()
boot = {}
for k in [50, 140]:
    gaps = []
    for _ in range(1000):
        pick = rng.choice(np.unique(clients), size=len(np.unique(clients)), replace=True)
        idx = np.concatenate([np.where(clients == c)[0] for c in pick])
        gaps.append(p_at(late_oof["rich"][idx], y_late[idx], k) - p_at(late_oof["rule"][idx], y_late[idx], k))
    gaps = np.asarray(gaps)
    boot[str(k)] = {
        "mean_gap": float(gaps.mean()),
        "ci_low": float(np.percentile(gaps, 2.5)),
        "ci_high": float(np.percentile(gaps, 97.5)),
        "prob_gap_positive": float((gaps > 0).mean()),
    }

# Figures.
colors = {"rule": "#c00000", "basic": "#7f7f7f", "rich": "#1f4e79"}
fig, ax = plt.subplots(figsize=(8.2, 4.6))
for name in ["rule", "basic", "rich"]:
    means = [late_cv[name][str(k)]["mean"] for k in KS]
    sds = [late_cv[name][str(k)]["sd"] for k in KS]
    ax.plot(KS, means, marker="o", label=name, color=colors[name], lw=2)
    ax.fill_between(KS, np.array(means) - np.array(sds), np.array(means) + np.array(sds),
                    color=colors[name], alpha=0.10)
ax.set_xscale("log")
ax.set_xlabel("pages reviewed (K, log scale)")
ax.set_ylabel("precision at K")
ax.set_title("Model vs rule at every review budget, five-fold grouped CV")
ax.legend(title="method")
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / "k_curve.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8.2, 4.2))
width = 0.25
positions = np.arange(3)
for i, name in enumerate(["rule", "basic", "rich"]):
    vals = [late_cv[name][str(k)]["mean"] for k in [50, 140, 500]]
    ax.bar(positions + (i - 1) * width, vals, width, label=name, color=colors[name])
ax.set_xticks(positions)
ax.set_xticklabels(["K=50", "K=140", "K=500"])
ax.set_ylim(0.90, 1.01)
ax.set_ylabel("precision at K")
ax.set_title("What the extra features buy at realistic budgets")
ax.legend()
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / "ablation.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 4.0))
labels = ["K=50", "K=140"]
means = [boot["50"]["mean_gap"], boot["140"]["mean_gap"]]
low = [boot["50"]["ci_low"], boot["140"]["ci_low"]]
high = [boot["50"]["ci_high"], boot["140"]["ci_high"]]
ax.errorbar(labels, means, yerr=[np.array(means) - np.array(low), np.array(high) - np.array(means)],
            fmt="o", color="#1f4e79", capsize=8, lw=2, markersize=8)
ax.axhline(0, color="#c00000", ls="--", lw=1)
ax.set_ylabel("rich model minus rule, precision at K")
ax.set_title("Client bootstrap, 95% interval")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / "bootstrap_gap.png", dpi=150)
plt.close(fig)

metrics = {
    "ks": KS,
    "late_rows": int(len(late)),
    "early_rows": int(len(early)),
    "late_clients": int(late.client_hash_id.nunique()),
    "basic_features": BASIC,
    "rich_features": RICH,
    "late_cv": late_cv,
    "early_cv": early_cv,
    "time_forward": forward,
    "bootstrap": boot,
}
(OUT / "excellence_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

rows = []
for period, cv in [("late", late_cv), ("early", early_cv)]:
    for name in ["rule", "basic", "rich"]:
        for k in KS:
            rows.append({"period": period, "method": name, "k": k,
                         "mean": cv[name][str(k)]["mean"], "sd": cv[name][str(k)]["sd"]})
pd.DataFrame(rows).to_csv(OUT / "excellence_kcurve.csv", index=False)

print(json.dumps({
    "late_cv_50": {n: round(late_cv[n]["50"]["mean"], 4) for n in ["rule", "basic", "rich"]},
    "late_cv_140": {n: round(late_cv[n]["140"]["mean"], 4) for n in ["rule", "basic", "rich"]},
    "late_cv_500": {n: round(late_cv[n]["500"]["mean"], 4) for n in ["rule", "basic", "rich"]},
    "early_cv_140": {n: round(early_cv[n]["140"]["mean"], 4) for n in ["rule", "basic", "rich"]},
    "time_forward_140": {n: round(forward[n]["140"], 4) for n in ["rule", "basic", "rich"]},
    "bootstrap": boot,
}, indent=2))
print("wrote figures and metrics")
