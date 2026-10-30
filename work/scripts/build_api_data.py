"""Generate the Worker dataset from the playbook queue.

Run from the repo root:
    .venv/bin/python work/scripts/build_api_data.py
"""
import json
from pathlib import Path

import pandas as pd

SRC = Path("work/outputs/action_playbook_queue.csv")
OUT = Path("work/api/src/data.js")
TOP_N = 200

df = pd.read_csv(SRC).head(TOP_N)

rows = []
for _, r in df.iterrows():
    rows.append({
        "rank": int(r["rank"]),
        "tier": r["tier"],
        "impressions": int(r["imp"]),
        "clicks": int(r["clk"]),
        "ctr_pct": round(float(r["ctr_pct"]), 4),
        "avg_position": round(float(r["avg_pos"]), 2),
        "age_days": int(r["age_days"]),
        "expected_click_gap": round(float(r["gap"]), 2),
        "archetype": r["archetype"],
        "action": r["action"],
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("export default " + json.dumps(rows, indent=2) + ";\n")
print(f"wrote {OUT} with {len(rows)} rows")
