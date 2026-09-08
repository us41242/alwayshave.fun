# STRATEGY

Seeded 2026-08-31; first real version 2026-09-01 after the genre survey in
docs/RESEARCH.md.

## Thesis (confirmed by research)
Playable, coached strategy trainers are absent from this genre. Every
competitor is text plus, at most, an uncoached practice table or a bare
calculator. Tournament blackjack in particular has zero interactive trainers
and its authorities' pages date to 2009-2018. Games earn links and repeat
visits; guides monetize the audience the games attract.

## Positioning
"Play it before you bet it." Mobile-first, dark felt aesthetic (Final Hand
brand direction). Math and cited sources (Wong, Smith, Wizard of Odds), never
invented anecdotes. Honest about comps: they lower the cost of play, they
don't make you a winner.

## v1 build (charter loop 2b) — complete 2026-09-04
1. ✅ Homepage: one screen, one CTA into Final Hand, guide links.
2. ✅ `games/final-hand/` live at `/final-hand/` with coach mode.
3. Cornerstone guides (each links into a game/calculator):
   - ✅ Blackjack tournament strategy: `/blackjack-tournament-strategy/`.
   - ✅ Casino comps and theoretical loss, with calculator: `/casino-comps/` (2026-09-03).
   - ✅ Players cards compared: `/players-cards-compared/` (2026-09-04). Base
     rebate table, trip calculator, tier price list, locals clubs.
4. ✅ Worker: path allowlist → assets. `/j` kept. Everything else 410.
5. ✅ Sitemap live at /sitemap.xml; submitted to GSC (API, 2026-09-03) and pinged via IndexNow.

## Growth (2c) candidates, in order
1. ✅ Tournament bet sizer: `/tournament-bet-sizer/` (2026-09-05). One
   screen, Wong's last-hand rules encoded, asserted against the guide.
2. ✅ Video poker trainer: `/video-poker-trainer/` (2026-09-07). Exact EV of all
   32 holds by full enumeration; coach, hint, session stats.
3. Candidates: Deuces Wild pay table in the same trainer; pay-table
   identifier; more only once something is indexed. Links are the bottleneck.

Indexing: sitemap submitted 09-03, never downloaded by 09-06; Indexing API
nudge sent for all 6 URLs 2026-09-06. Repo purged of trails files 09-06.

## Distribution
Reddit account u/StunningOpinion7483 (session cookie at
~/.camoufox-mcp/sessions/reddit.pw.json, token via scripts/reddit_token.py,
Mac only). Register: answer real questions, disclose, never announce the
site as a post (r/blackjack "I built a site" posts sit at 0). First
comment 2026-09-05 on r/blackjack "Blackjack Tournament Tomorrow".

## Monetization (2d) — all require asking Josh first
Ads once there are real users; affiliate links only with approval; premium
guide / BJA-style funnel (free trainer → email → paid) once there is an
audience.

## Metrics that matter
Games played per visit, return visits, guide→game click-through. Traffic
second. Track once v1 is live (GSC + a privacy-light counter).
