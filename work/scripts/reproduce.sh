#!/usr/bin/env bash
# Regenerate the excellence analysis, the queue explorer, and the capstone notebook.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -z "${HF_TOKEN:-}" ]; then
  echo "Set HF_TOKEN to a Hugging Face read token before running." >&2
  exit 1
fi

.venv/bin/python work/scripts/excellence_analysis.py
.venv/bin/python work/scripts/build_queue_explorer.py
.venv/bin/jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=flyrank \
  --ExecutePreprocessor.timeout=2400 \
  work/notebooks/capstone.ipynb

echo "Regenerated metrics, figures, queue explorer, and the capstone notebook."
