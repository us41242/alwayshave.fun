# alwayshave.fun — Daily Logbook

Running record of every decision made, why it was made, what was learned, and what's coming next. Updated each session.

---

## 2026-04-04 — Session 1

### Added
- **Static HTML per trail** (`generated/{state}/{slug}.html`) — biggest SEO fix in the project. Every trail was sharing a single `trail.html` template; Google saw the same generic title and canonical for all 40 trails. Now each trail gets its own pre-rendered file with real title, canonical, meta description, OG tags, and schema baked in at build time. JS still updates live data on top for users.
- **`scripts/build_static.py`** — generates the 40 trail pages from conditions JSON + trail.html template. Runs every 30 min in the pipeline.
- **Worker routing** (`worker.js`) — updated to serve `generated/{state}/{slug}.html` first, falling back to `trail.html` if file is missing.

### Reasoning
SEO audit score was 41/100. Root cause: single-template architecture meant Googlebot saw zero unique trail URLs in raw HTML — only the homepage canonical appeared on every page. Static HTML per trail was the single highest-leverage fix available.

### Learned
- Cloudflare Pages Workers with `env.ASSETS.fetch()` can serve any file in the repo by URL — clean way to implement static-first with dynamic fallback.
- The `stefanzweifel/git-auto-commit-action` commits and pushes from Actions — need to `git pull --rebase` before any local push or you'll get non-fast-forward rejections.

### Upcoming
Wire up dog-friendly flags, state landing pages, and IndexNow submission.

---

## 2026-04-04 — Session 3

### Fixed
- **"Trail data unavailable" on all trail pages** — root cause: `build_static.py` was stripping `id="page-title"` from the `<title>` tag in the regex replacement. JS render() calls `getElementById('page-title')`, got null, threw TypeError, catch block showed error div. Fix: preserve the id attribute in the replacement string.
- **Article trail link wrong slug** — first article linked to `/az/wire-pass-to-buckskin-gulch` (made-up slug). Fixed to correct `/az/wire-pass-buckskin-az`.
- **`publish_article.py` trail frontmatter keys** — was reading `fm.get("trail")` but writer_bot outputs `trail_slug` and `trail_name`. Fixed key names so trail links in articles resolve correctly.
- **Schema never injected** — `build_static.py` tried to regex-replace an existing `<script type="application/ld+json">` block in trail.html, but trail.html had none. Schema was silently dropped. Fix: inject schema tag directly before `</head>` instead.

