/**
 * POST /api/trail-alert
 * Body: { "email": "user@example.com", "slug": "angels-landing-zion-ut" }
 *
 * Adds or updates a Brevo contact with the trail slug stored as an attribute.
 * condition_notifier.py reads TRAIL_ALERTS to send per-trail shift emails.
 *
 * Env: BREVO_API_KEY, BREVO_LIST_ID (same as /api/subscribe)
 */
export async function onRequestPost({ request, env }) {
  const origin  = request.headers.get("Origin") || "";
  const headers = corsHeaders(origin);

  let email, slug;
  try {
    const body = await request.json();
    email = (body.email || "").trim().toLowerCase();
    slug  = (body.slug  || "").trim();
  } catch {
    return json({ error: "Invalid request body" }, 400, headers);
  }

  if (!email || !email.includes("@")) {
    return json({ error: "Valid email required" }, 400, headers);
  }
  if (!slug) {
    return json({ error: "Trail slug required" }, 400, headers);
  }

  const apiKey = env.BREVO_API_KEY;
  const listId = parseInt(env.BREVO_LIST_ID || "2", 10);

  if (!apiKey) {
    console.warn("BREVO_API_KEY not set");
    return json({ ok: true }, 200, headers);
  }

  // 1. Fetch existing contact to merge trail slugs
  let existingSlugs = [];
  try {
    const getRes = await fetch(
      `https://api.brevo.com/v3/contacts/${encodeURIComponent(email)}`,
      { headers: { "api-key": apiKey } }
    );
    if (getRes.status === 200) {
      const contact = await getRes.json();
      const existing = (contact.attributes?.TRAIL_ALERTS || "");
      existingSlugs = existing.split(",").map(s => s.trim()).filter(Boolean);
    }
  } catch (_) {}

  // 2. Merge — avoid duplicates
  if (!existingSlugs.includes(slug)) {
    existingSlugs.push(slug);
  }
  const trailAlerts = existingSlugs.join(",");

  // 3. Upsert contact with merged trail alerts
  try {
    const res = await fetch("https://api.brevo.com/v3/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json", "api-key": apiKey },
      body: JSON.stringify({
        email,
        listIds: [listId],
        updateEnabled: true,
        attributes: { TRAIL_ALERTS: trailAlerts },
      }),
    });

    if (res.status === 201 || res.status === 204) {
      return json({ ok: true }, 200, headers);
    }
    // 400 can mean contact exists — try PATCH update
    const patchRes = await fetch(
      `https://api.brevo.com/v3/contacts/${encodeURIComponent(email)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json", "api-key": apiKey },
        body: JSON.stringify({ attributes: { TRAIL_ALERTS: trailAlerts } }),
      }
    );
    if (patchRes.status === 204) {
      return json({ ok: true }, 200, headers);
    }
    return json({ error: "Subscription failed" }, 502, headers);
  } catch (err) {
    console.error("trail-alert error:", err);
    return json({ error: "Network error" }, 502, headers);
  }
}

export async function onRequestOptions({ request }) {
  const origin = request.headers.get("Origin") || "";
  return new Response(null, { status: 204, headers: corsHeaders(origin) });
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin":  origin || "https://alwayshave.fun",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(body, status, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...extraHeaders },
  });
}
