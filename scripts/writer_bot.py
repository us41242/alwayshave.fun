"""
writer_bot.py — Daily article generator for alwayshave.fun

Persona: Late-20s dog dad, Australian Shepherd, 6-figure job, work-life balance
  over everything. Athletic. Writes like he's texting his crew about the weekend.
  Optimistic even when conditions are rough — always pivots to alternatives.

Runs once per day (triggered by GitHub Actions). Writes a draft to:
  content/drafts/YYYY-MM-DD-<slug>.md

You review, add a photo, then run publish_article.py to push it live.
"""

import os
import json
import csv
import random
import requests
from datetime import datetime, timezone, timedelta

GEMINI_KEY = os.environ.get("GEMINI_KEY", os.environ.get("GEMINI_API_KEY", ""))
DATA_DIR   = "data/conditions"
DRAFTS_DIR = "content/drafts"
PUBLISHED  = "content/published"


def load_trails():
    trails = []
    with open("seeds/trails.csv", newline="", encoding="utf-8") as f:
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            trails.append(row)
    return trails


def load_conditions(slug):
    path = f"{DATA_DIR}/{slug}.json"
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def recently_written_slugs(days=7):
    """Return slugs already published in the last N days — avoid repeating."""
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written = set()
    for directory in (DRAFTS_DIR, PUBLISHED):
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if fname.endswith(".md"):
                # Strip date prefix to get slug
                slug = fname.replace(".md", "")
                import re as _re
                slug = _re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
                written.add(slug)
    # Also check articles/ dir for published HTML
    if os.path.isdir("articles"):
        for fname in os.listdir("articles"):
            if fname.endswith(".html"):
                written.add(fname[:-5])
    return written


