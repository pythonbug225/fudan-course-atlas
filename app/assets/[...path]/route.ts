import references from '../../../public/data/offsite-assets.json';

// Some hosting adapters do not apply static _redirects rules to missing assets.
// Keep previously published material URLs working through the server as well.
export function GET(request: Request) {
  const pathname = new URL(request.url).pathname;
  const item = references.assets.find((entry) => '/' + entry.path === pathname);
  if (!item) return new Response('Not found', { status: 404 });
  const url = item.url.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  // The host can consume cross-origin HTTP redirects before returning to the browser.
  // A small HTML handoff keeps the original material URL openable by the browser.
  return new Response(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><meta http-equiv="refresh" content="0;url=${url}"><title>课程资料</title><p>正在打开课程资料…… <a href="${url}">直接打开</a></p></html>`, {
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

export const HEAD = GET;
