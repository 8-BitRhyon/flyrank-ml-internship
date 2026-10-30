import rows, { stats } from "./data.js";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const PAPER = "https://8-bitrhyon.github.io/flyrank-ml-internship/paper/";
const EXPLORER = "https://8-bitrhyon.github.io/flyrank-ml-internship/queue/";
const BASE = "https://flyrank-ctr-queue.rhyonfs.workers.dev";

function json(data, status = 200, cache = "public, max-age=300") {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": cache,
      ...CORS,
    },
  });
}

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300",
      ...CORS,
    },
  });
}

function normalize(pathname) {
  const stripped = pathname.replace(/^\/v1(?=\/|$)/, "");
  return stripped === "" ? "/" : stripped;
}

function landing() {
  const top = rows.slice(0, 10);
  const tr = top
    .map(
      (r) => `<tr>
        <td class="n">${r.rank}</td><td>${r.tier}</td>
        <td class="n">${r.impressions.toLocaleString("en-US")}</td>
        <td class="n">${r.ctr_pct.toFixed(2)}%</td>
        <td class="n">${r.avg_position.toFixed(1)}</td>
        <td class="n">${r.expected_click_gap.toLocaleString("en-US")}</td>
        <td><span class="tag ${r.archetype}">${r.archetype}</span></td>
        <td>${r.action}</td>
      </tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CTR Opportunity Queue API</title>
<style>
  :root { --ink:#1b1b1b; --muted:#5b5b5b; --rule:#d9d5cc; --paper:#fbfaf7; --accent:#1f4e79; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
    font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height:1.6; }
  .wrap { max-width:1000px; margin:0 auto; padding:48px 22px 70px; }
  .eyebrow { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:700; margin:0 0 12px; }
  h1 { font-size:34px; margin:0 0 10px; }
  .sub { color:var(--muted); font-size:17px; margin:0 0 22px; max-width:760px; }
  .links { display:flex; gap:10px; flex-wrap:wrap; margin:0 0 26px; }
  .links a { display:inline-block; border:1px solid var(--rule); background:#fff; color:var(--accent);
    text-decoration:none; padding:8px 12px; border-radius:6px; font-size:14px; }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:0 0 30px; }
  .card { background:#fff; border:1px solid var(--rule); padding:14px; }
  .card b { display:block; font-size:24px; color:var(--accent); line-height:1.1; }
  .card span { font-size:12px; color:var(--muted); }
  h2 { font-size:20px; margin:32px 0 10px; }
  code { font-family:ui-monospace, SFMono-Regular, Menlo, monospace; background:#f1efe9; padding:2px 5px; border-radius:3px; font-size:0.9em; }
  table { width:100%; border-collapse:collapse; font-size:13px; background:#fff; }
  th, td { padding:8px 9px; border-bottom:1px solid var(--rule); text-align:left; }
  th { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); background:#f4f1ea; }
  td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; }
  .tag { display:inline-block; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:700; color:#fff; }
  .CTR_GAP_PRIME { background:#1f4e79; } .CTR_GAP_AGED { background:#8a5a00; } .VERIFY_FIRST { background:#8a2b2b; }
  .foot { margin-top:20px; font-size:12px; color:var(--muted); }
  @media (max-width:720px) { h1 { font-size:26px; } .cards { grid-template-columns:repeat(2,1fr); } table { font-size:12px; } th, td { padding:6px; } }
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">FlyRank ML Internship &middot; Capstone</p>
  <h1>CTR Opportunity Queue API</h1>
  <p class="sub">A JSON endpoint for the March 2026 ranked queue. Decision-support for content review,
  not a forecast. Each row carries a reason code and an action.</p>
  <div class="links">
    <a href="${PAPER}">Read the paper</a>
    <a href="${EXPLORER}">Browse the queue</a>
    <a href="/queue?limit=5">JSON: /queue?limit=5</a>
    <a href="/stats">JSON: /stats</a>
    <a href="/openapi.json">OpenAPI spec</a>
  </div>

  <div class="cards">
    <div class="card"><b>${stats.in_scope_pages.toLocaleString("en-US")}</b><span>pages in scope</span></div>
    <div class="card"><b>${stats.top140_gap_clicks.toLocaleString("en-US")}</b><span>clicks of gap in the top 140</span></div>
    <div class="card"><b>${stats.top140_share_pct}%</b><span>of the in-scope gap</span></div>
    <div class="card"><b>${stats.top140_archetypes.CTR_GAP_AGED}</b><span>aged pages in the top 140</span></div>
  </div>

  <h2>Endpoints</h2>
  <table>
    <thead><tr><th>Path</th><th>Returns</th></tr></thead>
    <tbody>
      <tr><td><code>/queue?limit=20</code></td><td>Ranked rows. Optional <code>tier</code>, <code>archetype</code>, and <code>offset</code>.</td></tr>
      <tr><td><code>/queue?tier=page_1</code></td><td>Filter by position tier: <code>top_3</code>, <code>page_1</code>, <code>page_2</code>.</td></tr>
      <tr><td><code>/queue?archetype=CTR_GAP_AGED</code></td><td>Filter by reason code.</td></tr>
      <tr><td><code>/stats</code></td><td>Aggregate numbers for the queue and the paper.</td></tr>
      <tr><td><code>/health</code></td><td>Service status and row count.</td></tr>
      <tr><td><code>/openapi.json</code></td><td>OpenAPI 3.1 spec.</td></tr>
      <tr><td><code>/v1/queue</code></td><td>Versioned alias of every endpoint.</td></tr>
    </tbody>
  </table>

  <h2>Top 10 rows</h2>
  <table>
    <thead><tr><th class="n">Rank</th><th>Tier</th><th class="n">Impressions</th><th class="n">CTR</th>
    <th class="n">Position</th><th class="n">Gap</th><th>Reason</th><th>Action</th></tr></thead>
    <tbody>${tr}</tbody>
  </table>
  <p class="foot">No client names, domains, URLs, or queries. Identifiers are omitted. The full
  method, validation, and limits are in the <a href="${PAPER}">paper</a>.</p>
</div>
</body>
</html>`;
}

function openapi() {
  return {
    openapi: "3.1.0",
    info: {
      title: "FlyRank CTR Opportunity Queue",
      version: "1.0.0",
      description: "Ranked page-months for manual CTR review. Decision-support, not a forecast.",
    },
    servers: [{ url: BASE }],
    paths: {
      "/queue": {
        get: {
          summary: "Ranked queue rows",
          parameters: [
            { name: "limit", in: "query", schema: { type: "integer", minimum: 1, maximum: 200, default: 20 } },
            { name: "offset", in: "query", schema: { type: "integer", minimum: 0, default: 0 } },
            { name: "tier", in: "query", schema: { type: "string", enum: ["top_3", "page_1", "page_2"] } },
            { name: "archetype", in: "query", schema: { type: "string", enum: ["CTR_GAP_PRIME", "CTR_GAP_AGED", "VERIFY_FIRST"] } },
          ],
          responses: { "200": { description: "Ranked rows" } },
        },
      },
      "/stats": { get: { summary: "Aggregate queue numbers", responses: { "200": { description: "Stats" } } } },
      "/health": { get: { summary: "Service status", responses: { "200": { description: "Status" } } } },
    },
    externalDocs: { url: PAPER },
  };
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    const path = normalize(url.pathname);

    if (path === "/health") {
      return json({ status: "ok", month: stats.month, rows: rows.length }, 200, "public, max-age=60");
    }

    if (path === "/stats") {
      return json({
        ...stats,
        model: {
          precision_at_50: 1.0,
          precision_at_140: 0.9871,
          time_forward_precision_at_140: 0.9714,
          brier_score: 0.162,
          bootstrap_gap_140: [0.0143, 0.1],
        },
        paper: PAPER,
      });
    }

    if (path === "/openapi.json") {
      return json(openapi());
    }

    if (path === "/api") {
      return json({
        name: "FlyRank CTR Opportunity Queue",
        month: stats.month,
        endpoints: {
          "/queue?limit=20": "Ranked rows",
          "/queue?tier=page_1&archetype=CTR_GAP_PRIME": "Filtered rows",
          "/stats": "Aggregate numbers",
          "/health": "Service status",
          "/openapi.json": "OpenAPI spec",
        },
        values: {
          tier: ["top_3", "page_1", "page_2"],
          archetype: ["CTR_GAP_PRIME", "CTR_GAP_AGED", "VERIFY_FIRST"],
        },
        paper: PAPER,
      });
    }

    if (path === "/queue") {
      const rawLimit = parseInt(url.searchParams.get("limit") ?? "20", 10);
      const rawOffset = parseInt(url.searchParams.get("offset") ?? "0", 10);
      const limit = Math.min(Math.max(Number.isFinite(rawLimit) ? rawLimit : 20, 1), 200);
      const offset = Math.max(Number.isFinite(rawOffset) ? rawOffset : 0, 0);
      const tier = url.searchParams.get("tier");
      const archetype = url.searchParams.get("archetype");

      let filtered = rows;
      if (tier) filtered = filtered.filter((r) => r.tier === tier);
      if (archetype) filtered = filtered.filter((r) => r.archetype === archetype);

      const page = filtered.slice(offset, offset + limit);
      return json({
        month: stats.month,
        total: filtered.length,
        count: page.length,
        offset,
        limit,
        filters: { tier: tier || null, archetype: archetype || null },
        rows: page,
      });
    }

    if (path === "/") {
      return html(landing());
    }

    return json({ error: "not found", endpoints: ["/", "/api", "/stats", "/health", "/queue", "/openapi.json"] }, 404, "no-store");
  },
};
