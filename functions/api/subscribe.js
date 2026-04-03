/**
 * POST /api/subscribe
 * Body: { "email": "user@example.com" }
 * Env:  BREVO_API_KEY  — set in Cloudflare Pages → Settings → Environment variables
 *       BREVO_LIST_ID  — numeric ID of your Brevo list (default 2 if unset)
 */
export async function onRequestPost({ request, env }) {
  // CORS preflight handled by onRequestOptions below
  const origin = request.headers.get("Origin") || "";
  const headers = corsHeaders(origin);

  let email;
  try {
    const body = await request.json();
    email = (body.email || "").trim().toLowerCase();
  } catch {
    return json({ error: "Invalid request body" }, 400, headers);
  }

  if (!email || !email.includes("@")) {
    return json({ error: "Valid email required" }, 400, headers);
  }

  const apiKey  = env.BREVO_API_KEY;
  const listId  = parseInt(env.BREVO_LIST_ID || "2", 10);

  if (!apiKey) {
    // Silently succeed in dev/preview so the UI still works
    console.warn("BREVO_API_KEY not set — skipping Brevo call");
    return json({ ok: true }, 200, headers);
  }

  try {
    const res = await fetch("https://api.brevo.com/v3/contacts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": apiKey,
      },
      body: JSON.stringify({
        email,
        listIds: [listId],
        updateEnabled: true,   // re-subscribe if previously unsubscribed
      }),
    });

    // 201 = created, 204 = already exists (updated) — both are success
    if (res.status === 201 || res.status === 204) {
      return json({ ok: true }, 200, headers);
    }

    const data = await res.json().catch(() => ({}));
    console.error("Brevo error:", res.status, data);
    return json({ error: "Subscription failed, please try again" }, 502, headers);
  } catch (err) {
    console.error("Fetch error:", err);
    return json({ error: "Network error, please try again" }, 502, headers);
  }
}

// Handle CORS preflight
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
