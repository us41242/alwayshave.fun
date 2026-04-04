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


def already_written_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    for fname in os.listdir(DRAFTS_DIR):
        if fname.startswith(today):
            return fname
    return None


def pick_trail(trails):
    """Pick a trail with good or interesting conditions — prioritize high scores or caution alerts."""
    scored = []
    for t in trails:
        slug = t.get("slug", "").strip()
        if not slug:
            continue
        c = load_conditions(slug)
        if not c:
            continue
        score     = c.get("score", 0)
        aqi       = (c.get("aqi") or {}).get("aqi") or 0
        wind      = (c.get("current") or {}).get("wind_mph") or 0
        has_alert = aqi > 100 or wind > 25
        # Interesting = high score OR a caution story to tell
        interest = score + (15 if has_alert else 0)
        scored.append((interest, t, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Pick from top 10 with some randomness so we don't repeat the same trail
    pool = scored[:10]
    return random.choice(pool)[1], random.choice(pool)[2]


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

PERSONA: You're a late-20s guy named Jake. You have an Australian Shepherd named Ruckus who goes everywhere with you. You have a solid job in tech sales but you live for the weekends. Your crew are other guys your age — some married, some not — who carpool up and make a whole thing of it. You're athletic, optimistic, and you write like you're hyping up your group chat. You love the outdoors but you're not a gear snob about it.

BRAND VOICE: alwayshave.fun — even when conditions are rough, the user should leave the page with a plan. Always have fun. Suggest alternatives. Keep it real but keep it positive.

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
1. Title: SEO-friendly, specific, includes trail name + conditions context. Under 60 chars.
2. Meta description: 150 chars max. Include caution alert if AQI>100 or wind>25mph.
3. Body: 600-800 words. Sections: Intro (Jake's voice, hook the reader) | Conditions Breakdown | The Forecast | Dog-Friendly? (always include — Ruckus tested) | Jake's Take (personal recommendation, gear tips, best time to go).
4. If conditions are poor or cautionary: end with "Still want to go?" alternatives — nearby trails with better conditions or tips for when to come back.
5. Natural SEO: weave in the trail name, state, and 2-3 long-tail phrases organically. No keyword stuffing.
6. Tone: casual, first-person, like a smart guy talking to his friends. Not stiff. Not corporate.

OUTPUT FORMAT (markdown):
---
title: [title]
meta_description: [meta]
trail_slug: {trail.get('slug')}
state: {trail.get('state', '').lower()}
date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
score: {score}
score_label: {label}
author: Jake
tags: [{trail.get('state', '').lower()}, {trail.get('region', '').lower().replace(' ', '-')}, trail-conditions, {'caution, ' if has_caution else ''}outdoor-guide]
---

[article body in markdown]
"""
    return prompt


def generate_article(prompt):
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 1400,
        }
    }
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


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


def main():
    already = already_written_today()
    if already:
        print(f"Already wrote today: {already}. One article per day. Come back tomorrow.")
        return

    trails = load_trails()
    trail, conditions = pick_trail(trails)
    print(f"Writing about: {trail.get('name')} (score {conditions.get('score')}/100)")

    prompt  = build_prompt(trail, conditions)
    article = generate_article(prompt)
    path    = save_draft(trail, article)

    print(f"\nDraft ready for your review: {path}")
    print("Add a photo and run: python3 scripts/publish_article.py <draft-file>")


if __name__ == "__main__":
    main()
