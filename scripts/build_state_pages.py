"""
build_state_pages.py — Generate pre-rendered state landing pages.

Creates generated/{state}/index.html for each state so /nv, /ut, /az, etc.
serve real SEO content instead of redirecting to the homepage.

Google sees: unique title, canonical, meta, schema, and a baked-in trail
listing with current conditions. The page still loads fresh JS data on top.
"""

import os
import json
import glob

BASE_URL = "https://alwayshave.fun"
DATA_DIR = "data/conditions"
OUT_DIR  = "generated"

STATE_FAQS = {
    "NV": [
        ("What's the best time of year to hike near Las Vegas?",
         "October through April is the sweet spot — daytime temps are 60–80°F at Red Rock Canyon and Valley of Fire. Summer (June–September) sees regular 100°F+ days at low elevation; switch to Mt. Charleston or the Spring Mountains for cooler high-country hiking July–September."),
        ("Are there dog-friendly trails near Las Vegas?",
         "Yes. Red Rock Canyon, Lake Mead NRA, and most BLM land in southern Nevada permit leashed dogs. See the dog-friendly trails list filtered by Nevada."),
        ("What is a 'great today' score?",
         "It's a 1-100 score combining temperature, AQI, wind, fire risk, and forecast. 85+ is great, 50–70 is caution, below 30 is poor. Updated every 30 minutes."),
    ],
    "UT": [
        ("Do I need a permit for Angels Landing?",
         "Yes. Since 2022, Zion National Park requires a timed-entry permit for the chains section of Angels Landing. Apply via Recreation.gov — seasonal and day-before lotteries available."),
        ("When is the best time to hike in Utah's canyon country?",
         "April–June and September–October are ideal across Zion, Bryce, and Snow Canyon. Higher-elevation Bryce stays cool through summer; lower Zion gets dangerously hot June–August."),
        ("Are dogs allowed on Zion trails?",
         "No, dogs are banned on every Zion backcountry trail except the Pa'rus Trail. Most Utah national parks have similar restrictions — state parks like Snow Canyon are more dog-friendly."),
    ],
    "AZ": [
        ("When should I avoid the Grand Canyon?",
         "Avoid hiking inner-canyon trails (Bright Angel, South Kaibab) June–August between 10am and 4pm — temperatures at the river regularly exceed 110°F and rangers do dozens of heat rescues per summer."),
        ("Is Havasupai open to day hikers?",
         "No. Havasupai requires a multi-night reservation through the tribal office. Permits sell out within minutes of release each February."),
        ("Are dogs allowed in the Grand Canyon?",
         "Only on rim trails above the canyon edge. No dogs are permitted on inner-canyon trails. Service animals require special arrangement with rangers."),
    ],
    "CO": [
        ("Do Colorado 14ers require permits?",
         "Most don't, but Maroon Bells Scenic Loop has timed-entry shuttle requirements June–October, and Hanging Lake requires a paid timed-entry permit. Always check trailhead before driving up."),
        ("When is afternoon thunderstorm season in Colorado?",
         "Mid-June through mid-September. Plan to be off summit ridges by 11am-noon. Lightning strikes have killed hikers on every major Colorado peak — start at sunrise or earlier."),
        ("How do I avoid altitude sickness?",
         "Sleep at moderate elevation (Denver/Boulder) for 1–2 nights before attempting anything above 12,000 ft. Hydrate, descend if symptoms worsen, and consider a slow ramp up."),
    ],
    "CA": [
        ("Do I need a permit for Half Dome?",
         "Yes. The cables route requires a daily permit awarded by lottery — apply in March via Recreation.gov for the May–October season. Day-before lottery also exists."),
        ("Is Mount Whitney a permit hike?",
         "Yes. The day-hike and overnight permits are awarded by lottery in February for the May–November season. Walk-up permits are extremely limited."),
        ("Can I bring my dog to Yosemite trails?",
         "No. Dogs are banned from every Yosemite backcountry trail. Only paved roads and select bike paths permit leashed dogs."),
    ],
}


