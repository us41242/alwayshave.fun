export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\//, '').split('/').filter(p => p.length > 0);

    // /{state}/{slug}  →  serve trail.html (keeps the URL intact)
    if (parts.length === 2) {
      return env.ASSETS.fetch(new URL('/trail.html', url.origin));
    }

    // /{state}  →  redirect to homepage (state filter links in footer)
    if (parts.length === 1 && ['nv','ut','az','ca','co'].includes(parts[0].toLowerCase())) {
      return Response.redirect(url.origin + '/', 302);
    }

    // Everything else  →  serve static assets normally
    return env.ASSETS.fetch(request);
  }
};
