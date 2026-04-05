"""
publish_article.py — Convert a reviewed draft to a live article page.

Usage:
  python3 scripts/publish_article.py content/drafts/2026-04-04-wire-pass-buckskin-az.md

What it does:
  1. Parses frontmatter from the draft
  2. Converts markdown body to HTML
  3. Copies the article photo to photos/articles/{slug}.{ext}
     (looks for a file matching slug pattern in content/drafts/ or photos/)
  4. Writes articles/{slug}.html with full SEO head + Article schema
  5. Moves draft to content/published/
  6. Prints a reminder to commit and push

Photo convention: drop a .jpg/.webp named loosely after the slug in content/drafts/
before running this script. If none found, uses the trail's existing photo.
"""

import os
import re
import sys
import json
import shutil
import glob
from datetime import datetime, timezone

BASE_URL     = "https://alwayshave.fun"
ARTICLES_DIR = "articles"
PHOTOS_DIR   = "photos/articles"
DRAFTS_DIR   = "content/drafts"
PUBLISHED_DIR = "content/published"


# ── Minimal Markdown → HTML ──────────────────────────────────────────────────

def md_to_html(text):
    lines  = text.split("\n")
    output = []
    in_ul  = False

    for line in lines:
        # Headings
        if line.startswith("## "):
            if in_ul: output.append("</ul>"); in_ul = False
            output.append(f"<h2>{inline(line[3:])}</h2>")
            continue
        if line.startswith("### "):
            if in_ul: output.append("</ul>"); in_ul = False
            output.append(f"<h3>{inline(line[4:])}</h3>")
            continue

        # Bullet list
        if line.startswith("- "):
            if not in_ul: output.append("<ul>"); in_ul = True
            output.append(f"<li>{inline(line[2:])}</li>")
            continue

        # End list
        if in_ul and not line.startswith("- "):
            output.append("</ul>")
            in_ul = False

        # Blank line
        if line.strip() == "":
            output.append("")
            continue

        # Regular paragraph
        output.append(f"<p>{inline(line)}</p>")

    if in_ul:
        output.append("</ul>")

    return "\n".join(output)


def inline(text):
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic (but not the *[...] footer pattern)
    text = re.sub(r'(?<!\[)\*(.+?)\*(?!\])', r'<em>\1</em>', text)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Strip italic wrapper from *[...]*
    text = re.sub(r'^\*\[(.+?)\]\*$', r'<em>[\1]</em>', text)
    return text


# ── Frontmatter parser ───────────────────────────────────────────────────────

def parse_frontmatter(content):
    if not content.startswith("---"):
        return {}, content
    end = content.index("---", 3)
    fm_raw = content[3:end].strip()
    body   = content[end+3:].strip()
    fm = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, body


# ── Find photo ───────────────────────────────────────────────────────────────

def find_photo(slug, drafts_dir):
    # Look for any image in drafts/ that mentions the slug or trail name
    for ext in ("jpg", "jpeg", "webp", "png"):
        # Exact slug match
        exact = os.path.join(drafts_dir, f"{slug}.{ext}")
        if os.path.exists(exact):
            return exact
        # Loose match — any file in drafts containing slug words
        slug_words = slug.replace("-", " ").split()[:3]
        for path in glob.glob(os.path.join(drafts_dir, f"*.{ext}")):
            name_lc = os.path.basename(path).lower()
            if any(w in name_lc for w in slug_words):
                return path
    # Fall back to the trail's hero photo
    trail_hero = f"photos/{slug}/{slug}.jpg"
    if os.path.exists(trail_hero):
        return trail_hero
    return None


# ── Build HTML ───────────────────────────────────────────────────────────────