STATE_META = {
    "NV": {
        "name":    "Nevada",
        "title":   "Nevada Trail Conditions — Live Scores | alwayshave.fun",
        "desc":    "Live trail conditions for 13 Nevada trails. Red Rock Canyon, Mt. Charleston, Valley of Fire, Lake Mead. AQI, weather, and 1-100 scores updated every 30 minutes.",
        "hero":    "From Red Rock Canyon's sandstone ridges to the alpine meadows of the Spring Mountains, Nevada's trails are surprisingly diverse — and most are open year-round.",
        "best":    "October–April is peak season for Las Vegas-area trails. Charleston Peak and Mt. Moriah open July–September. Always check conditions before heading out.",
    },
    "UT": {
        "name":    "Utah",
        "title":   "Utah Trail Conditions — Live Scores | alwayshave.fun",
        "desc":    "Live trail conditions for 8 Utah trails. Zion, Bryce Canyon, Snow Canyon. AQI, weather, and 1-100 scores updated every 30 minutes.",
        "hero":    "Utah's canyon country hosts some of the most iconic hiking in North America — Zion's slot canyons, Bryce's hoodoos, and the otherworldly red rock of Snow Canyon.",
        "best":    "Spring (April–June) and fall (September–October) are ideal for most Utah trails. Summer heat at lower elevations can be extreme. Higher trails stay accessible May–October.",
    },
    "AZ": {
        "name":    "Arizona",
        "title":   "Arizona Trail Conditions — Live Scores | alwayshave.fun",
        "desc":    "Live trail conditions for 9 Arizona trails. Grand Canyon, Havasupai, Sedona, Vermilion Cliffs. AQI, weather, and 1-100 scores updated every 30 minutes.",
        "hero":    "Arizona's trails span the depths of the Grand Canyon to Sedona's red rock wonderlands. Hot summers shift the prime season to October through April.",
        "best":    "October–April is the sweet spot for Grand Canyon and Sonoran Desert trails. Havasupai requires advance permits. Flagstaff and high-country trails open May–October.",
    },
    "CO": {
        "name":    "Colorado",
        "title":   "Colorado Trail Conditions — Live Scores | alwayshave.fun",
        "desc":    "Live trail conditions for 5 Colorado trails. Hanging Lake, Maroon Bells, Rocky Mountain NP, San Juan Mountains. AQI, weather, and scores updated every 30 minutes.",
        "hero":    "Colorado's Front Range and San Juan Mountains deliver high-alpine drama — wildflowers, 14ers, and turquoise lakes that reward an early start.",
        "best":    "Most high-altitude Colorado trails are snow-free July–September. Afternoon thunderstorms are common — start before 7am at elevation. Hanging Lake requires timed-entry permits.",
    },
    "CA": {
        "name":    "California",
        "title":   "California Trail Conditions — Live Scores | alwayshave.fun",
        "desc":    "Live trail conditions for 5 California trails. Yosemite, Mount Whitney, Crystal Cove, Lake Tahoe. AQI, weather, and 1-100 scores updated every 30 minutes.",
        "hero":    "California's trails span from Yosemite's granite peaks to Crystal Cove's coastal bluffs. Fire, drought, and permit lotteries make real-time conditions essential reading.",
        "best":    "Yosemite and Whitney are best May–October; coastal California trails are year-round. Half Dome cables go up in spring — check NPS for exact dates. AQI spikes during fire season (Jul–Oct).",
    },
}


def score_color(score):
    if score >= 85: return "#16a34a"
    if score >= 70: return "#65a30d"
    if score >= 50: return "#d97706"
    if score >= 30: return "#ea580c"
    return "#dc2626"


def load_conditions_by_state():
    by_state = {}
    for path in glob.glob(f"{DATA_DIR}/*.json"):
        try:
            with open(path) as f:
                d = json.load(f)
            state = (d.get("state") or "").upper()
            if state:
                by_state.setdefault(state, []).append(d)
        except Exception:
            pass
    # Sort each state's trails by score descending
    for state in by_state:
        by_state[state].sort(key=lambda x: x.get("score", 0), reverse=True)
    return by_state


