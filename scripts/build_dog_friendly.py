"""
build_dog_friendly.py — Generate /dog-friendly/ landing page.

Creates generated/dog-friendly/index.html listing only the trails with
dog_friendly=Yes. Targets high-intent local queries like
"dog friendly hikes near las vegas" / "trails dogs allowed utah".
"""

import os
import json
import glob

BASE_URL = "https://alwayshave.fun"
DATA_DIR = "data/conditions"
OUT_DIR  = "generated/dog-friendly"

PAGE_TITLE = "Dog-Friendly Trails — Live Conditions for Hiking with Dogs | alwayshave.fun"
PAGE_DESC  = ("Trails that welcome dogs across NV, UT, AZ, CO, and CA. Live AQI, weather, "
              "and 1-100 conditions scores updated every 30 minutes — pick a great day to "
              "hike with your dog.")
HERO_TEXT  = ("Most national parks ban dogs on trail. These are the ones that don't — state parks, "
              "BLM land, national forests, and recreation areas where leashed dogs are welcome. "
              "Live conditions update every 30 minutes so you can pick the right day.")


def score_color(score):
    if score >= 85: return "#16a34a"
    if score >= 70: return "#65a30d"
    if score >= 50: return "#d97706"
    if score >= 30: return "#ea580c"
    return "#dc2626"


def load_dog_trails():
    trails = []
    for path in glob.glob(f"{DATA_DIR}/*.json"):
        try:
            with open(path) as f:
                d = json.load(f)
            if (d.get("dog_friendly") or "").lower() == "yes":
                trails.append(d)
        except Exception:
            pass
    trails.sort(key=lambda x: x.get("score", 0), reverse=True)
    return trails


def trail_row_html(d):
    slug      = d.get("slug", "")
    state_lc  = (d.get("state") or "").lower()
    name      = d.get("name", "")
    park      = d.get("park_name", "")
    score     = d.get("score", 0)
    label     = d.get("score_label", "")
    diff      = d.get("difficulty", "")
    miles     = d.get("length_mi", "")
    cur       = d.get("current") or {}
    aqi_data  = d.get("aqi") or {}
    temp      = cur.get("temp_f", "")
    aqi_val   = aqi_data.get("aqi", "")
    color     = score_color(score)

    diff_colors = {"Easy": "#16a34a", "Moderate": "#d97706", "Hard": "#ea580c", "Expert": "#dc2626"}
    diff_color  = diff_colors.get(diff, "#8b949e")

    temp_str = f"{temp}°F · " if temp else ""
    aqi_str  = f"AQI {aqi_val} · " if aqi_val else ""

    return f'''
    <a href="/{state_lc}/{slug}" style="display:flex;align-items:center;gap:16px;padding:14px 0;border-bottom:1px solid #30363d;text-decoration:none;color:inherit">
      <div style="min-width:54px;text-align:center">
        <div style="font-size:1.5rem;font-weight:800;color:{color};line-height:1">{score}</div>
        <div style="font-size:.65rem;color:#8b949e">/100</div>
      </div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:600;font-size:.95rem;color:#e6edf3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name} <span style="font-size:.75rem;color:#16a34a">🐕</span></div>
        <div style="font-size:.75rem;color:#8b949e;margin-top:2px">{park} · {(d.get("state") or "").upper()}</div>
        <div style="font-size:.72rem;color:#8b949e;margin-top:2px">
          <span style="color:{diff_color}">{diff}</span> · {miles} mi · {temp_str}{aqi_str}<span style="color:{color}">{label}</span>
        </div>
      </div>
      <div style="font-size:.8rem;color:#8b949e;white-space:nowrap">View →</div>
    </a>'''


