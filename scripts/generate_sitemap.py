import csv
import json
import os
from datetime import datetime, timezone

BASE_URL = "https://alwayshave.fun"

def load_trails(path="seeds/trails.csv"):
    trails = []
    with open(path, newline="", encoding="utf-8") as f:
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            trails.append(row)
    return trails

def load_last_updated(slug):
    path = f"data/conditions/{slug}.json"
    try:
        with open(path) as f:
            data = json.load(f)
            raw = data.get("updated_at", "")
            if raw:
                # Parse the ISO timestamp and re-format to YYYY-MM-DDTHH:MM:SSZ
                dt = datetime.fromisoformat(raw)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def generate_sitemap(trails):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    urls = []

    # Homepage
    urls.append({"loc": BASE_URL, "lastmod": today})

    states = sorted(set(t.get("state", "") for t in trails if t.get("state")))

    # Individual trail pages
    for trail in trails:
        slug  = trail.get("slug", "").strip()
        state = trail.get("state", "").strip().lower()
        if not slug or not state:
            continue
        lastmod = load_last_updated(slug)
        urls.append({
            "loc": f"{BASE_URL}/{state}/{slug}",
            "lastmod": lastmod,
        })

    # Article index
    urls.append({"loc": f"{BASE_URL}/articles", "lastmod": today})

    # Individual articles
    articles_dir = "articles"
    if os.path.isdir(articles_dir):
        for fname in sorted(os.listdir(articles_dir)):
            if fname.endswith(".html") and fname != "index.html":
                slug = fname[:-5]
                # Get article date from published markdown if available
                article_date = today
                for pub_file in os.listdir("content/published") if os.path.isdir("content/published") else []:
                    if f"-{slug}.md" in pub_file:
                        article_date = pub_file[:10] + "T00:00:00Z"
                        break
                urls.append({
                    "loc": f"{BASE_URL}/articles/{slug}",
                    "lastmod": article_date,
                })

    # State landing pages (pre-rendered)
    for state in states:
        urls.append({
            "loc": f"{BASE_URL}/{state.lower()}",
            "lastmod": today,
        })

    # States hub page
    urls.append({"loc": f"{BASE_URL}/states", "lastmod": today})

    # Great today page
    urls.append({"loc": f"{BASE_URL}/great-today", "lastmod": today})

    # Build XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")

    return "\n".join(lines)

def main():
    trails = load_trails()
    sitemap = generate_sitemap(trails)
    os.makedirs("site", exist_ok=True)
    with open("site/sitemap.xml", "w") as f:
        f.write(sitemap)
    print(f"Sitemap generated — {len(trails)} trails, written to site/sitemap.xml")

if __name__ == "__main__":
    main()
