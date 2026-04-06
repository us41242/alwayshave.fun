"""
reddit_scraper.py — Pull recent trip reports from hiking subreddits.

Runs weekly (Mondays via GitHub Actions).
Matches posts to trails by keyword, stores in:
  - data/reddit/{slug}.json  (local cache, latest 20 posts per trail)
  - Google Sheet "alwayshave.fun — Reddit Intel"  (full historical log)

No Reddit API key needed — uses public JSON endpoints.
"""

import os, json, time, re, csv, requests
from datetime import datetime, timezone, timedelta

DATA_DIR   = "data/reddit"
SEEDS_FILE = "seeds/trails.csv"

# Subreddits to search, with associated state context
SUBREDDITS = [
    "hiking", "Ultralight", "CampingandHiking",
    "Zion", "zionnationalpark",
    "Yosemite",
    "GrandCanyon",
    "coloradohiking", "Colorado", "14ers",
    "Nevada", "lasvegas",
    "Utah",
    "Arizona",
    "socalhiking", "LosAngeles",
    "NationalParks",
]

# Trail → keywords for matching post titles/text
TRAIL_KEYWORDS = {
    "angels-landing-zion-ut":          ["angels landing", "angel's landing"],
    "the-narrows-zion-ut":             ["the narrows", "zion narrows", "narrows bottom"],
    "narrows-top-down-zion-ut":        ["narrows top", "top-down narrows", "chamberlain ranch"],
    "wire-pass-buckskin-az":           ["wire pass", "buckskin gulch", "vermilion cliffs"],
    "paria-canyon-az":                 ["paria canyon", "paria river"],
    "bright-angel-trail-gc-az":        ["bright angel", "grand canyon rim to river"],
    "south-kaibab-gc-az":              ["south kaibab", "ooh aah point"],
    "hermit-trail-gc-az":              ["hermit trail", "hermit creek"],
    "kanab-creek-wilderness-az":       ["kanab creek", "kaibab national forest hike"],
    "toroweap-overlook-az":            ["toroweap", "tuweep"],
    "west-fork-oak-creek-az":          ["west fork", "oak creek canyon"],
    "havasu-falls-az":                 ["havasu falls", "havasupai", "supai"],
    "bryce-rim-trail-ut":              ["bryce rim", "bryce canyon"],
    "peek-a-boo-loop-bryce-ut":        ["peek-a-boo loop", "peekaboo bryce"],
    "kanarra-creek-ut":                ["kanarra creek", "kanarraville falls"],
    "pine-valley-mountain-ut":         ["pine valley mountain"],
    "snow-canyon-rim-ut":              ["snow canyon"],
    "half-dome-yosemite-ca":           ["half dome", "sub dome"],
    "mist-trail-vernal-fall-ca":       ["mist trail", "vernal fall", "nevada fall"],
    "marlette-lake-ca":                ["marlette lake", "flume trail"],
    "crystal-cove-el-moro-ca":         ["crystal cove", "el moro"],
    "mount-whitney-ca":                ["mount whitney", "mt whitney", "whitney portal"],
    "emerald-lake-rmnp-co":            ["emerald lake", "rocky mountain national park", "bear lake"],
    "hanging-lake-co":                 ["hanging lake", "glenwood canyon"],
    "ice-lake-basin-co":               ["ice lake basin", "silverton colorado hike"],
    "maroon-bells-crater-lake-co":     ["maroon bells", "crater lake colorado", "aspen hike"],
    "garden-of-the-gods-co":           ["garden of the gods"],
    "calico-hills-red-rock-nv":        ["calico hills", "red rock canyon", "red rock las vegas"],
    "mary-jane-falls-nv":              ["mary jane falls", "mt charleston"],
    "charleston-peak-nv":              ["charleston peak", "mount charleston summit"],
    "wheeler-peak-great-basin-nv":     ["wheeler peak", "great basin national park"],
    "mount-moriah-nv":                 ["mount moriah nevada"],
    "nelson-ghost-town-nv":            ["nelson ghost town", "el dorado canyon"],
    "rhyolite-ghost-town-nv":          ["rhyolite ghost town", "rhyolite nevada"],
    "river-mountains-loop-nv":         ["river mountains loop", "boulder city trail"],
    "hoover-dam-trail-nv":             ["hoover dam trail"],
    "black-canyon-water-trail-nv":     ["black canyon water trail", "hot spring canyon"],
    "petroglyph-canyon-gold-butte-nv": ["petroglyph canyon", "gold butte"],
    "cathedral-gorge-nv":              ["cathedral gorge"],
    "wave-rock-valley-of-fire-nv":     ["valley of fire", "fire wave", "wave rock valley"],
}


def load_service_account():
    """Load Google service account credentials from env file."""
    env_path = os.path.expanduser("~/Documents/alwayshavefun.env.local")
    # Also check env var directly
    raw = os.environ.get("SERVICE_ACCOUNT_CREDENTIALS", "")
    if not raw and os.path.exists(env_path):
        content = open(env_path).read()
        m = re.search(r'SERVICE_ACCOUNT_CREDENTIALS=(\{.*?\n\})', content, re.DOTALL)
        if m:
            raw = m.group(1)
    if raw:
        try:
            return json.loads(raw)
        except Exception as e:
            print(f"  Warning: couldn't parse service account JSON: {e}")
    return None