def build_html(fm, body_md, photo_url, slug):
    title       = fm.get("title", slug)
    date_str    = fm.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    state       = fm.get("state", "")
    trail_slug  = fm.get("trail_slug", slug).lower().replace(" ", "-").replace("(","").replace(")","")
    trail_name  = fm.get("trail_name", fm.get("trail", ""))
    score       = fm.get("score", "")
    author      = fm.get("author", "Jake")
    tags        = fm.get("tags", "[]").strip("[]").replace('"','').split(",")
    page_url    = f"{BASE_URL}/articles/{slug}"
    trail_url   = f"{BASE_URL}/{state}/{trail_slug}" if state else None

    # Format date nicely
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = dt.strftime("%B %-d, %Y")
        iso_date     = dt.strftime("%Y-%m-%dT00:00:00Z")
    except Exception:
        display_date = date_str
        iso_date     = date_str

    body_html = md_to_html(body_md)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": page_url,
                "headline": title,
                "author": {"@type": "Person", "name": author},
                "datePublished": iso_date,
                "dateModified":  iso_date,
                "image": photo_url,
                "url": page_url,
                "publisher": {
                    "@type": "Organization",
                    "name": "alwayshave.fun",
                    "url":  BASE_URL,
                }
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home",     "item": BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": "Articles", "item": f"{BASE_URL}/articles"},
                    {"@type": "ListItem", "position": 3, "name": title,      "item": page_url},
                ]
            }
        ]
    }

    trail_link = ""
    if trail_url and trail_name:
        trail_link = f'<a href="{trail_url}" class="trail-link">📍 Live conditions for {trail_name} →</a>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | alwayshave.fun</title>
  <meta name="description" content="{title} — real-time trail conditions guide from alwayshave.fun">
  <link rel="canonical" href="{page_url}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{title} — trail conditions guide from alwayshave.fun">
  <meta property="og:image" content="{photo_url}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="alwayshave.fun">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{title} — trail conditions guide from alwayshave.fun">
  <meta name="twitter:image" content="{photo_url}">
  <script type="application/ld+json">{json.dumps(schema, separators=(",",":"))}</script>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛰️</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0c1117; color: #e6edf3; font-family: 'Inter', sans-serif; line-height: 1.7; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .nav {{ position: sticky; top: 0; background: rgba(12,17,23,.95); border-bottom: 1px solid #30363d; z-index: 100; padding: 14px 0; }}
    .nav-inner {{ max-width: 720px; margin: 0 auto; padding: 0 20px; display: flex; align-items: center; gap: 12px; }}
    .nav-logo {{ font-weight: 800; font-size: 1.1rem; text-decoration: none; color: #e6edf3; }}
    .nav-sep {{ color: #30363d; }}
    .nav-link {{ color: #8b949e; font-size: .9rem; }}
    .hero {{ width: 100%; max-height: 480px; object-fit: cover; display: block; }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 0 20px; }}
    .article-header {{ padding: 36px 0 28px; border-bottom: 1px solid #30363d; margin-bottom: 32px; }}
    .article-title {{ font-size: clamp(1.6rem, 4vw, 2.2rem); font-weight: 900; line-height: 1.2; margin-bottom: 14px; color: #e6edf3; }}
    .article-meta {{ font-size: .82rem; color: #8b949e; display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }}
    .author-badge {{ background: #161b22; border: 1px solid #30363d; border-radius: 20px; padding: 3px 10px; font-size: .75rem; color: #8b949e; }}
    .article-body {{ font-size: 1rem; color: #c9d1d9; }}
    .article-body h2 {{ font-size: 1.3rem; font-weight: 700; color: #e6edf3; margin: 36px 0 12px; }}
    .article-body h3 {{ font-size: 1.1rem; font-weight: 600; color: #e6edf3; margin: 28px 0 10px; }}
    .article-body p {{ margin-bottom: 18px; }}
    .article-body ul {{ margin: 0 0 18px 22px; }}
    .article-body li {{ margin-bottom: 8px; }}
    .article-body strong {{ color: #e6edf3; font-weight: 600; }}
    .article-body em {{ color: #8b949e; }}
    .trail-link {{ display: inline-block; margin: 32px 0; background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 14px 20px; font-weight: 600; color: #58a6ff; font-size: .95rem; }}
    .trail-link:hover {{ border-color: #58a6ff; text-decoration: none; }}
    footer {{ border-top: 1px solid #30363d; padding: 32px 0; margin-top: 48px; font-size: .8rem; color: #6e7681; text-align: center; line-height: 2; }}
    footer a {{ color: #8b949e; }}
    footer a:hover {{ color: #e6edf3; }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="nav-logo" href="/">alwayshave.fun</a>
      <span class="nav-sep">/</span>
      <a class="nav-link" href="/articles">Articles</a>
    </div>
  </nav>

  <img class="hero" src="{photo_url}" alt="{title}" loading="eager">

  <div class="wrap">
    <header class="article-header">
      <h1 class="article-title">{title}</h1>
      <div class="article-meta">
        <span class="author-badge">by {author}</span>
        <span>{display_date}</span>
        {f'<span>Score: <strong style="color:#16a34a">{score}/100</strong> at time of writing</span>' if score else ''}
      </div>
    </header>

    <div class="article-body">
      {body_html}
      {trail_link}
    </div>

    <footer>
      <a href="/">← All Trails</a> &nbsp;·&nbsp;
      <a href="/articles">More Articles</a><br>
      Weather via <a href="https://open-meteo.com" target="_blank" rel="noopener">Open-Meteo</a> &nbsp;·&nbsp;
      AQI via <a href="https://www.airnow.gov" target="_blank" rel="noopener">AirNow</a><br>
      Conditions updated every 30 min &nbsp;·&nbsp; <a href="/">alwayshave.fun</a>
    </footer>
  </div>
</body>
</html>'''


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/publish_article.py <path/to/draft.md>")
        sys.exit(1)

    draft_path = sys.argv[1]
    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    with open(draft_path, encoding="utf-8") as f:
        content = f.read()

    fm, body_md = parse_frontmatter(content)
    slug = fm.get("slug") or os.path.basename(draft_path).replace(".md", "").lstrip("0123456789-")
    # Strip date prefix if present (e.g., 2026-04-04-)
    slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)

    print(f"Publishing: {slug}")

    # Find and copy photo
    photo_src  = find_photo(slug, DRAFTS_DIR)
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    if photo_src:
        ext       = os.path.splitext(photo_src)[1]
        photo_dst = os.path.join(PHOTOS_DIR, f"{slug}{ext}")
        shutil.copy2(photo_src, photo_dst)
        photo_url = f"{BASE_URL}/photos/articles/{slug}{ext}"
        print(f"  Photo: {photo_src} → {photo_dst}")
    else:
        photo_url = f"{BASE_URL}/photos/{slug}/{slug}.jpg"
        print(f"  Photo: not found in drafts — using trail photo at {photo_url}")

    # Build and write HTML
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    html      = build_html(fm, body_md, photo_url, slug)
    html_path = os.path.join(ARTICLES_DIR, f"{slug}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Article: {html_path}")

    # Move draft to published
    os.makedirs(PUBLISHED_DIR, exist_ok=True)
    pub_path = os.path.join(PUBLISHED_DIR, os.path.basename(draft_path))
    shutil.move(draft_path, pub_path)
    print(f"  Draft moved: {pub_path}")

    print(f"\nLive at: {BASE_URL}/articles/{slug}")
    print("Next: git add articles/ photos/articles/ content/ && git push")


if __name__ == "__main__":
    main()
