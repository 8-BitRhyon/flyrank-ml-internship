import rows from "./data.js";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS },
  });
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    if (url.pathname === "/health") {
      return json({ status: "ok", month: "2026-03", rows: rows.length });
    }

    if (url.pathname === "/queue") {
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
        month: "2026-03",
        total: filtered.length,
        count: page.length,
        offset,
        limit,
        filters: { tier: tier || null, archetype: archetype || null },
        rows: page,
      });
    }

    if (url.pathname === "/") {
      return json({
        name: "FlyRank CTR Opportunity Queue",
        month: "2026-03",
        description: "Ranked page-months for manual CTR review. Decision-support, not a forecast.",
        endpoints: {
          "/health": "Service status",
          "/queue?limit=20": "Ranked rows",
          "/queue?tier=page_1&archetype=CTR_GAP_PRIME": "Filtered rows",
        },
        values: {
          tier: ["top_3", "page_1", "page_2"],
          archetype: ["CTR_GAP_PRIME", "CTR_GAP_AGED", "VERIFY_FIRST"],
        },
        paper: "https://8-bitrhyon.github.io/flyrank-ml-internship/paper/",
      });
    }

    return json({ error: "not found", endpoints: ["/", "/health", "/queue"] }, 404);
  },
};
