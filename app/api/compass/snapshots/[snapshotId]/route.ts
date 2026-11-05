import { withStudentAccess } from '../../../../../lib/student-access';
import { env } from 'cloudflare:workers';
import { user } from '../../../../../lib/community';
import { apiError, CompassStateError, getCompassSnapshot, saveCompassSnapshot } from '../../../../../lib/compass-state';

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

async function handleGET(req: Request, { params }: { params: Promise<{ snapshotId: string }> }) {
  const userId = user(req);
  if (!userId) return json({ error: '请先使用学号登录。' }, 401);
  if (!env.DB) return json({ error: '课途云端保存服务暂不可用。' }, 503);
  try {
    const { snapshotId } = await params;
    const snapshot = await getCompassSnapshot(env.DB, userId, snapshotId);
    return snapshot ? json(snapshot) : json({ error: '规划快照不存在。' }, 404);
  } catch (error) {
    return apiError(error);
  }
}

async function handlePUT(req: Request, { params }: { params: Promise<{ snapshotId: string }> }) {
  const userId = user(req);
  if (!userId) return json({ error: '请先使用学号登录。' }, 401);
  if (req.headers.get('origin') !== new URL(req.url).origin) return json({ error: '请从本站提交。' }, 403);
  if (!env.DB) return json({ error: '课途云端保存服务暂不可用。' }, 503);
  try {
    const { snapshotId } = await params;
    const input = await readBody(req);
    if (!Number.isInteger(input.expectedVersion) || Number(input.expectedVersion) < 1 || !('state' in input)) {
      throw new CompassStateError('快照保存请求格式不正确。', 400);
    }
    return json(await saveCompassSnapshot(env.DB, userId, snapshotId, Number(input.expectedVersion), input.state));
  } catch (error) {
    return apiError(error);
  }
}

export async function GET(req:Request, context:{params:Promise<{snapshotId:string}>}) { return withStudentAccess(req, verified => handleGET(verified,context)); }

export async function PUT(req:Request, context:{params:Promise<{snapshotId:string}>}) { return withStudentAccess(req, verified => handlePUT(verified,context)); }