def pick_trails(trails, count=1):
    """Pick N trails with good/interesting conditions, avoiding recent repeats."""
    skip = recently_written_slugs()
    scored = []
    for t in trails:
        slug = t.get("slug", "").strip()
        if not slug or slug in skip:
            continue
        c = load_conditions(slug)
        if not c:
            continue
        score     = c.get("score", 0)
        aqi       = (c.get("aqi") or {}).get("aqi") or 0
        wind      = (c.get("current") or {}).get("wind_mph") or 0
        has_alert = aqi > 100 or wind > 25
        interest  = score + (15 if has_alert else 0)
        scored.append((interest, t, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Shuffle top 15 so we get variety, then take N
    pool = scored[:15]
    random.shuffle(pool)
    return [(t, c) for _, t, c in pool[:count]]


PERSONAS = {
    # AZ / UT / NV → Jake
    "AZ": {
        "name": "Jake",
        "bio": "Late 20s. Australian Shepherd named Riley who goes on most trips. Solid job, lives for weekends. Crew of friends — guys his age, they carpool, make it a whole thing. Athletic but not a gear snob. Writes like he's texting the group chat but smarter.",
        "dog": "Riley",
    },
    "UT": {
        "name": "Jake",
        "bio": "Late 20s. Australian Shepherd named Riley who goes on most trips. Solid job, lives for weekends. Crew of friends — guys his age, they carpool, make it a whole thing. Athletic but not a gear snob. Writes like he's texting the group chat but smarter.",
        "dog": "Riley",
    },
    "NV": {
        "name": "Jake",
        "bio": "Late 20s. Australian Shepherd named Riley who goes on most trips. Solid job, lives for weekends. Crew of friends — guys his age, they carpool, make it a whole thing. Athletic but not a gear snob. Writes like he's texting the group chat but smarter.",
        "dog": "Riley",
    },
    # CA → Olivia
    "CA": {
        "name": "Olivia",
        "bio": "Late 20s, California-based. American Eskimo named Kipper — fluffy, opinionated, always in the way of a good photo and she loves it. Works in tech, hikes on her days off, has opinions about light and timing that she didn't used to have. Writes like she's leaving a voice memo for a friend.",
        "dog": "Kipper",
    },
    # CO → John
    "CO": {
        "name": "John",
        "bio": "Colorado-based, hikes with his partner Kelly and their two shitzus Mark and Hank — yes, two shitzus on technical trail, yes they keep up. Works remotely, been in CO long enough to stop being impressed by the mountains and start being annoyed by the crowds. Writes straight, no filler.",
        "dog": "Mark and Hank",
    },
}
# Fallback to Jake for any unlisted state
_DEFAULT_PERSONA = PERSONAS["NV"]


def _persona(state):
    return PERSONAS.get(state.upper(), _DEFAULT_PERSONA)

def _persona_block(state):
    p = _persona(state)
    return f"{p['name']}. {p['bio']}"

def _author_name(state):
    return _persona(state)["name"]

def _dog_name(state):
    return _persona(state)["dog"]


def build_roundup_prompt(state, top_trails):
    """Build a Friday state-roundup article prompt."""
    state_names = {"NV": "Nevada", "UT": "Utah", "AZ": "Arizona", "CA": "California", "CO": "Colorado"}
    state_name  = state_names.get(state.upper(), state)
    author      = _author_name(state)
    persona     = _persona_block(state)
    dog         = _dog_name(state)
    today       = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    trail_list = "\n".join(
        f"- {t['name']} ({t['slug']}): {t['score']}/100 — {t['score_label']} | "
        f"{t['difficulty']}, {t['length_mi']} mi, {t['gain_ft']} ft | {t['temp']}°F, {t['rain_pct']}% rain"
        for t in top_trails
    )

    return f"""You are writing a weekend trail roundup for alwayshave.fun.

PERSONA: {persona}

BRAND: alwayshave.fun — real-time conditions, honest scores, always optimistic. Even a caution trail gets a plan.

TASK: Write a "Best hikes in {state_name} this weekend" roundup. Cover {len(top_trails)} trails.

FORMAT RULES:
- Lead with the best trail and its score. Don't bury it.
- Each trail gets 2-4 sentences: what the score means on the ground, one thing to know, go or wait.
- The whole piece should read like one fluid take, not a listicle with headers.
- No markdown headers (##/###). No bold. Flowing paragraphs only.
- Mention {dog} at least once naturally.
- Close with a push — pick one trail and tell them to go.
- 700-900 words total.
- Do not use: "stunning," "breathtaking," "nestled," "picturesque," "hidden gem," "don't miss."

THIS WEEKEND'S TOP {state_name.upper()} TRAILS (live data):
{trail_list}

OUTPUT FORMAT (markdown):
---
title: [specific title — e.g. "Best Utah Hikes This Weekend — April 12"]
meta_description: [150 chars max — mention state + weekend + top score]
article_type: roundup
state: {state.lower()}
date: {today}
score: {top_trails[0]['score'] if top_trails else 0}
author: {author}
tags: [{state.lower()}, weekend-roundup, trail-conditions, outdoor-guide]
---

[article body]
"""


def build_prompt(trail, conditions):
    cur      = conditions.get("current") or {}
    aqi_data = conditions.get("aqi") or {}
    fire     = conditions.get("fire") or {}
    forecast = conditions.get("forecast") or []
    score    = conditions.get("score", 0)
    label    = conditions.get("score_label", "")
    aqi_val  = aqi_data.get("aqi")
    wind     = cur.get("wind_mph")
    temp     = cur.get("temp_f")
    rain     = cur.get("rain_pct")

    has_caution = (aqi_val and aqi_val > 100) or (wind and wind > 25)

    # Weekend forecast snippet
    fc_text = ""
    if forecast:
        days = forecast[:3]
        fc_text = " | ".join(
            f"{d['date']}: {d['high_f']}°/{d['low_f']}°, {d['rain_pct']}% rain"
            for d in days
        )

    caution_note = ""
    if has_caution:
        alerts = []
        if aqi_val and aqi_val > 100:
            alerts.append(f"AQI is {aqi_val} ({aqi_data.get('category', 'Unhealthy')})")
        if wind and wind > 25:
            alerts.append(f"winds at {wind} mph")
        caution_note = f"CAUTION conditions: {', '.join(alerts)}. Article must address this head-on but stay optimistic — suggest alternatives, gear, or best windows."

    prompt = f"""You are writing a trail conditions article for alwayshave.fun.

VOICE — study this excerpt from a real approved article before writing anything:

---
Okay, I'll keep this short because you don't need a lot of convincing when the score is literally 100 out of 100.

Wire Pass to Buckskin Gulch in the Vermilion Cliffs is running perfect right now. 59°F, AQI 36 (that's crystal clear, by the way), winds at 12 mph, and zero chance of rain. The conditions don't get better than this for a slot canyon hike. Like, mathematically they don't.

This is 7.2 miles round trip with only 400 feet of gain, which sounds easy until you're wading through ankle-deep sand in a canyon that's 8 feet wide and 200 feet tall. The "moderate" rating is real — it's not a death march, but you're not going to cruise through it either.

Flash floods. I know you've heard this before, but at Buckskin Gulch it is genuinely not a drill. The canyon is so narrow that a storm 20 miles upstream — a storm you can't see, won't hear until it's too late — can send a wall of water through here in minutes. This is non-negotiable.

If you're in southern Utah or northern Arizona this weekend and you don't take advantage of a 100/100 score at one of the most photogenic slot canyons in the American Southwest, I genuinely don't know what to tell you. We all complain that we never have time — this is time. The conditions are perfect. Go.
---

WHAT MAKES THAT VOICE WORK:
- Opens fast, no preamble, gets to the point in sentence one
- States the data then immediately translates it to what it means on the ground
- Calls out real risks directly — doesn't soften them, doesn't dwell on them
- Uses parentheticals to add color without slowing down ("that's crystal clear, by the way")
- Ends with a push — reader should feel like they're being talked to by someone who's been there and wants them to go
- No gear-snob language. No hiking blog clichés. No "stunning vistas."
- Short sentences when making a point. Longer ones when building a picture.

PERSONA: {_persona_block(trail.get('state', '').upper())}

BRAND: alwayshave.fun — conditions are honest, outlook is always optimistic. Even a caution score gets a plan. Reader leaves with a decision, not a shrug.

TRAIL: {trail.get('name')} ({trail.get('state')})
PARK: {trail.get('park_name')}
DIFFICULTY: {trail.get('difficulty')} | {trail.get('length_mi')} miles | {trail.get('gain_ft')} ft gain
BEST MONTHS: {trail.get('best_months')}
NOTES: {trail.get('notes', 'None')}

CURRENT CONDITIONS (live data):
- Score: {score}/100 — {label}
- Temp: {temp}°F | Wind: {wind} mph | Rain chance: {rain}%
- AQI: {aqi_val} ({aqi_data.get('category', 'Unknown')})
- Fire risk: {fire.get('risk_level', 'unknown')}
{caution_note}

3-DAY FORECAST: {fc_text or 'Not available'}

ARTICLE REQUIREMENTS:
1. Title: specific, includes trail name + conditions hook. Under 60 chars. Not generic.
2. Meta description: 150 chars max. Caution prefix if AQI>100 or wind>25mph.
3. Body: 600-800 words. No mandatory section headers — write it like the excerpt above. Cover: what conditions mean on the ground, one real risk or thing to know, dog situation ({_dog_name(trail.get('state','').upper())} tested), logistics (parking, permit, timing), closing push.
4. Poor/caution conditions: give them a plan — best window, gear fix, or nearby alternative.
5. SEO: trail name, state, 2-3 natural long-tail phrases. No stuffing.
6. Do not use: "stunning," "breathtaking," "nestled," "picturesque," "don't miss," "hidden gem," "you know?", "by the way" (except in parentheticals like the excerpt).
7. No bold text (**word**) — the voice doesn't need emphasis markers. No markdown headers (##, ###) in the body. Flowing paragraphs only.
8. Write as if talking to one friend, not broadcasting to the internet. "You" = singular, specific person.

OUTPUT FORMAT (markdown):
---
title: [title]
meta_description: [meta]
trail_slug: {trail.get('slug')}
trail_name: {trail.get('name')}
dog_friendly: {trail.get('dog_friendly', '')}
state: {trail.get('state', '').lower()}
date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
score: {score}
score_label: {label}
author: {_author_name(trail.get('state', '').upper())}
tags: [{trail.get('state', '').lower()}, {trail.get('region', '').lower().replace(' ', '-')}, trail-conditions, {'caution, ' if has_caution else ''}outdoor-guide]
---

[article body in markdown]
"""
    return prompt


def generate_article(prompt):
    import time

    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if ANTHROPIC_KEY:
        return _generate_claude(prompt, ANTHROPIC_KEY)

    if GEMINI_KEY:
        return _generate_gemini(prompt)

    raise RuntimeError("No AI API key set — need ANTHROPIC_API_KEY or GEMINI_API_KEY")


def _generate_claude(prompt, api_key):
    """Generate via Claude claude-haiku-4-5-20251001 — fast, reliable, no rate limit issues."""
    import time
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "temperature": 1,
        "messages": [{"role": "user", "content": prompt}],
    }
    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            r.raise_for_status()
            data = r.json()
            return data["content"][0]["text"]
        except Exception as e:
            if attempt < 2:
                time.sleep(10)
            else:
                raise
    raise RuntimeError("Claude generation failed")


def _generate_gemini(prompt):
    """Gemini fallback — free tier, rate limits may apply."""
    import time
    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 8192},
    }
    last_err = None
    for model in models:
        for attempt in range(3):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
                r = requests.post(url, json=body, timeout=120)
                if r.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"  Rate limited on {model} (attempt {attempt+1}), waiting {wait}s…")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                parts = r.json()["candidates"][0]["content"]["parts"]
                # Join text parts, skipping thinking parts (thought=True)
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                return text
            except Exception as e:
                last_err = e
                if attempt < 2:
                    time.sleep(15)
        print(f"  {model} failed, trying next model…")
    raise last_err or RuntimeError("All Gemini models failed")


