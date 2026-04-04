"""
build_static.py — Generate pre-rendered HTML per trail for SEO.

For each trail, reads conditions JSON and injects real title, canonical,
meta description, OG tags, Twitter tags, and schema.org JSON-LD directly
into the HTML <head> — no JavaScript required for Google to read them.

The JS still runs on page load and updates live data for users.
Google sees complete, unique, correct metadata immediately.

Output: generated/{state}/{slug}.html
Worker checks these first; falls back to trail.html if missing.
"""

import os
import json
import glob
import re
from datetime import datetime, timezone

BASE_URL  = "https://alwayshave.fun"
DATA_DIR  = "data/conditions"
TMPL_PATH = "trail.html"
OUT_DIR   = "generated"

STATE_NAMES = {
    "NV": "Nevada", "UT": "Utah", "AZ": "Arizona",
    "CO": "Colorado", "CA": "California", "NM": "New Mexico"
}


def aqi_category(aqi):
    if aqi is None: return "Unknown"
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"


def build_meta(d):
    """Build all SEO strings for a trail."""
    cur       = d.get("current") or {}
    aqi_data  = d.get("aqi") or {}
    fire      = d.get("fire") or {}
    state     = (d.get("state") or "").upper()
    state_lc  = state.lower()
    state_name = STATE_NAMES.get(state, state)
    slug      = d.get("slug", "")
    name      = d.get("name", "")
    park      = d.get("park_name", "")
    score     = d.get("score", 0)
    label     = d.get("score_label", "")
    aqi_val   = aqi_data.get("aqi")
    wind      = cur.get("wind_mph")
    temp      = cur.get("temp_f")
    rain      = cur.get("rain_pct")
    diff      = d.get("difficulty", "")
    miles     = d.get("length_mi", "")
    gain      = d.get("gain_ft", "")
    notes     = (d.get("notes") or "").strip()
    lat       = d.get("lat", 0)
    lng       = d.get("lng", 0)
    updated   = (d.get("updated_at") or "")[:10]

    page_url  = f"{BASE_URL}/{state_lc}/{slug}"
    photo_url = f"{BASE_URL}/photos/{slug}/{slug}.jpg"

    # Caution prefix
    alerts = []
    if aqi_val and aqi_val > 100:
        alerts.append(f"AQI {aqi_val} — {aqi_category(aqi_val).lower()}")
    if wind and wind > 25:
        alerts.append(f"winds {wind} mph")
    alert_str = f"⚠️ CAUTION: {', '.join(alerts)}. " if alerts else ""

    # Meta description
    parts = [f"{name} conditions: {label} ({score}/100)."]
    if temp:   parts.append(f"{temp}°F")
    if wind:   parts.append(f"wind {wind} mph")
    if aqi_val: parts.append(f"AQI {aqi_val}")
    meta_desc = f"{alert_str}{' '.join(parts)} Live data updated every 30 min."

    # Page title
    title = f"{name} Trail Conditions — {label} | alwayshave.fun"

    # Schema
    description = f"{name} in {park}."
    if miles: description += f" {miles} miles"
    if gain:  description += f", {gain} ft gain"
    if diff:  description += f". Difficulty: {diff}."
    if notes: description += f" {notes}"

    additional = [
        {"@type": "PropertyValue", "name": "Difficulty",       "value": str(diff)},
        {"@type": "PropertyValue", "name": "Distance",         "value": f"{miles} miles"},
        {"@type": "PropertyValue", "name": "Elevation Gain",   "value": f"{gain} ft"},
        {"@type": "PropertyValue", "name": "Current Score",    "value": f"{score}/100 — {label}"},
        {"@type": "PropertyValue", "name": "Trail Type",       "value": str(d.get("trail_type", ""))},
    ]
    if aqi_val is not None:
        additional.append({"@type": "PropertyValue", "name": "Air Quality (AQI)", "value": str(aqi_val)})
    if temp is not None:
        additional.append({"@type": "PropertyValue", "name": "Current Temperature", "value": f"{temp}°F"})
    if fire.get("risk_level"):
        additional.append({"@type": "PropertyValue", "name": "Fire Risk", "value": fire["risk_level"].capitalize()})

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SportsActivityLocation",
                "@id": page_url,
                "name": name,
                "description": description.strip(),
                "url": page_url,
                "image": photo_url,
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": float(lat),
                    "longitude": float(lng)
                },
                "containedInPlace": {"@type": "Park", "name": park},
                "additionalProperty": additional,
                "dateModified": updated
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home",       "item": BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": state_name,   "item": f"{BASE_URL}/{state_lc}"},
                    {"@type": "ListItem", "position": 3, "name": name,         "item": page_url}
                ]
            }
        ]
    }

    return {
        "title":      title,
        "meta_desc":  meta_desc,
        "page_url":   page_url,
        "photo_url":  photo_url,
        "state_lc":   state_lc,
        "state_name": state_name,
        "schema":     json.dumps(schema, indent=2),
    }


def inject_head(html, m):
    # Use lambda replacements so re.sub does not interpret backslashes in JSON schema.
    subs = [
        (r'<title[^>]*>.*?</title>',
         f'<title>{m["title"]}</title>'),
        (r'<meta name="description"[^>]*>',
         f'<meta name="description" id="page-desc" content="{m["meta_desc"]}">'),
        (r'<link rel="canonical"[^>]*>',
         f'<link rel="canonical" id="canonical" href="{m["page_url"]}">'),
        (r'<meta property="og:title"[^>]*>',
         f'<meta property="og:title" id="og-title" content="{m["title"]}">'),
        (r'<meta property="og:description"[^>]*>',
         f'<meta property="og:description" id="og-desc" content="{m["meta_desc"]}">'),
        (r'<meta property="og:url"[^>]*>',
         f'<meta property="og:url" id="og-url" content="{m["page_url"]}">'),
        (r'<meta property="og:image"[^>]*>',
         f'<meta property="og:image" id="og-image" content="{m["photo_url"]}">'),
        (r'<meta name="twitter:title"[^>]*>',
         f'<meta name="twitter:title" id="tw-title" content="{m["title"]}">'),
        (r'<meta name="twitter:description"[^>]*>',
         f'<meta name="twitter:description" id="tw-desc" content="{m["meta_desc"]}">'),
        (r'<meta name="twitter:image"[^>]*>',
         f'<meta name="twitter:image" id="tw-image" content="{m["photo_url"]}">'),
        (r'<script type="application/ld\+json"[^>]*>.*?</script>',
         f'<script type="application/ld+json" id="schema-ld">{m["schema"]}</script>'),
    ]

    for pattern, replacement in subs:
        repl = replacement  # capture for lambda closure
        html = re.sub(pattern, lambda _m, r=repl: r, html, flags=re.DOTALL | re.IGNORECASE)

    return html


def load_all_conditions():
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


def main():
    with open(TMPL_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    conditions = load_all_conditions()
    generated  = 0
    errors     = 0

    for slug, d in conditions.items():
        state = (d.get("state") or "").lower()
        if not state or not slug:
            continue
        try:
            m    = build_meta(d)
            html = inject_head(template, m)

            out_dir  = os.path.join(OUT_DIR, state)
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{slug}.html")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)

            generated += 1
            print(f"  ✓ {state}/{slug}.html")
        except Exception as e:
            print(f"  ✗ {slug}: {e}")
            errors += 1

    print(f"\nDone — {generated} pages generated, {errors} errors → {OUT_DIR}/")


if __name__ == "__main__":
    main()
