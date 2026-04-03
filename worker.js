const STATES = ['nv', 'ut', 'az', 'ca', 'co', 'nm'];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\//, '').split('/').filter(p => p.length > 0);
    const first = (parts[0] || '').toLowerCase();

    // /{state}/{slug}  →  serve trail.html (keeps the URL intact)
    if (parts.length === 2 && STATES.includes(first)) {
      return env.ASSETS.fetch(new URL('/trail.html', url.origin));
    }

    // /{state}  →  redirect to homepage
    if (parts.length === 1 && STATES.includes(first)) {
      return Response.redirect(url.origin + '/', 302);
    }

    // Everything else  →  serve static assets normally
    return env.ASSETS.fetch(request);
  }
};