def save_draft(trail, content):
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug     = trail.get("slug", "unknown")
    filename = f"{today}-{slug}.md"
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    path = f"{DRAFTS_DIR}/{filename}"
    with open(path, "w") as f:
        f.write(content)
    print(f"Draft saved: {path}")
    return path


def write_roundups(states=None):
    """Write Friday state-roundup articles. Called on Fridays or with --roundup flag."""
    trails_by_state = {}
    all_trails = load_trails()
    skip = recently_written_slugs()

    for t in all_trails:
        slug  = t.get("slug", "").strip()
        state = t.get("state", "").upper()
        if not slug or slug in skip:
            continue
        c = load_conditions(slug)
        if not c:
            continue
        trails_by_state.setdefault(state, []).append({
            "name":       t.get("name"),
            "slug":       slug,
            "state":      state,
            "difficulty": t.get("difficulty"),
            "length_mi":  t.get("length_mi"),
            "gain_ft":    t.get("gain_ft"),
            "score":      c.get("score", 0),
            "score_label":c.get("score_label", ""),
            "temp":       (c.get("current") or {}).get("temp_f", "?"),
            "rain_pct":   (c.get("current") or {}).get("rain_pct", "?"),
        })

    target_states = [s.upper() for s in states] if states else list(PERSONAS.keys())
    paths = []
    for state in target_states:
        candidates = sorted(trails_by_state.get(state, []), key=lambda x: x["score"], reverse=True)[:5]
        if len(candidates) < 3:
            print(f"  Skipping {state} roundup — not enough trails ({len(candidates)})")
            continue
        print(f"Writing {state} weekend roundup ({len(candidates)} trails)…")
        prompt  = build_roundup_prompt(state, candidates)
        article = generate_article(prompt)
        # Save as a special roundup draft
        today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug    = f"weekend-roundup-{state.lower()}"
        fname   = f"{today}-{slug}.md"
        os.makedirs(DRAFTS_DIR, exist_ok=True)
        path = f"{DRAFTS_DIR}/{fname}"
        with open(path, "w") as f:
            f.write(article)
        print(f"  Draft saved: {path}")
        paths.append(path)
    return paths


