# Decision Memo: Which Pages First?

**For:** a content editor or team lead with a fixed review budget.
**Date:** 2026-10-30
**Paper:** https://8-bitrhyon.github.io/flyrank-ml-internship/paper/

## The decision

You can review about 140 pages over seven weeks. Which pages do you open first?

## The recommendation

Use the 25-feature model at 50 to 500 reviews. Use the value rule above 1,000 reviews, because its
stability wins once the queue reaches deep pages. Both feed the same human-reviewed playbook.

| Budget | Use | Reason |
|---|---|---|
| 50 to 500 reviews | Model | Precision@140 0.987 against 0.966 for the rule |
| Above 1,000 reviews | Rule | The model falls behind at K=5000 under a time-forward test |

## What the queue looks like

Each row carries one reason code and one action.

| Archetype | Reason code | Action |
|---|---|---|
| Near-zero CTR at volume | `VERIFY_FIRST` | Check tracking and query mix before any edit |
| Aged snippet gap, 270+ days | `CTR_GAP_AGED` | Refresh the page, then rewrite the snippet |
| Prime snippet gap | `CTR_GAP_PRIME` | Rewrite the title and meta description |

The top 140 carries about 11,700 clicks of expected gap, 12.1% of the in-scope gap. At an assumed 1.5
hours per review, that is about 210 editor-hours, or 84 clicks of gap per review.

## What a reviewer checks before acting

1. The query report. Can the page answer the queries that bring the impressions?
2. The SERP. Is a featured snippet or AI answer absorbing the click?
3. Tracking. For `VERIFY_FIRST` pages, confirm the clicks are really zero.
4. Recency. Has the page been edited in the last 30 days?
5. Ownership. Is the client already changing the page?

## What not to automate

- No automatic title or meta changes, and no publishing.
- No bulk edits without a 10% sample review.
- No client-facing promises or revenue estimates.
- No editor performance reviews.
- No deep pages in a CTR queue.
- No June 2026 data in development.

## What would make this wrong

- The query mix has no click intent, so a better snippet cannot recover the gap.
- The zero-click pattern is a tracking failure, not a content problem.
- The page is a duplicate or redirect that should be consolidated, not rewritten.
- The review budget is large enough that the rule is the better queue.

## Monitoring

- Recompute tier medians and the queue every month.
- If the next-month precision@140 falls below 0.90, revisit the rule or the model.
- If the near-zero share in the top 140 rises above 10%, run a tracking audit.
- If GA4 coverage rises above 50% of rows, revisit the engagement exclusion.

## Where to look

- Paper: https://8-bitrhyon.github.io/flyrank-ml-internship/paper/
- Queue explorer: https://8-bitrhyon.github.io/flyrank-ml-internship/queue/
- Queue builder: https://8-bitrhyon.github.io/flyrank-ml-internship/tool/
- Live API: https://flyrank-ctr-queue.rhyonfs.workers.dev/queue?limit=5
- Model card: `MODEL_CARD.md`
- Data card: `DATA_CARD.md`
- Reproduce: `work/scripts/reproduce.sh`
