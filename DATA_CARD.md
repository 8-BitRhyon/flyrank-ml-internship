# Data Card: FlyRank Internship Warehouse

**Version:** build `v20260703`
**Date:** 2026-10-30
**Owner:** Rhyon Caleb Foz-Santos, FlyRank ML Internship
**Source:** https://huggingface.co/datasets/FlyRank/internship-warehouse

## What this dataset is

A pseudonymized star schema of search performance for content pages. It is gated on Hugging Face.
Access needs a Read token with access to the gated repository. No client names, domains, URLs, or
raw queries are included.

## Tables

| Table | Grain | Rows | Use here |
|---|---:|---:|---|
| `fact_content_daily_performance` | report date x client x content | 78,835,655 | Features and labels |
| `dim_content` | one row per content item | 519,606 | Age, type, intent, depth, volume, links |
| `dim_clients` | one row per client | 104 | Coverage context |

The fact table is partitioned by month. This study reads March 2026 (9,841,378 rows), April 2026,
February 2026, January 2026, and December 2025. June 2026 is the sealed final month and was never
read for development.

## Windows

| Purpose | Feature month | Prior month | Label month |
|---|---|---|---|
| Primary | 2026-03 | 2026-02 | 2026-04 |
| Replication | 2026-01 | 2025-12 | 2026-02 |
| Sealed | not used | not used | 2026-06 |

## Inclusion rules

- At least 500 March impressions.
- At least 20 March days with GSC data.
- A real position value. `avg_position = 0` means no position data, not rank zero.
- At least 100 April impressions for the label.
- Position tier is cut at 3, 10, and 20.

## Exclusions

- **GA4 engagement.** `ga4_data_available IS TRUE` on only 4.21% of March rows, and coverage is patchy inside a page.
- **Query table.** `fact_content_query_90d` has a 90-day window that overlaps the feature and label months.
- **Identifiers.** Client and content hashes are context only, never features.
- **Product flags.** No FlyRank flag or health score is used as a feature.

## Known issues

- **Unbalanced panel.** History depth differs by client. `dim_clients.gsc_data_start` is the honest start date.
- **Three-valued availability.** `gsc_data_available` and `ga4_data_available` can be TRUE, FALSE, or NULL. Always filter with `IS TRUE`.
- **Outcome-dependent cohort.** The April 100-impression floor drops 829 of 59,306 eligible pages (1.4%). This is disclosed in the paper.
- **Tier-relative label.** A page with a healthy absolute CTR can be flagged if it falls below a low tier median.

## Public safety

- All identifiers are salted hashes.
- No client names, domains, URLs, or private queries appear in this repository.
- Figures and tables report aggregates only.
- The data is not redistributed. The repository stores code, metrics, and figures, not raw rows.

## Citation

Built on the FlyRank ML Internship dataset: https://flyrank.ai
