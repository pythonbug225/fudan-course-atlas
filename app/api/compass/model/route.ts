import { user } from '../../../../lib/community';
import { forwardDeepSeek } from '../../../../lib/compass-model';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  if (!user(req)) return Response.json({ error: '请先登录 ChatGPT 账号后再使用 AI 规划。' }, { status: 401, headers: { 'Cache-Control': 'no-store' } });
  if (req.headers.get('origin') !== new URL(req.url).origin) return Response.json({ error: '请从本站提交模型请求。' }, { status: 403, headers: { 'Cache-Control': 'no-store' } });
  return forwardDeepSeek(req);
}
