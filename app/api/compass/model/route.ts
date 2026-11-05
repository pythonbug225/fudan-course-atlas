import { withStudentAccess } from '../../../../lib/student-access';
import { user } from '../../../../lib/community';
import { forwardDeepSeek } from '../../../../lib/compass-model';

export const dynamic = 'force-dynamic';

async function handlePOST(req: Request) {
  if (!user(req)) return Response.json({ error: '请先使用学号登录后再使用 AI 规划。' }, { status: 401, headers: { 'Cache-Control': 'no-store' } });
  if (req.headers.get('origin') !== new URL(req.url).origin) return Response.json({ error: '请从本站提交模型请求。' }, { status: 403, headers: { 'Cache-Control': 'no-store' } });
  return forwardDeepSeek(req);
}

export async function POST(req:Request) { return withStudentAccess(req, handlePOST); }
