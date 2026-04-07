"""
build_articles_index.py — Generate /articles index page.

Reads all articles/*.html files, extracts title/date/trail from their meta tags,
and writes articles/index.html — a crawlable archive page for Google.

Run after publish_article.py or from the pipeline.
"""

import os
import re
import json
from datetime import datetime, timezone

BASE_URL     = "https://alwayshave.fun"
ARTICLES_DIR = "articles"
OUT_PATH     = "articles/index.html"


def extract_meta(html):
    """Pull title, description, og:image, date from article HTML."""
    title = re.search(r'<title>(.+?)\s*\|', html)
    desc  = re.search(r'<meta name="description" content="([^"]+)"', html)
    img   = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    # Pull datePublished from schema
    date  = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    slug  = re.search(r'<link rel="canonical" href="[^"]+/articles/([^"]+)"', html)
    trail_link = re.search(r'<a href="([^"]+)" class="trail-link"', html)

    return {
        "title": title.group(1).strip() if title else "",
        "desc":  desc.group(1).strip()  if desc  else "",
        "img":   img.group(1).strip()   if img   else "",
        "date":  date.group(1)[:10]     if date  else "",
        "slug":  slug.group(1)          if slug  else "",
        "trail_url": trail_link.group(1) if trail_link else "",
    }


def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %-d, %Y")
    except Exception:
        return date_str


def main():
    articles = []

    for fname in os.listdir(ARTICLES_DIR):
        if fname == "index.html" or not fname.endswith(".html"):
            continue
        path = os.path.join(ARTICLES_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                html = f.read()
            meta = extract_meta(html)
            if meta["title"]:
                articles.append(meta)
        except Exception as e:
            print(f"  skip {fname}: {e}")

    # Newest first
    articles.sort(key=lambda a: a["date"], reverse=True)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{BASE_URL}/articles",
                "name": "Trail Guides & Conditions Reports | alwayshave.fun",
                "description": "Trail conditions articles, hiking guides, and outdoor reports for the American Southwest — updated constantly.",
                "url": f"{BASE_URL}/articles",
                "publisher": {"@type": "Organization", "name": "alwayshave.fun", "url": BASE_URL}
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home",     "item": BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": "Articles", "item": f"{BASE_URL}/articles"},
                ]
            }
        ]
    }

    cards_html = ""
    for a in articles:
        img_tag = f'<img class="card-img" src="{a["img"]}" alt="{a["title"]}" loading="lazy">' if a["img"] else ""
        date_str = format_date(a["date"])
        cards_html += f"""
    <a class="card" href="/articles/{a['slug']}">
      {img_tag}
      <div class="card-body">
        <div class="card-date">{date_str}</div>
        <h2 class="card-title">{a['title']}</h2>
        <p class="card-desc">{a['desc'][:120]}{'…' if len(a['desc']) > 120 else ''}</p>
      </div>
    </a>"""

    updated = datetime.now(timezone.utc).strftime("%B %-d, %Y")

    html = f'''<!DOCTYPE html>
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
  <title>Trail Guides & Conditions Reports | alwayshave.fun</title>
  <meta name="description" content="Trail conditions articles, hiking guides, and outdoor reports for the American Southwest — updated constantly. Real data, real talk.">
  <link rel="canonical" href="{BASE_URL}/articles">
  <meta property="og:title" content="Trail Guides & Conditions Reports | alwayshave.fun">
  <meta property="og:description" content="Trail conditions articles, hiking guides, and outdoor reports for the American Southwest.">
  <meta property="og:url" content="{BASE_URL}/articles">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="alwayshave.fun">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{json.dumps(schema, separators=(",",":"))}</script>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛰️</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0c1117; color: #e6edf3; font-family: 'Inter', sans-serif; line-height: 1.5; }}
    a {{ text-decoration: none; color: inherit; }}
    .nav {{ position: sticky; top: 0; background: rgba(12,17,23,.96); border-bottom: 1px solid #30363d; z-index: 100; padding: 14px 0; }}
    .nav-inner {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; }}
    .nav-logo {{ font-weight: 900; font-size: 1.05rem; color: #22c55e; letter-spacing: -.02em; }}
    .nav-back {{ color: #8b949e; font-size: .85rem; }}
    .nav-back:hover {{ color: #e6edf3; }}
    .hero-section {{ max-width: 1100px; margin: 0 auto; padding: 48px 24px 32px; }}
    .hero-section h1 {{ font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 900; letter-spacing: -.03em; }}
    .hero-section p {{ color: #8b949e; margin-top: 10px; font-size: 1rem; }}
    .articles-count {{ display: inline-block; margin-top: 12px; background: #161b22; border: 1px solid #30363d; border-radius: 20px; padding: 3px 12px; font-size: .78rem; color: #8b949e; }}
    .grid {{ max-width: 1100px; margin: 0 auto; padding: 0 24px 64px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; overflow: hidden; transition: border-color .15s, transform .15s; display: flex; flex-direction: column; }}
    .card:hover {{ border-color: #58a6ff; transform: translateY(-2px); }}
    .card-img {{ width: 100%; height: 200px; object-fit: cover; display: block; background: #1f2937; }}
    .card-body {{ padding: 18px; flex: 1; display: flex; flex-direction: column; gap: 8px; }}
    .card-date {{ font-size: .75rem; color: #6e7681; }}
    .card-title {{ font-size: 1rem; font-weight: 700; color: #e6edf3; line-height: 1.3; }}
    .card:hover .card-title {{ color: #58a6ff; }}
    .card-desc {{ font-size: .85rem; color: #8b949e; line-height: 1.5; margin-top: 2px; }}
    .empty {{ text-align: center; padding: 80px 24px; color: #6e7681; }}
    footer {{ border-top: 1px solid #30363d; padding: 28px 24px; text-align: center; font-size: .8rem; color: #6e7681; }}
    footer a {{ color: #8b949e; }}
    footer a:hover {{ color: #e6edf3; }}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="nav-logo" href="/">alwayshave.fun</a>
      <a class="nav-back" href="/">← All Trails</a>
    </div>
  </nav>

  <div class="hero-section">
    <h1>Trail Guides &amp; Conditions Reports</h1>
    <p>Real conditions, real talk — Jake's take on the best trails in the Southwest.</p>
    <span class="articles-count">{len(articles)} article{"s" if len(articles) != 1 else ""} · updated {updated}</span>
  </div>

  {'<div class="grid">' + cards_html + '</div>' if articles else '<div class="empty"><p>No articles yet — check back soon.</p></div>'}

  <footer>
    <a href="/">← All Trails</a> &nbsp;·&nbsp;
    Conditions updated every 30 min &nbsp;·&nbsp; <a href="/">alwayshave.fun</a>
  </footer>
</body>
</html>'''

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Articles index built — {len(articles)} articles → {OUT_PATH}")


if __name__ == "__main__":
    main()
