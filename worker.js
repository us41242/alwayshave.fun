// alwayshave.fun Worker — v1 vegas site (2026-09-02).
// run_worker_first in wrangler.toml routes EVERY request here. Only the paths
// in ROUTES are served from static assets; everything else is 410 because
// the old trails site was purged (SEO reset, see AUTONOMY.md).
// /j is the short link into the gate unlocker on gates.alwayshave.fun.
// NEVER remove or change it — gates depend on it.

// ponytail: allowlist map instead of a router; grow it as pages ship.
const ROUTES = {
  '/': '/index.html',
  '/final-hand/': '/games/final-hand/index.html',
  '/blackjack-tournament-strategy/': '/guides/blackjack-tournament-strategy/index.html',
  '/casino-comps/': '/guides/casino-comps/index.html',
  '/players-cards-compared/': '/guides/players-cards-compared/index.html',
  '/tournament-bet-sizer/': '/tools/tournament-bet-sizer/index.html',
  '/video-poker-trainer/': '/games/video-poker/index.html',
  '/site.css': '/site.css',
  '/robots.txt': '/robots.txt',
  '/sitemap.xml': '/sitemap.xml',
  '/3d00877f1b744d7898b2862b4c5e94fd.txt': '/3d00877f1b744d7898b2862b4c5e94fd.txt', // IndexNow key
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const p = url.pathname;

    // /j → short link to the Jones gate unlocker (302, repointable). KEEP.
    if (p === '/j') {
      return Response.redirect('https://gates.alwayshave.fun/j', 302);
    }

    // Directory URLs are canonical with a trailing slash.
    if ((p + '/') in ROUTES) {
      url.pathname = p + '/';
      return Response.redirect(url.toString(), 301);
    }

    if (p in ROUTES) {
      url.pathname = ROUTES[p];
      return env.ASSETS.fetch(new Request(url.toString(), request));
    }

    // Every other URL is gone (old trails site) — 410 tells crawlers to drop it.
    url.pathname = '/404.html';
    const nf = await env.ASSETS.fetch(new Request(url.toString(), request));
    return new Response(nf.body, {
      status: 410,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  },
};
