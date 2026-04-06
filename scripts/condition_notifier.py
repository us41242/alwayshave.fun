"""
condition_notifier.py — Alerts when a trail shifts from Poor to Good conditions.

Compares current scores against a snapshot from the previous run.
On shift: sends email via Brevo to the subscriber list tagged with that trail.
Snapshot stored at: data/meta/score_snapshot.json

Run after fetch_conditions.py in the GitHub Actions workflow.
"""

import os
import json
import requests
from datetime import datetime, timezone

BREVO_KEY     = os.environ.get("BREVO_API_KEY", "")
_brevo_list_raw = os.environ.get("BREVO_LIST_ID", "2").strip()
BREVO_LIST_ID = int(_brevo_list_raw) if _brevo_list_raw.isdigit() else 2
DATA_DIR      = "data/conditions"
SNAPSHOT_PATH = "data/meta/score_snapshot.json"
BASE_URL      = "https://alwayshave.fun"

# Score thresholds matching score_label in fetch_conditions.py
GOOD_THRESHOLD = 70   # "Good conditions" or better
POOR_THRESHOLD = 50   # below this = "Use caution" or worse


def load_snapshot():
    try:
        with open(SNAPSHOT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_snapshot(snapshot):
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)


def load_all_conditions():
    import glob
    results = {}
    for path in glob.glob(f"{DATA_DIR}/*.json"):
        try:
            with open(path) as f:
                d = json.load(f)
            slug = d.get("slug")
            if slug:
                results[slug] = d
        except Exception:
            pass
    return results


def get_trail_subscribers(slug):
    """Return emails subscribed to alerts for this trail via Brevo TRAIL_ALERTS attribute."""
    if not BREVO_KEY:
        return []
    try:
        emails = []
        offset, limit = 0, 500
        while True:
            r = requests.get(
                f"https://api.brevo.com/v3/contacts?limit={limit}&offset={offset}&sort=asc",
                headers={"api-key": BREVO_KEY}, timeout=20,
            )
            if r.status_code != 200:
                break
            data     = r.json()
            contacts = data.get("contacts", [])
            for c in contacts:
                alerts = (c.get("attributes") or {}).get("TRAIL_ALERTS", "") or ""
                if slug in [s.strip() for s in alerts.split(",")]:
                    emails.append(c["email"])
            if len(contacts) < limit:
                break
            offset += limit
        return emails
    except Exception as e:
        print(f"  [notifier] Error fetching subscribers for {slug}: {e}")
        return []


def send_alert(trail_data, old_score, new_score):
    """Send a condition-improvement alert via Brevo to per-trail subscribers."""
    if not BREVO_KEY:
        print(f"  [notifier] No BREVO_KEY — skipping email for {trail_data['name']}")
        return

    name      = trail_data["name"]
    slug      = trail_data["slug"]
    state     = (trail_data.get("state") or "").lower()
    label     = trail_data.get("score_label", "Good conditions")
    score     = new_score
    temp      = (trail_data.get("current") or {}).get("temp_f")
    wind      = (trail_data.get("current") or {}).get("wind_mph")
    aqi_val   = (trail_data.get("aqi") or {}).get("aqi")
    trail_url = f"{BASE_URL}/{state}/{slug}"

    subject = f"✅ {name} just flipped to {label} — go time!"

    html = f"""
<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;background:#0c1117;color:#e6edf3;padding:32px;border-radius:12px">
  <h1 style="color:#22c55e;font-size:24px;margin-bottom:8px">Good news for your weekend 🏔️</h1>
  <p style="color:#8b949e;margin-bottom:24px">Conditions just improved on a trail you're watching.</p>

  <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;margin-bottom:24px">
    <h2 style="font-size:20px;margin:0 0 4px">{name}</h2>
    <p style="color:#22c55e;font-size:28px;font-weight:700;margin:8px 0">{score}/100 — {label}</p>
    <p style="color:#8b949e;font-size:14px">Was {old_score}/100 · Now {new_score}/100</p>
    <div style="margin-top:16px;display:flex;gap:12px;flex-wrap:wrap">
      {f'<span style="background:#1f2937;padding:6px 12px;border-radius:6px;font-size:14px">🌡 {temp}°F</span>' if temp else ''}
      {f'<span style="background:#1f2937;padding:6px 12px;border-radius:6px;font-size:14px">💨 {wind} mph</span>' if wind else ''}
      {f'<span style="background:#1f2937;padding:6px 12px;border-radius:6px;font-size:14px">🌫 AQI {aqi_val}</span>' if aqi_val else ''}
    </div>
  </div>

  <a href="{trail_url}" style="display:inline-block;background:#22c55e;color:#000;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:16px">
    See full conditions →
  </a>

  <p style="color:#6e7681;font-size:12px;margin-top:32px">
    You're getting this because you signed up for condition alerts at alwayshave.fun.<br>
    <a href="{BASE_URL}/unsubscribe" style="color:#6e7681">Unsubscribe</a>
  </p>
</div>
"""

    brevo_headers = {
        "api-key":      BREVO_KEY,
        "Content-Type": "application/json",
    }

    print(f"  [notifier] SHIFT: {name} {old_score} → {new_score} ({label})")
    print(f"  [notifier] URL: {trail_url}")

    # Get per-trail subscribers
    subscribers = get_trail_subscribers(slug)
    print(f"  [notifier] Subscribers for {slug}: {len(subscribers)}")

    if not subscribers:
        return  # no one watching this trail yet

    # Send one transactional email per subscriber
    sent = 0
    for email in subscribers:
        payload = {
            "sender":      {"name": "alwayshave.fun", "email": "hello@alwayshave.fun"},
            "to":          [{"email": email}],
            "subject":     subject,
            "htmlContent": html,
        }
        try:
            r = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload, headers=brevo_headers, timeout=15,
            )
            if r.status_code in (200, 201):
                sent += 1
            else:
                print(f"  [notifier] Brevo error {r.status_code} for {email}: {r.text[:100]}")
        except Exception as e:
            print(f"  [notifier] Send error for {email}: {e}")

    print(f"  [notifier] Sent {sent}/{len(subscribers)} alerts for {name}")


def main():
    print(f"Condition notifier — {datetime.now(timezone.utc).isoformat()}")

    snapshot   = load_snapshot()
    current    = load_all_conditions()
    new_snapshot = {}
    shifts     = []

    for slug, data in current.items():
        score = data.get("score", 0)
        new_snapshot[slug] = score

        old_score = snapshot.get(slug)
        if old_score is None:
            continue  # first run, no comparison

        was_poor = old_score < POOR_THRESHOLD
        now_good = score >= GOOD_THRESHOLD
        improved_significantly = (score - old_score) >= 20 and score >= GOOD_THRESHOLD

        if (was_poor and now_good) or improved_significantly:
            shifts.append((slug, old_score, score, data))
            print(f"  SHIFT: {data.get('name')} {old_score} → {score}")

    for slug, old, new, data in shifts:
        send_alert(data, old, new)

    save_snapshot(new_snapshot)
    print(f"Done. {len(shifts)} shifts detected across {len(current)} trails.")


if __name__ == "__main__":
    main()
