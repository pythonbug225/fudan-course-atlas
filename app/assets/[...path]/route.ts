import references from '../../../public/data/offsite-assets.json';

// Some hosting adapters do not apply static _redirects rules to missing assets.
// Keep previously published material URLs working through the server as well.
export function GET(request: Request) {
  const pathname = new URL(request.url).pathname;
  const item = references.assets.find((entry) => '/' + entry.path === pathname);
  if (!item) return new Response('Not found', { status: 404 });
  return Response.redirect(item.url, 302);
}

export const HEAD = GET;
