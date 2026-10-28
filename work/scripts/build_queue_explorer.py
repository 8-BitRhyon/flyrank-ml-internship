"""Build the static queue explorer page from the playbook queue.

Run from the repo root:
    .venv/bin/python work/scripts/build_queue_explorer.py
"""
from pathlib import Path

import pandas as pd

SRC = Path("work/outputs/action_playbook_queue.csv")
OUT = Path("docs/queue/index.html")
TOP_N = 200

df = pd.read_csv(SRC).head(TOP_N)

rows = []
for _, r in df.iterrows():
    rows.append(
        f'<tr data-archetype="{r.archetype}" data-tier="{r.tier}">'
        f"<td class='num'>{int(r['rank'])}</td>"
        f"<td>{r.tier}</td>"
        f"<td class='num'>{int(r.imp):,}</td>"
        f"<td class='num'>{int(r.clk):,}</td>"
        f"<td class='num'>{r.ctr_pct:.2f}%</td>"
        f"<td class='num'>{r.avg_pos:.1f}</td>"
        f"<td class='num'>{int(r.age_days):,}</td>"
        f"<td class='num'>{r.gap:,.0f}</td>"
        f"<td><span class='tag {r.archetype}'>{r.archetype}</span></td>"
        f"<td>{r.action}</td>"
        "</tr>"
    )
body = "\n".join(rows)

counts = df.archetype.value_counts()
total_gap = df.gap.sum()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Queue Explorer - Which Pages First?</title>
<style>
  :root {{ --ink:#1b1b1b; --muted:#5b5b5b; --rule:#d9d5cc; --paper:#fbfaf7;
    --accent:#1f4e79; --prime:#1f4e79; --aged:#8a5a00; --verify:#8a2b2b; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:48px 22px 70px; }}
  .eyebrow {{ font-size:12px; letter-spacing:.14em; text-transform:uppercase;
    color:var(--accent); font-weight:700; margin:0 0 12px; }}
  h1 {{ font-size:34px; margin:0 0 10px; line-height:1.15; }}
  .sub {{ color:var(--muted); font-size:17px; margin:0 0 22px; line-height:1.5; max-width:760px; }}
  .stats {{ display:flex; gap:22px; flex-wrap:wrap; margin:0 0 22px; font-size:14px; color:var(--muted); }}
  .stats b {{ color:var(--ink); font-size:18px; display:block; }}
  .filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:0 0 14px; }}
  button {{ border:1px solid var(--rule); background:#fff; color:var(--ink); padding:7px 12px;
    border-radius:999px; font-size:13px; cursor:pointer; }}
  button.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; background:#fff; }}
  th, td {{ padding:8px 9px; border-bottom:1px solid var(--rule); text-align:left; }}
  th {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
    background:#f4f1ea; position:sticky; top:0; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  tr:hover td {{ background:#f8f6f1; }}
  .tag {{ display:inline-block; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:700; color:#fff; }}
  .CTR_GAP_PRIME {{ background:var(--prime); }}
  .CTR_GAP_AGED {{ background:var(--aged); }}
  .VERIFY_FIRST {{ background:var(--verify); }}
  a {{ color:var(--accent); }}
  .foot {{ margin-top:18px; font-size:12px; color:var(--muted); line-height:1.6; }}
  @media (max-width:760px) {{ .wrap {{ padding:30px 14px 50px; }} h1 {{ font-size:26px; }}
    table {{ font-size:12px; }} th, td {{ padding:6px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">FlyRank ML Internship &middot; Capstone</p>
  <h1>Queue Explorer</h1>
  <p class="sub">
    The top {TOP_N} pages from the March 2026 CTR opportunity queue. Each row shows why it is here:
    the click gap against its position tier, the reason code, and the action a reviewer takes.
  </p>
  <div class="stats">
    <div><b>{len(df):,}</b>pages shown</div>
    <div><b>{total_gap:,.0f}</b>clicks of gap in these rows</div>
    <div><b>{counts.get('CTR_GAP_PRIME', 0)}</b>prime snippet gaps</div>
    <div><b>{counts.get('CTR_GAP_AGED', 0)}</b>aged gaps</div>
    <div><b>{counts.get('VERIFY_FIRST', 0)}</b>tracking checks</div>
  </div>
  <div class="filters">
    <button class="active" data-filter="all">All</button>
    <button data-filter="CTR_GAP_PRIME">Prime</button>
    <button data-filter="CTR_GAP_AGED">Aged</button>
    <button data-filter="VERIFY_FIRST">Verify first</button>
    <button data-filter="top_3">Top 3</button>
    <button data-filter="page_1">Page 1</button>
    <button data-filter="page_2">Page 2</button>
  </div>
  <table>
    <thead><tr>
      <th class="num">Rank</th><th>Tier</th><th class="num">Impressions</th><th class="num">Clicks</th>
      <th class="num">CTR</th><th class="num">Position</th><th class="num">Age</th>
      <th class="num">Gap</th><th>Reason</th><th>Action</th>
    </tr></thead>
    <tbody id="rows">
{body}
    </tbody>
  </table>
  <p class="foot">
    Public-safe view. No client names, domains, URLs, or queries appear here. Identifiers are omitted.
    The queue is decision-support, not a forecast. Read the
    <a href="../paper/">paper</a> for the method, the validation, and the limits.
  </p>
</div>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const rows = document.querySelectorAll('#rows tr');
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    rows.forEach(row => {{
      const show = f === 'all' || row.dataset.archetype === f || row.dataset.tier === f;
      row.style.display = show ? '' : 'none';
    }});
  }}));
</script>
</body>
</html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html)
print(f"wrote {OUT} with {len(df)} rows")
