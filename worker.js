const STATES = ['nv', 'ut', 'az', 'ca', 'co', 'nm'];

// Articles served from /articles/{slug}.html
// Worker maps /articles/{slug} → /articles/{slug}.html

export default {
  async scheduled(event, env, ctx) {
    const resp = await fetch(
      'https://api.github.com/repos/us41242/alwayshave-fun/actions/workflows/fetch_conditions.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.GH_DISPATCH_TOKEN}`,
          'Accept': 'application/vnd.github+json',
          'User-Agent': 'alwayshave-fun-cron',
        },
        body: JSON.stringify({ ref: 'main' }),
      }
    );
    if (!resp.ok) {
      console.error(`dispatch failed: ${resp.status} ${await resp.text()}`);
    }
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\//, '').split('/').filter(p => p.length > 0);
    const first = (parts[0] || '').toLowerCase();

    // Legacy /trail.html?slug=foo-bar-ut → 301 to /{state}/{slug}
    // (slug embeds the state suffix, so we map the suffix back to the state path)
    if (url.pathname === '/trail.html' || url.pathname === '/trail') {
      const slug = url.searchParams.get('slug');
      if (slug) {
        const m = slug.match(/-(nv|ut|az|co|ca|nm|gc-az)$/i);
        // Special: Grand Canyon trails end in "-gc-az" — state is az
        let state = '';
        if (m) {
          state = m[1].toLowerCase();
          if (state === 'gc-az') state = 'az';
        }
        if (state) {
          return Response.redirect(`${url.origin}/${state}/${slug}`, 301);
        }
      }
    }

    // /dog-friendly  →  serve dog-friendly landing page
    if (parts.length === 1 && first === 'dog-friendly') {
      const dfUrl = new URL('/generated/dog-friendly/index.html', url.origin);
      const dfRes = await env.ASSETS.fetch(dfUrl);
      if (dfRes.status === 200) return dfRes;
    }

    // /states  →  serve states hub page
    if (parts.length === 1 && first === 'states') {
      return env.ASSETS.fetch(new URL('/states.html', url.origin));
    }

    // /great-today  →  serve great trails page
    if (parts.length === 1 && first === 'great-today') {
      return env.ASSETS.fetch(new URL('/great-today.html', url.origin));
    }

    // /about, /privacy, /scoring  →  serve trust/E-E-A-T pages
    if (parts.length === 1 && ['about', 'privacy', 'scoring'].includes(first)) {
      return env.ASSETS.fetch(new URL(`/${first}.html`, url.origin));
    }

    // /articles  →  serve articles index
    if (parts.length === 1 && first === 'articles') {
      const idxUrl = new URL('/articles/index.html', url.origin);
      const idxRes = await env.ASSETS.fetch(idxUrl);
      if (idxRes.status === 200) return idxRes;
    }

    // /articles/{slug}  →  serve published article HTML
    if (parts.length === 2 && parts[0] === 'articles') {
      const articleUrl = new URL(`/articles/${parts[1]}.html`, url.origin);
      const articleRes = await env.ASSETS.fetch(articleUrl);
      if (articleRes.status === 200) return articleRes;
    }

    // /{state}/{slug}  →  try pre-rendered static file first, fall back to trail.html
    if (parts.length === 2 && STATES.includes(first)) {
      const [state, slug] = parts;
      const staticUrl = new URL(`/generated/${state}/${slug}.html`, url.origin);
      const staticRes = await env.ASSETS.fetch(staticUrl);
      if (staticRes.status === 200) return staticRes;
      return env.ASSETS.fetch(new URL('/trail.html', url.origin));
    }

    // /{state}  →  serve pre-rendered state landing page, fall back to homepage
    if (parts.length === 1 && STATES.includes(first)) {
      const statePageUrl = new URL(`/generated/${first}/index.html`, url.origin);
      const stateRes = await env.ASSETS.fetch(statePageUrl);
      if (stateRes.status === 200) return stateRes;
      return env.ASSETS.fetch(new URL('/', url.origin));
    }

    // Everything else  →  serve static assets normally
    return env.ASSETS.fetch(request);
  }
};
