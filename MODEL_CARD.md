# Model Card: CTR Opportunity Ranker

**Version:** 1.0
**Date:** 2026-10-30
**Owner:** Rhyon Caleb Foz-Santos, FlyRank ML Internship
**Paper:** https://8-bitrhyon.github.io/flyrank-ml-internship/paper/
**Code:** `work/scripts/excellence_analysis.py`, `work/notebooks/capstone.ipynb`

## What this model does

It ranks content page-months for manual CTR review. One row is one page for one client in one
calendar month. The score estimates how far a page's CTR sits below the median for its position tier,
weighted by impressions. A reviewer works down the queue and rewrites the title and meta description.

## Intended use

- Decision-support for a content editor with a review budget of 50 to 500 pages.
- Ordering pages by expected CTR gap against position-tier peers.
- Pairing each page with a reason code and an action label.

## Out of scope

- Automated title, meta, or content changes. A human reviews every page.
- Publishing or bulk edits without a 10% sample review.
- Client-facing promises, revenue estimates, or ranking guarantees.
- Editor performance reviews. The score measures pages, not people.
- Deep pages (position above 20), pages below 500 impressions, and pages without position data.
- Any use of the sealed June 2026 partition in development.

## Model

| Item | Value |
|---|---|
| Type | Gradient-boosted classifier, `HistGradientBoostingClassifier` |
| Task | Binary ranking, scored by predicted probability |
| Features | 25: 5 base, 5 prior-month trend, 6 content metadata, 6 categorical, 3 flags |
| Label | `low_ctr_next`, April CTR below the March tier median, at least 100 April impressions |
| Training rows | 58,477 page-months, 31 clients |
| Seed | 42 |

## Performance

Five-fold client-grouped CV, March 2026 features into April 2026 labels.

| Method | Precision@50 | Precision@140 | Precision@500 |
|---|---:|---:|---:|
| Value rule | 0.956 | 0.966 | 0.939 |
| Base model, 5 features | 0.972 | 0.967 | 0.949 |
| This model, 25 features | 1.000 | 0.987 | 0.954 |

- Bootstrap 95% interval on the gap over the rule at K=140: **+1.4 to +10.0 points**.
- Time-forward test, trained on January-February and tested on March-April: **0.971 at K=140**, against **0.943** for the rule.
- Top-140 misses fall from about 5 to about 2 per 140 reviewed.

## Limits

- **Budget reversal.** Under the time-forward test the rule wins at K=5000, 0.934 against 0.912.
- **Period sensitivity.** The January replication is unstable, with wide fold variance.
- **Coverage.** 48,725 of 331,437 March page-months (14.7%) are in scope.
- **Tier-relative label.** A page with a healthy absolute CTR can be flagged if it falls below a low tier median.
- **Population selection.** The 100-impression April floor drops 829 of 59,306 eligible pages (1.4%).
- **No engagement.** GA4 is available on 4.21% of March rows, so on-page experience is outside the model.
- **No causal claim.** The score identifies an association, not a proven lift from a rewrite.

## Maintenance

- Recompute tier medians and the queue every month. Do not reuse last month's ranks.
- Retrain if next-month precision@140 falls below 0.90.
- Revisit the model if the review budget grows beyond 1,000 pages, where the rule is competitive.
- Revisit the engagement exclusion if GA4 coverage rises above 50% of rows.

## Reproduction

```bash
export HF_TOKEN=...
python work/scripts/excellence_analysis.py
python work/scripts/build_queue_explorer.py
```

Metrics receipts: `work/outputs/excellence_metrics.json`, `work/outputs/capstone_metrics.json`.
