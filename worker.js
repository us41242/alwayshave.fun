const STATES = ['nv', 'ut', 'az', 'ca', 'co', 'nm'];

// Articles served from /articles/{slug}.html
// Worker maps /articles/{slug} → /articles/{slug}.html

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\//, '').split('/').filter(p => p.length > 0);
    const first = (parts[0] || '').toLowerCase();

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
