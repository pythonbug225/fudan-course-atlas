import { withStudentAccess } from '../../../../lib/student-access';
import { env } from 'cloudflare:workers';
import { user } from '../../../../lib/community';
import { apiError, CompassStateError, createCompassSnapshot } from '../../../../lib/compass-state';

export const dynamic = 'force-dynamic';
const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });

async function readBody(req: Request) {
  const body = await req.text();
  if (new TextEncoder().encode(body).byteLength > 560 * 1024) throw new CompassStateError('规划快照请求过大。', 413);
  try {
    const parsed: unknown = JSON.parse(body);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid');
    return parsed as Record<string, unknown>;
  }
  catch { throw new CompassStateError('请求内容不是有效 JSON。', 400); }
}

async function handlePOST(req: Request) {
  const userId = user(req);
  if (!userId) return json({ error: '请先使用学号登录。' }, 401);
  if (req.headers.get('origin') !== new URL(req.url).origin) return json({ error: '请从本站提交。' }, 403);
  if (!env.DB) return json({ error: '课途云端保存服务暂不可用。' }, 503);
  try {
    const input = await readBody(req);
    const result = await createCompassSnapshot(env.DB, userId, {
      label: typeof input.label === 'string' ? input.label : '',
      state: input.state,
      source: typeof input.source === 'string' ? input.source : 'browser',
      importKey: input.importKey === null || input.importKey === undefined ? null : typeof input.importKey === 'string' ? input.importKey : '',
    });
    return json(result, result.created ? 201 : 200);
  } catch (error) {
    return apiError(error);
  }
}

export async function POST(req:Request) { return withStudentAccess(req, handlePOST); }