### Added
- **`/articles` index page** (`articles/index.html`) — was 404. Now a real crawlable archive page: CollectionPage schema, card grid with trail photos, newest-first sort, article count. Worker updated to serve it at `/articles`.
- **`scripts/build_articles_index.py`** — generates the articles index from all articles/*.html. Added to both pipeline runs (conditions + writer bot).
- **FAQPage schema on all 40 trail pages** — 5 pre-answered questions per trail: current conditions, dog-friendly, difficulty, AQI, best months. Targets "is [trail] safe today?" rich results in Google. This is the highest-ROI schema type for our query intent.
- **Writer bot multi-article support** — `--count N` flag, `--auto-publish` flag. Tracks recently-written slugs to avoid repeats (checks both drafts/ and articles/ dirs). Adds `trail_name` to frontmatter.
- **4 articles published today:**
  1. Wire Pass to Buckskin Gulch (from Session 2, Jake + Riley photo)
  2. Angels Landing — "Is It Worth the Chains?" — 100/100
  3. Bryce Canyon Rim Trail — April is peak season — 100/100
  4. Calico Hills Red Rock NV — Best day hike near Vegas — 100/100

### Changed
- **`writer_bot.yml`** — now writes 4 articles/day and auto-publishes (no review step). Commits to `articles/`, `photos/articles/`, `content/`.
- **`fetch_conditions.yml`** — added `build_articles_index.py` so articles index stays current on every 30-min data refresh.
- **`worker.js`** — added `/articles` route to serve index page.

### Learned
- FAQPage schema is the single highest-ROI schema addition for "should I hike X today?" query intent. Google shows these as expand/collapse rich results directly in the SERP.
- Internal linking from articles to trail pages (and between related trails) is the primary lever for distributing page authority. Articles need inline links to 2-3 contextual trails — not just the footer link.
- Weekly roundup posts ("Best 5 Trails in Utah This Weekend") capture high-intent voice search and comparison queries that individual trail pages miss.
- Real-time comparison cards (Angels Landing vs X) capture decision-point queries — build as a future feature once article volume is established.

### Plan: Days 2-5
- **Day 2 (Apr 5):** Dog-friendly guides + state roundups. Auto-bot handles 4 trail-condition articles. Manual: "Best Dog-Friendly Trails Nevada" + "Utah Weekend Hiking Roundup."
- **Day 3 (Apr 6):** Evergreen "best time to hike" guides for top 5 trails. Highest long-tail SEO value.
- **Day 4 (Apr 7):** Overlander and photographer persona content. Toroweap deep dive. Paria Canyon guide.
- **Day 5 (Apr 8):** State-level comprehensive guides. Internal linking audit. Sitemap resubmission to Google Search Console.
- **Ongoing tech:** Internal cross-links between articles, HowTo schema for difficulty ratings, comparison content format.

---

## 2026-04-04 — Session 2

### Added
- **`dog_friendly` column** in `seeds/trails.csv` — researched all 40 trails by land jurisdiction. 24 Yes (BLM, USFS, most state parks), 16 No (NPS — Zion, Bryce, Grand Canyon, Yosemite, RMNP — plus Havasupai tribal land, Hanging Lake, Kanarra Creek). Flows into conditions JSONs, trail meta descriptions ("Dogs welcome." / "No dogs on trail."), and schema.org PropertyValue.
- **State landing pages** (`generated/{state}/index.html`) — /nv, /ut, /az, /co, /ca were 302-redirecting to the homepage. Now each serves a real pre-rendered SEO page with unique title/canonical, full trail listing with baked-in live scores, dog-friendly counts, and state-specific intro copy. 5 new indexable URLs.
- **`scripts/build_state_pages.py`** — generates the 5 state pages from conditions data. Added to pipeline.
- **`scripts/indexnow.py`** — pings Bing and Yandex via IndexNow API after every 30-min data update. Submits all 46 URLs (40 trails + 5 states + homepage). Key: `3d00877f1b744d7898b2862b4c5e94fd`, file deployed to repo root.
- **Sunrise/sunset in pipeline** — added `sunrise` and `sunset` fields to Open-Meteo daily request. Now stored in each trail's forecast array. UI hasn't been wired yet.
- **Article publish pipeline** (`scripts/publish_article.py`) — converts reviewed markdown drafts to static HTML article pages at `articles/{slug}.html`. Handles frontmatter parsing, markdown-to-HTML conversion, photo copy to `photos/articles/`, Article + BreadcrumbList schema injection, and moves draft to `content/published/`.
- **Worker updated** — `/articles/{slug}` now routes to `articles/{slug}.html`.
- **First published article** — `articles/wire-pass-buckskin-az.html` — Wire Pass to Buckskin Gulch, 100/100 score. Jake & Riley hero photo. Full SEO head, Article schema.

### Changed
- **Dog name: Ruckus → Riley** — Josh corrected this. Updated everywhere: draft, writer bot persona prompt, and memory.
- **Writer bot model fallback** — was crashing on 429 (rate limit). Added retry loop with exponential backoff across three model endpoints: `gemini-2.0-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash-latest`.
- **Worker `/state` routing** — changed from `302 redirect to /` to serving `generated/{state}/index.html`.

### Removed
- `.env.example` — deleted (was committed accidentally, credentials template not needed in repo).

### Learned
- Gemini API free tier rate-limits aggressively on the local machine but is fine in GitHub Actions (different quota window + IP). Don't rely on it for local testing — write drafts manually when needed.
- NPS land = no dogs on trails (with one exception: Great Basin NP allows leashed dogs). BLM and USFS are dog-friendly by default. This is a useful heuristic for expanding to new trails.
- `git push` with a PAT embedded in the URL (`https://{token}@github.com/...`) is the reliable fallback when credential helpers aren't configured locally.
- IndexNow is a one-shot POST — no ongoing maintenance. Bing indexes within hours of submission. Worth running on every data update, not just weekly.

### Upcoming
- Wire sunrise/sunset into `trail.html` UI (data is ready, just needs display)
- "Best time to hike [trail]" content pages — 40 pages, high long-tail SEO value
- Submit sitemap to Google Search Console if not already done
- Consider adding a `/articles` index page so the article archive is crawlable

---

## 2026-04-06 — Session 5

### Fixed
- **fetch_conditions.yml concurrent run merge conflicts** — two 30-min cron runs writing different JSON to same files would conflict on `git pull --rebase`. Fix: `git pull --rebase -X theirs` so the current run's fresh data wins.
- **Duplicate `fetch_conditions.yaml`** — old broken version (with `git reset --hard`, no concurrency block, missing scripts) was running alongside the correct `.yml`. Deleted the `.yaml`.
- **`if: secrets.CF_CACHE_PURGE_TOKEN != ''` syntax** — invalid in GitHub Actions `if` expressions. Changed to env var + bash conditional.
- **Writer bot Gemini 2.5 Flash truncation** — Gemini 2.5 Flash is a thinking model; its reasoning chain consumes output tokens before text output. With `maxOutputTokens: 1500`, only ~200 chars of text were written. Fixed: 8192 tokens + handle multi-part response to skip thought parts.
- **Misnamed article files** — `zion-narrows-top-down-ut.html` and `valley-of-fire-wave-rock-nv.html` were wrong slug names (didn't match trail data slugs). Replaced with correct `narrows-top-down-zion-ut` and `wave-rock-valley-of-fire-nv`.
- **Articles missing from sitemap** — 14 articles were live but not in sitemap.xml. Google couldn't discover them. Added article URLs (+ state landing pages; removed phantom `/state/` and `/region/` URLs).
- **Article meta descriptions** — all articles were using `{title} — trail conditions guide...` as meta description instead of the specific `meta_description` from frontmatter. Fixed.

### Added
- **7 new articles published today** (17 total):
  - The Narrows (Bottom-Up) UT — 100/100
  - River Mountains Loop NV — 100/100, dog-friendly
  - Kanarra Creek Slot Canyon UT — 100/100, permit required
  - Paria Canyon AZ — 100/100, 38-mile multi-day
  - Hermit Trail GC AZ — 90/100 (bot-generated with Gemini 2.5 Flash)
  - Petroglyph Canyon Gold Butte NV — 90/100 (bot-generated)
  - Bright Angel Trail GC AZ — 90/100, highest-traffic GC query
  - West Fork Oak Creek AZ — 100/100, dog-friendly, Sedona
  - Garden of the Gods CO — 70/100, first Colorado article
- **Sunrise/sunset on forecast cards** — `☀️ HH:MM–HH:MM` below each day's forecast card. Data was already in conditions JSON from Open-Meteo, just not displayed.
- **Related article cross-links** — each article now shows "More Jake's takes from [State]" with links to 3 other published articles from same state. Bidirectional linking.
- **Trail → article link** — trail detail pages now show "Jake's Take" link if an article exists for that trail (JS HEAD request check).
- **CF_CACHE_PURGE_TOKEN** and **CLOUDFLARE_ZONE_ID** added to GitHub Actions secrets.
- **Writer bot voice prompt** — rewrote with verbatim Wire Pass excerpt as gold-standard voice reference + 7 specific rules. No preamble, data → ground truth, direct risk callout, parenthetical color, closing push, banned words.

### Changed
- **Gemini model list** — `gemini-1.5-flash` (now 404) and `gemini-1.5-flash-8b` removed. Replaced with `gemini-2.5-flash` as primary (works on free tier), 2.0-flash/lite as fallbacks.
- **ANTHROPIC_API_KEY** — not yet in GitHub Actions secrets. Writer bot falls back to Gemini 2.5 Flash successfully. STILL NEEDED for Claude Haiku as primary generator.

### Learned
- Gemini 2.5 Flash is a thinking model — its reasoning chain consumes output tokens before visible text. Need 8192 max tokens, not 1500. Also returns multi-part content (thought + text parts).
- Concurrent GitHub Actions cron runs with 30-min schedule will both write to the same JSON files and conflict on push. `-X theirs` in rebase resolves this with the current run's data winning.
- Two workflow files with the same name but different extensions (`.yaml` + `.yml`) both run — GitHub treats them as separate workflows. This created a race condition where both ran on schedule.
- `secrets` context is not available in `if` expressions at the step level — use env var exposure + bash conditional instead.

### Upcoming
- ANTHROPIC_API_KEY — Josh needs to create at console.anthropic.com and add to repo secrets
- Vehicle requirements column in seeds/trails.csv → overlander queries
- Weekly roundup articles ("Best 5 hikes this weekend in Utah") — Thu/Fri schedule
- Remaining 23 trails without articles — bot generating 4/day, ~6 days to full coverage
- HowTo schema for difficulty ratings
