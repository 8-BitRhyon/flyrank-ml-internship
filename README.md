# Which Pages First?

A CTR opportunity model for content review, built on 9.8 million daily rows from the
[FlyRank ML Internship](https://flyrank.ai) warehouse.

**Paper:** https://8-bitrhyon.github.io/flyrank-ml-internship/paper/
**Queue explorer:** https://8-bitrhyon.github.io/flyrank-ml-internship/queue/

## The result

A content team can review about 140 pages over seven weeks. The question is which pages come first.
A transparent CTR-gap rule is a strong baseline. A 25-feature gradient-boosted model beats it at
realistic budgets, and the gain survives a time-forward test.

| Method | Precision@50 | Precision@140 | Time-forward @140 |
|---|---:|---:|---:|
| Value rule | 0.956 | 0.966 | 0.943 |
| Base model, 5 features | 0.972 | 0.967 | 0.914 |
| Rich model, 25 features | 1.000 | 0.987 | 0.971 |

Five-fold client-grouped CV, March 2026 features into April 2026 labels. The rich model is 5.5 points
above the rule at K=140, with a client-bootstrap 95% interval of +1.4 to +10.0. The base model ties
the rule in-period and falls below it time-forward, so the gain comes from features, not from model
class. At K=5000 the rule wins under the time-forward test, so the recommendation is budget-dependent.

## What is in this repo

| Path | Content |
|---|---|
| `docs/paper/` | The deployed research paper |
| `docs/queue/` | The static queue explorer |
| `work/notebooks/` | Executed assignment notebooks and the capstone |
| `work/scripts/excellence_analysis.py` | Rich features, five-fold CV, bootstrap, two-period replication |
| `work/scripts/build_queue_explorer.py` | Builds the queue explorer page |
| `work/outputs/*.json` | Metrics receipts for every number in the paper |
| `work/figures/` | Figures used in the paper |

The queue CSV stays out of git by design. The CI leak guard blocks data files, and the scripts
regenerate it.

## Reproduce

```bash
python -m venv .venv
. .venv/bin/activate
pip install duckdb pandas numpy scikit-learn matplotlib huggingface_hub jupyter nbformat

export HF_TOKEN=...   # Hugging Face read token with access to the gated warehouse

python work/scripts/excellence_analysis.py
python work/scripts/build_queue_explorer.py
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=flyrank \
  --ExecutePreprocessor.timeout=2400 \
  work/notebooks/capstone.ipynb
```

Seeds are fixed at 42. Row order is sorted before every split. The metrics receipts are
`work/outputs/excellence_metrics.json`, `work/outputs/capstone_metrics.json`, and
`work/outputs/ml10_playbook_metrics.json`.

## Data and safety

The warehouse is a pseudonymized, gated release. All identifiers are salted hashes. No client names,
domains, URLs, or private queries appear in this repository, its figures, or the paper. The June 2026
partition stays sealed and is never used for development.

Claims are observed, measured, directional, or decision-support. No causal claim is made without an
experiment.
