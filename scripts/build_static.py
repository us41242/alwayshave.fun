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
    notes       = (d.get("notes") or "").strip()
    dog         = d.get("dog_friendly", "")
    lat         = d.get("lat", 0)
    lng         = d.get("lng", 0)
    updated     = (d.get("updated_at") or "")[:10]
    # Top-level sunrise/sunset (ISO datetime); fall back to first forecast entry.
    sunrise_iso = d.get("sunrise") or ((d.get("forecast") or [{}])[0].get("sunrise", ""))
    sunset_iso  = d.get("sunset")  or ((d.get("forecast") or [{}])[0].get("sunset",  ""))
    sunrise_hm  = sunrise_iso[11:16] if sunrise_iso and len(sunrise_iso) >= 16 else ""
    sunset_hm   = sunset_iso[11:16]  if sunset_iso  and len(sunset_iso)  >= 16 else ""

    page_url  = f"{BASE_URL}/{state_lc}/{slug}"
    photo_url = f"{BASE_URL}/photos/{slug}/{slug}.jpg"

    # Caution prefix
    alerts = []
    if aqi_val and aqi_val > 100:
        alerts.append(f"AQI {aqi_val} — {aqi_category(aqi_val).lower()}")
    if wind and wind > 25:
        alerts.append(f"winds {wind} mph")
    alert_str = f"⚠️ CAUTION: {', '.join(alerts)}. " if alerts else ""

    # Meta description (dog-friendly flag for Weekend Warrior queries)
    parts = [f"{name} conditions: {label} ({score}/100)."]
    if temp:    parts.append(f"{temp}°F")
    if wind:    parts.append(f"wind {wind} mph")
    if aqi_val: parts.append(f"AQI {aqi_val}")
    if dog == "Yes":
        parts.append("Dogs welcome.")
    elif dog == "No":
        parts.append("No dogs on trail.")
    if sunrise_hm and sunset_hm:
        parts.append(f"Sunrise {sunrise_hm}, sunset {sunset_hm}.")
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
    if dog in ("Yes", "No"):
        additional.append({"@type": "PropertyValue", "name": "Dog Friendly", "value": dog})
    if sunrise_hm:
        additional.append({"@type": "PropertyValue", "name": "Sunrise (local)", "value": sunrise_hm})
    if sunset_hm:
        additional.append({"@type": "PropertyValue", "name": "Sunset (local)",  "value": sunset_hm})

    # FAQPage — answers high-intent "is X trail safe/open/dog-friendly?" queries
    faq_pairs = []
    faq_pairs.append({
        "q": f"What are the current conditions at {name}?",
        "a": f"As of the latest update, {name} is scoring {score}/100 ({label}). "
             f"Temperature: {temp}°F, wind: {wind} mph, rain chance: {rain}%. "
             f"Data is refreshed every 30 minutes."
    })
    faq_pairs.append({
        "q": f"Is {name} dog-friendly?",
        "a": (f"Yes, dogs are welcome on {name}. Leash required."
              if dog == "Yes" else
              f"No, dogs are not permitted on {name}.")
        if dog in ("Yes", "No") else
        f"Check the park's current pet policy before visiting {name}."
    })
    faq_pairs.append({
        "q": f"How difficult is {name}?",
        "a": f"{name} is rated {diff}. "
             f"The trail is {miles} miles with {gain} ft of elevation gain."
        if diff and miles else f"{name} difficulty: {diff or 'see trail details'}."
    })
    if aqi_val is not None:
        faq_pairs.append({
            "q": f"What is the air quality (AQI) at {name} today?",
            "a": f"Current AQI at {name} is {aqi_val} — {aqi_category(aqi_val)}. "
                 f"AQI under 50 is Good; 51-100 is Moderate; above 100 may require a mask."
        })
    faq_pairs.append({
        "q": f"When is the best time to visit {name}?",
        "a": f"The best months to hike {name} are {d.get('best_months', 'spring and fall')}."
        if d.get("best_months") else
        f"Spring and fall typically offer the best conditions at {name}."
    })

    faq_schema = {
        "@type": "FAQPage",
        "@id": f"{page_url}#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": p["q"],
                "acceptedAnswer": {"@type": "Answer", "text": p["a"]}
            }
            for p in faq_pairs
        ]
    }

    # amenityFeature surfaces "dogs allowed" as a Schema.org-recognized facility flag —
    # better for AI overviews & rich results than a bare additionalProperty.
    amenity_features = []
    if dog in ("Yes", "No"):
        amenity_features.append({
            "@type": "LocationFeatureSpecification",
            "name": "Dogs allowed",
            "value": dog == "Yes",
        })

    sports_loc = {
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
    }
    if amenity_features:
        sports_loc["amenityFeature"] = amenity_features

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            sports_loc,
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home",       "item": BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": state_name,   "item": f"{BASE_URL}/{state_lc}"},
                    {"@type": "ListItem", "position": 3, "name": name,         "item": page_url}
                ]
            },
            faq_schema
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
         f'<title id="page-title">{m["title"]}</title>'),
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
    ]

    for pattern, replacement in subs:
        repl = replacement  # capture for lambda closure
        html = re.sub(pattern, lambda _m, r=repl: r, html, flags=re.DOTALL | re.IGNORECASE)

    # Inject schema before </head> — trail.html has no existing ld+json block
    schema_tag = f'<script type="application/ld+json" id="schema-ld">{m["schema"]}</script>\n'
    html = html.replace('</head>', schema_tag + '</head>', 1)

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