def publish_scheduled_drafts():
    """Publish any drafts dated today that are sitting in content/drafts/."""
    import subprocess, re as _re
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    published = 0
    if not os.path.isdir(DRAFTS_DIR):
        return 0
    for fname in sorted(os.listdir(DRAFTS_DIR)):
        if fname.startswith(today) and fname.endswith(".md"):
            path = os.path.join(DRAFTS_DIR, fname)
            print(f"Publishing scheduled draft: {path}")
            result = subprocess.run(
                ["python3", "scripts/publish_article.py", path],
                capture_output=True, text=True
            )
            print(result.stdout.strip())
            if result.returncode != 0:
                print(f"  publish error: {result.stderr.strip()}")
            else:
                published += 1
    return published


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=int(os.environ.get("ARTICLE_COUNT", 1)),
                        help="Number of articles to write (default 1)")
    parser.add_argument("--auto-publish", action="store_true",
                        default=os.environ.get("AUTO_PUBLISH", "").lower() in ("1", "true", "yes"),
                        help="Auto-publish drafts after writing")
    parser.add_argument("--skip-write", action="store_true",
                        help="Only publish scheduled drafts, skip writing new articles")
    parser.add_argument("--roundup", action="store_true",
                        default=os.environ.get("ROUNDUP_MODE", "").lower() in ("1", "true", "yes"),
                        help="Write Friday state roundup articles instead of individual trail articles")
    parser.add_argument("--states", nargs="+", default=None,
                        help="States for roundup mode (e.g. NV UT AZ). Defaults to all.")
    args = parser.parse_args()

    # Always publish any drafts scheduled for today first
    n = publish_scheduled_drafts()
    if n:
        print(f"Published {n} scheduled draft(s).\n")

    if args.skip_write:
        return

    # Friday auto-roundup (or explicit --roundup flag)
    is_friday = datetime.now(timezone.utc).weekday() == 4
    if args.roundup or is_friday:
        print("Friday roundup mode…")
        paths = write_roundups(states=args.states)
        if args.auto_publish and paths:
            import subprocess
            for path in paths:
                result = subprocess.run(["python3", "scripts/publish_article.py", path],
                                        capture_output=True, text=True)
                print(result.stdout)
                if result.returncode != 0:
                    print(f"  publish error: {result.stderr}")
        print(f"Wrote {len(paths)} roundup(s).")
        if is_friday and not args.roundup:
            return  # on Fridays, roundup replaces individual articles

    trails = load_trails()
    picks  = pick_trails(trails, count=args.count)

    if not picks:
        print("No eligible trails found — all recently covered or no conditions data.")
        return

    paths = []
    for trail, conditions in picks:
        print(f"Writing about: {trail.get('name')} (score {conditions.get('score')}/100)")
        prompt  = build_prompt(trail, conditions)
        article = generate_article(prompt)
        path    = save_draft(trail, article)
        paths.append(path)
        print()

    if args.auto_publish and paths:
        import subprocess
        for path in paths:
            print(f"Auto-publishing: {path}")
            result = subprocess.run(
                ["python3", "scripts/publish_article.py", path],
                capture_output=True, text=True
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"  publish error: {result.stderr}")

    print(f"\nWrote {len(paths)} article(s).")


if __name__ == "__main__":
    main()