def build_html(trails):
    page_url = f"{BASE_URL}/dog-friendly"
    rows = "\n".join(trail_row_html(t) for t in trails)

    schema_items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "url": f"{BASE_URL}/{(t.get('state') or '').lower()}/{t.get('slug','')}",
            "name": t.get("name", ""),
        }
        for i, t in enumerate(trails)
    ]

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": page_url,
                "name": PAGE_TITLE,
                "description": PAGE_DESC,
                "url": page_url,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": "Dog-Friendly Trails", "item": page_url},
                ],
            },
            {
                "@type": "ItemList",
                "name": "Dog-Friendly Trails",
                "numberOfItems": len(trails),
                "itemListElement": schema_items,
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Which national parks allow dogs on trail?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Most national parks ban dogs on backcountry trails. Notable exceptions on this list include certain trails in Bryce Canyon (paved sections), Acadia, and Shenandoah. Most dog-friendly hikes are on BLM land, in state parks, or national forests.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Do I need a leash?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Yes — every trail listed here requires a 6-foot leash. Off-leash is rare on public land in the Southwest and is enforced.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Is the trail safe for dogs in summer heat?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Check the live conditions score before going. We flag high temperatures (>90°F) and unhealthy AQI in real time. Dogs overheat faster than humans — start before sunrise on hot days, carry extra water, and check trail surface temperature with the back of your hand.",
                        },
                    },
                ],
            },
        ],
    }

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-SENVGVQJ6X"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-SENVGVQJ6X');
  </script>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{PAGE_TITLE}</title>
  <meta name="description" content="{PAGE_DESC}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="{PAGE_TITLE}">
  <meta property="og:description" content="{PAGE_DESC}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="alwayshave.fun">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{PAGE_TITLE}">
  <meta name="twitter:description" content="{PAGE_DESC}">
  <script type="application/ld+json">{json.dumps(schema, separators=(",", ":"))}</script>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐕</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0c1117; color: #e6edf3; font-family: 'Inter', sans-serif; }}
    a {{ color: inherit; }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 0 20px; }}
    .nav {{ position: sticky; top: 0; background: rgba(12,17,23,.95); border-bottom: 1px solid #30363d; z-index: 100; padding: 14px 0; }}
    .nav-inner {{ display: flex; align-items: center; gap: 12px; }}
    .nav-logo {{ font-weight: 800; font-size: 1.1rem; text-decoration: none; color: #e6edf3; }}
    .nav-sep {{ color: #30363d; }}
    .nav-state {{ color: #8b949e; font-size: .9rem; }}
    .hero {{ padding: 48px 0 32px; border-bottom: 1px solid #30363d; }}
    .h1 {{ font-size: 2.4rem; font-weight: 900; line-height: 1.1; margin-bottom: 12px; }}
    .stats {{ display: flex; gap: 24px; margin: 16px 0; flex-wrap: wrap; }}
    .pill {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px 16px; font-size: .85rem; color: #8b949e; }}
    .pill strong {{ color: #e6edf3; font-size: 1.1rem; }}
    .intro {{ font-size: .95rem; color: #8b949e; line-height: 1.7; margin-top: 16px; }}
    .section-title {{ font-size: 1rem; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: .08em; padding: 28px 0 8px; }}
    .list {{ padding-bottom: 40px; }}
    footer {{ border-top: 1px solid #30363d; padding: 32px 0; font-size: .8rem; color: #6e7681; line-height: 2; text-align: center; }}
    footer a {{ color: #8b949e; text-decoration: none; }}
    footer a:hover {{ color: #e6edf3; }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="wrap">
      <div class="nav-inner">
        <a class="nav-logo" href="/">alwayshave.fun</a>
        <span class="nav-sep">/</span>
        <span class="nav-state">Dog-Friendly</span>
      </div>
    </div>
  </nav>

  <div class="wrap">
    <div class="hero">
      <div class="h1">🐕 Dog-Friendly Trails</div>
      <div class="stats">
        <div class="pill"><strong>{len(trails)}</strong> trails welcome dogs</div>
        <div class="pill"><strong>{sum(1 for t in trails if t.get("score", 0) >= 85)}</strong> great today</div>
      </div>
      <p class="intro">{HERO_TEXT}</p>
    </div>

    <div class="section-title">All Dog-Friendly Trails — Live Conditions</div>
    <div class="list">
      {rows}
    </div>

    <footer>
      <a href="/">← All Trails</a> &nbsp;·&nbsp;
      <a href="/nv">Nevada</a> &nbsp;·&nbsp;
      <a href="/ut">Utah</a> &nbsp;·&nbsp;
      <a href="/az">Arizona</a> &nbsp;·&nbsp;
      <a href="/co">Colorado</a> &nbsp;·&nbsp;
      <a href="/ca">California</a><br>
      Conditions updated every 30 minutes &nbsp;·&nbsp; <a href="/">alwayshave.fun</a>
    </footer>
  </div>
</body>
</html>'''


def main():
    trails = load_dog_trails()
    if not trails:
        print("No dog-friendly trails found — skipping")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(trails))

    print(f"  ✓ dog-friendly/index.html ({len(trails)} trails)")


if __name__ == "__main__":
    main()