def trail_row_html(d):
    slug       = d.get("slug", "")
    state_lc   = (d.get("state") or "").lower()
    name       = d.get("name", "")
    park       = d.get("park_name", "")
    score      = d.get("score", 0)
    label      = d.get("score_label", "")
    diff       = d.get("difficulty", "")
    miles      = d.get("length_mi", "")
    dog        = d.get("dog_friendly", "")
    cur        = d.get("current") or {}
    aqi_data   = d.get("aqi") or {}
    temp       = cur.get("temp_f", "")
    aqi_val    = aqi_data.get("aqi", "")
    color      = score_color(score)
    dog_badge  = ' <span style="font-size:.75rem;color:#16a34a">🐾 Dogs OK</span>' if dog == "Yes" else ""

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
        <div style="font-weight:600;font-size:.95rem;color:#e6edf3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name}{dog_badge}</div>
        <div style="font-size:.75rem;color:#8b949e;margin-top:2px">{park}</div>
        <div style="font-size:.72rem;color:#8b949e;margin-top:2px">
          <span style="color:{diff_color}">{diff}</span> · {miles} mi · {temp_str}{aqi_str}<span style="color:{color}">{label}</span>
        </div>
      </div>
      <div style="font-size:.8rem;color:#8b949e;white-space:nowrap">View →</div>
    </a>'''


def build_state_page(state, trails, meta):
    state_lc   = state.lower()
    page_url   = f"{BASE_URL}/{state_lc}"
    good_count = sum(1 for t in trails if t.get("score", 0) >= 85)
    dog_count  = sum(1 for t in trails if t.get("dog_friendly") == "Yes")

    trail_rows = "\n".join(trail_row_html(t) for t in trails)

    # Schema: CollectionPage listing the trails
    schema_items = []
    for t in trails:
        slug = t.get("slug", "")
        schema_items.append({
            "@type": "ListItem",
            "position": trails.index(t) + 1,
            "url": f"{BASE_URL}/{state_lc}/{slug}",
            "name": t.get("name", ""),
        })

    faq_pairs = STATE_FAQS.get(state, [])
    faq_schema = {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faq_pairs
        ],
    } if faq_pairs else None

    graph = [
        {
            "@type": "CollectionPage",
            "@id": page_url,
            "name": meta["title"],
            "description": meta["desc"],
            "url": page_url,
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
                {"@type": "ListItem", "position": 2, "name": meta["name"], "item": page_url},
            ],
        },
        {
            "@type": "ItemList",
            "name": f"{meta['name']} Trails",
            "numberOfItems": len(trails),
            "itemListElement": schema_items,
        },
    ]
    if faq_schema:
        graph.append(faq_schema)

    schema = {"@context": "https://schema.org", "@graph": graph}

    faq_html = ""
    if faq_pairs:
        rows = "\n".join(
            f'<details style="border-top:1px solid #30363d;padding:14px 0"><summary style="cursor:pointer;font-weight:600;color:#e6edf3;list-style:none">{q}</summary><p style="margin-top:8px;color:#8b949e;line-height:1.7">{a}</p></details>'
            for q, a in faq_pairs
        )
        faq_html = f'''
    <div class="section-title">Frequently Asked — {meta["name"]} Hiking</div>
    <div style="padding-bottom:32px">{rows}</div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-SENVGVQJ6X"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-SENVGVQJ6X');
  </script>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta["title"]}</title>
  <meta name="description" content="{meta["desc"]}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="{meta["title"]}">
  <meta property="og:description" content="{meta["desc"]}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="alwayshave.fun">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{meta["title"]}">
  <meta name="twitter:description" content="{meta["desc"]}">
  <script type="application/ld+json">{json.dumps(schema, separators=(",", ":"))}</script>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛰️</text></svg>">
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
    .state-hero {{ padding: 48px 0 32px; border-bottom: 1px solid #30363d; }}
    .state-name {{ font-size: 2.4rem; font-weight: 900; line-height: 1.1; margin-bottom: 12px; }}
    .state-stats {{ display: flex; gap: 24px; margin: 16px 0; flex-wrap: wrap; }}
    .stat-pill {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px 16px; font-size: .85rem; color: #8b949e; }}
    .stat-pill strong {{ color: #e6edf3; font-size: 1.1rem; }}
    .state-intro {{ font-size: .95rem; color: #8b949e; line-height: 1.7; margin-top: 16px; }}
    .state-best {{ font-size: .85rem; color: #6e7681; line-height: 1.6; margin-top: 8px; padding: 10px 14px; border-left: 3px solid #30363d; }}
    .section-title {{ font-size: 1rem; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: .08em; padding: 28px 0 8px; }}
    .trail-list {{ padding-bottom: 40px; }}
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
        <span class="nav-state">{meta["name"]}</span>
      </div>
    </div>
  </nav>

  <div class="wrap">
    <div class="state-hero">
      <div class="state-name">{meta["name"]} Trails</div>
      <div class="state-stats">
        <div class="stat-pill"><strong>{len(trails)}</strong> trails tracked</div>
        <div class="stat-pill"><strong>{good_count}</strong> great conditions now</div>
        <div class="stat-pill"><strong>{dog_count}</strong> dog-friendly</div>
      </div>
      <p class="state-intro">{meta["hero"]}</p>
      <p class="state-best">{meta["best"]}</p>
    </div>

    <div class="section-title">All {meta["name"]} Trails — Live Conditions</div>
    <div class="trail-list">
      {trail_rows}
    </div>
{faq_html}
    <footer>
      <a href="/">← All Trails</a> &nbsp;·&nbsp;
      <a href="/nv">Nevada</a> &nbsp;·&nbsp;
      <a href="/ut">Utah</a> &nbsp;·&nbsp;
      <a href="/az">Arizona</a> &nbsp;·&nbsp;
      <a href="/co">Colorado</a> &nbsp;·&nbsp;
      <a href="/ca">California</a> &nbsp;·&nbsp;
      <a href="/dog-friendly">🐕 Dog-Friendly</a><br>
      Weather via <a href="https://open-meteo.com" target="_blank" rel="noopener">Open-Meteo</a> &nbsp;·&nbsp;
      AQI via <a href="https://www.airnow.gov" target="_blank" rel="noopener">AirNow</a><br>
      Conditions updated every 30 minutes &nbsp;·&nbsp; <a href="/">alwayshave.fun</a>
    </footer>
  </div>
</body>
</html>'''


def main():
    conditions = load_conditions_by_state()
    built = 0

    for state, meta in STATE_META.items():
        trails = conditions.get(state, [])
        if not trails:
            print(f"  ⚠ No condition data for {state} — skipping")
            continue

        out_dir  = os.path.join(OUT_DIR, state.lower())
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "index.html")

        html = build_state_page(state, trails, meta)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        built += 1
        print(f"  ✓ {state.lower()}/index.html ({len(trails)} trails)")

    print(f"\nDone — {built} state pages → {OUT_DIR}/")


if __name__ == "__main__":
    main()