def get_sheets_client():
    """Return an authenticated gspread client, or None if unavailable."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = load_service_account()
        if not creds_dict:
            print("  No service account — skipping Google Sheets upload")
            return None
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"  Sheets auth failed: {e}")
        return None


def get_or_create_sheet(client):
    """Open or create 'alwayshave.fun — Reddit Intel' spreadsheet."""
    if not client:
        return None
    title = "alwayshave.fun — Reddit Intel"
    try:
        sh = client.open(title)
        print(f"  Opened existing sheet: {title}")
        return sh
    except Exception:
        pass
    try:
        sh = client.create(title)
        sh.share("breakingeven@breakingeven.iam.gserviceaccount.com", perm_type="user", role="writer")
        print(f"  Created new sheet: {title}")
        return sh
    except Exception as e:
        print(f"  Could not open/create sheet: {e}")
        print("  → Enable Google Drive + Sheets APIs at console.developers.google.com for project 480283047835")
        return None


def ensure_worksheet(sh, tab_name):
    """Get or create a worksheet tab."""
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=2000, cols=10)
        ws.append_row(["date_utc", "trail_slug", "subreddit", "post_id",
                        "title", "score", "num_comments", "url", "selftext_snippet", "fetched_at"])
    return ws


def fetch_subreddit_posts(subreddit, after_days=8):
    """Fetch recent posts from a subreddit using public JSON API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    cutoff  = datetime.now(timezone.utc) - timedelta(days=after_days)
    posts   = []
    after   = None
    for _ in range(3):  # max 3 pages
        url    = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100&raw_json=1"
        if after:
            url += f"&after={after}"
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 429:
                print(f"    Rate limited on r/{subreddit} — waiting 30s")
                time.sleep(30)
                continue
            if r.status_code == 403:
                print(f"    r/{subreddit}: 403 (IP blocked by Reddit)")
                break
            if r.status_code != 200:
                print(f"    r/{subreddit}: HTTP {r.status_code}")
                break
            data     = r.json()
            children = data.get("data", {}).get("children", [])
            after    = data.get("data", {}).get("after")
            for child in children:
                p = child.get("data", {})
                created = datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc)
                if created < cutoff:
                    after = None  # stop paginating
                    break
                posts.append({
                    "post_id":    p.get("id"),
                    "title":      p.get("title", ""),
                    "selftext":   (p.get("selftext", "") or "")[:500],
                    "score":      p.get("score", 0),
                    "comments":   p.get("num_comments", 0),
                    "url":        f"https://reddit.com{p.get('permalink', '')}",
                    "created_utc":created.isoformat(),
                    "subreddit":  subreddit,
                })
            if not after:
                break
            time.sleep(1)
        except Exception as e:
            print(f"    Error fetching r/{subreddit}: {e}")
            break
    return posts


def match_posts_to_trails(posts):
    """Return dict of slug → [matching posts]."""
    matched = {}
    for post in posts:
        text = (post["title"] + " " + post["selftext"]).lower()
        for slug, keywords in TRAIL_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                matched.setdefault(slug, []).append(post)
    return matched


def save_local(slug, posts):
    """Cache matched posts locally as JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = f"{DATA_DIR}/{slug}.json"
    existing = []
    try:
        with open(path) as f:
            existing = json.load(f)
    except Exception:
        pass
    seen_ids = {p["post_id"] for p in existing}
    new_posts = [p for p in posts if p["post_id"] not in seen_ids]
    combined  = (new_posts + existing)[:40]  # keep latest 40
    with open(path, "w") as f:
        json.dump(combined, f, indent=2)
    return len(new_posts)


def upload_to_sheets(ws, slug, posts, fetched_at):
    """Append new rows to the Google Sheet."""
    rows = []
    for p in posts:
        rows.append([
            p["created_utc"],
            slug,
            p["subreddit"],
            p["post_id"],
            p["title"],
            p["score"],
            p["comments"],
            p["url"],
            p["selftext"][:200].replace("\n", " "),
            fetched_at,
        ])
    if rows:
        ws.append_rows(rows, value_input_option="RAW")


def main():
    print("Reddit scraper starting…")
    fetched_at = datetime.now(timezone.utc).isoformat()
    os.makedirs(DATA_DIR, exist_ok=True)

    # Auth Google Sheets once
    client   = get_sheets_client()
    sh       = get_or_create_sheet(client) if client else None
    ws       = ensure_worksheet(sh, "Posts") if sh else None

    # Fetch all subreddits
    all_posts = []
    for sub in SUBREDDITS:
        print(f"  Fetching r/{sub}…")
        posts = fetch_subreddit_posts(sub, after_days=8)
        print(f"    {len(posts)} posts")
        all_posts.extend(posts)
        time.sleep(2)  # rate limit

    # Deduplicate across subreddits
    seen  = set()
    deduped = []
    for p in all_posts:
        if p["post_id"] not in seen:
            seen.add(p["post_id"])
            deduped.append(p)
    print(f"\nTotal unique posts: {len(deduped)}")

    # Match to trails
    matched = match_posts_to_trails(deduped)
    print(f"Matched to {len(matched)} trails\n")

    total_new = 0
    for slug, posts in matched.items():
        new_count = save_local(slug, posts)
        total_new += new_count
        if ws and new_count > 0:
            # Only upload new posts
            existing_ids = set()
            try:
                existing_rows = ws.get_all_values()[1:]  # skip header
                existing_ids  = {r[3] for r in existing_rows if len(r) > 3}
            except Exception:
                pass
            new_only = [p for p in posts if p["post_id"] not in existing_ids]
            if new_only:
                upload_to_sheets(ws, slug, new_only, fetched_at)
        print(f"  {slug}: {len(posts)} total, {new_count} new")

    print(f"\nDone — {total_new} new posts stored across {len(matched)} trails.")
    if ws:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
        print(f"Google Sheet: {sheet_url}")


if __name__ == "__main__":
    main()
