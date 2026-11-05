import { withStudentAccess } from '../../../../lib/student-access';
import { env } from 'cloudflare:workers';
import { user } from '../../../../lib/community';
import { activateCompassSnapshot, apiError, CompassStateError, listCompassProfile } from '../../../../lib/compass-state';

export const dynamic = 'force-dynamic';
const json = (body: unknown, status = 200) => Response.json(body, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });

async function handleGET(req: Request) {
  const userId = user(req);
  if (!userId) return json({ error: '请先使用学号登录。' }, 401);
  if (!env.DB) return json({ error: '课途云端保存服务暂不可用。' }, 503);
  try {
    return json(await listCompassProfile(env.DB, userId));
  } catch (error) {
    return apiError(error);
  }
}

async function handlePUT(req: Request) {
  const userId = user(req);
  if (!userId) return json({ error: '请先使用学号登录。' }, 401);
  if (req.headers.get('origin') !== new URL(req.url).origin) return json({ error: '请从本站提交。' }, 403);
  if (!env.DB) return json({ error: '课途云端保存服务暂不可用。' }, 503);
  try {
    const body = await req.text();
    if (new TextEncoder().encode(body).byteLength > 4 * 1024) throw new CompassStateError('活动快照请求过大。', 413);
    let input: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(body);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid');
      input = parsed as Record<string, unknown>;
    } catch {
      throw new CompassStateError('活动快照请求不是有效 JSON。', 400);
    }
    if (typeof input.snapshotId !== 'string' || input.snapshotId.length > 100 || !Number.isInteger(input.expectedVersion) || Number(input.expectedVersion) < 0) {
      throw new CompassStateError('活动快照请求格式不正确。', 400);
    }
    return json(await activateCompassSnapshot(env.DB, userId, input.snapshotId, Number(input.expectedVersion)));
  } catch (error) {
    return apiError(error);
  }
}

export async function GET(req:Request) { return withStudentAccess(req, handleGET); }

export async function PUT(req:Request) { return withStudentAccess(req, handlePUT); }
