import examIndex from '../public/data/exams-preview.json' with { type: 'json' };

type Database = {
  prepare(sql: string): {
    bind(...values: unknown[]): {
      first<T = Record<string, unknown>>(): Promise<T | null>;
      all<T = Record<string, unknown>>(): Promise<{ results: T[] }>;
      run(): Promise<{ changes?: number; meta?: { changes?: number } }>;
    };
  };
};

type ExamFile = { id: string; githubUrl?: string };
type ExamIndex = { sets?: Array<{ files?: ExamFile[] }> };
type PointEventRow = {
  id: string;
  event_type: 'checkin' | 'exam_unlock' | 'submission_reward' | 'submission_withdrawal';
  event_key: string;
  delta: number;
  created_at: string;
};

const files = new Map(
  ((examIndex as ExamIndex).sets ?? []).flatMap((set) => set.files ?? [])
    .filter((file) => file.id && isAllowedExamUrl(file.githubUrl))
    .map((file) => [file.id, file.githubUrl!] as const),
);

const json = (body: unknown, status = 200) => Response.json(body, {
  status,
  headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
});

function isAllowedExamUrl(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:'
      && url.hostname === 'github.com'
      && url.username === ''
      && url.password === ''
      && url.search === ''
      && url.hash === ''
      && url.pathname.startsWith('/Annan-lyn/fudan-exam-paper/blob/main/');
  } catch {
    return false;
  }
}

function userId(req: Request) {
  return req.headers.get('oai-authenticated-user-id')?.trim() || null;
}

function authorizeWrite(req: Request) {
  if (!userId(req)) return json({ error: 'authentication_required' }, 401);
  const origin = req.headers.get('origin');
  if (!origin || origin !== new URL(req.url).origin) return json({ error: 'invalid_origin' }, 403);
  return null;
}

function shanghaiDate(now: Date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? '';
  return `${part('year')}-${part('month')}-${part('day')}`;
}

function changedRows(result: { changes?: number; meta?: { changes?: number } }) {
  return Number(result.meta?.changes ?? result.changes ?? 0);
}

function reportDatabaseFailure(action: string, error: unknown) {
  const detail = error instanceof Error ? error.message : 'unknown database error';
  console.error(`[points] ${action} failed: ${detail}`);
}

async function balance(db: Database, uid: string) {
  const row = await db.prepare('SELECT COALESCE(SUM(delta), 0) AS balance FROM point_events WHERE user_id = ?')
    .bind(uid).first<{ balance: number }>();
  return Number(row?.balance ?? 0);
}

export async function getPointsResponse(req: Request, db: Database | null, now = new Date()) {
  const uid = userId(req);
  if (!uid) return json({ signedIn: false });
  if (!db) return json({ error: 'points_service_unavailable' }, 503);

  try {
    const today = shanghaiDate(now);
    const [summary, daily, recent] = await Promise.all([
      db.prepare('SELECT COALESCE(SUM(delta), 0) AS balance FROM point_events WHERE user_id = ?')
        .bind(uid).first<{ balance: number }>(),
      db.prepare('SELECT id FROM point_events WHERE user_id = ? AND event_key = ? LIMIT 1')
        .bind(uid, `checkin:${today}`).first(),
      db.prepare('SELECT id, event_type, event_key, delta, created_at FROM point_events WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 20')
        .bind(uid).all<PointEventRow>(),
    ]);
    return json({
      signedIn: true,
      balance: Number(summary?.balance ?? 0),
      checkedInToday: Boolean(daily),
      events: recent.results.map((event) => ({
        id: event.id,
        eventType: event.event_type,
        referenceId: event.event_type === 'checkin' ? null : event.event_key.slice(event.event_key.indexOf(':') + 1),
        delta: Number(event.delta),
        createdAt: event.created_at,
      })),
    });
  } catch (error) {
    reportDatabaseFailure('summary', error);
    return json({ error: 'points_service_unavailable' }, 503);
  }
}

export async function checkInResponse(req: Request, db: Database | null, now = new Date()) {
  const denied = authorizeWrite(req);
  if (denied) return denied;
  if (!db) return json({ error: 'points_service_unavailable' }, 503);

  try {
    const uid = userId(req)!;
    const today = shanghaiDate(now);
    const createdAt = now.toISOString();
    const result = await db.prepare('INSERT OR IGNORE INTO point_events (id, user_id, event_type, event_key, delta, created_at) VALUES (?, ?, ?, ?, ?, ?)')
      .bind(crypto.randomUUID(), uid, 'checkin', `checkin:${today}`, 5, createdAt).run();
    const awarded = changedRows(result) > 0 ? 5 : 0;
    return json({ awarded, alreadyCheckedIn: awarded === 0, balance: await balance(db, uid) });
  } catch (error) {
    reportDatabaseFailure('check-in', error);
    return json({ error: 'points_service_unavailable' }, 503);
  }
}

export async function unlockExamResponse(req: Request, db: Database | null, fileId: string, now = new Date()) {
  const denied = authorizeWrite(req);
  if (denied) return denied;
  if (!db) return json({ error: 'points_service_unavailable' }, 503);

  const url = files.get(fileId);
  if (!url) return json({ error: 'unknown_file' }, 404);

  try {
    const uid = userId(req)!;
    const eventKey = `exam:${fileId}`;
    const existing = await db.prepare('SELECT id FROM point_events WHERE user_id = ? AND event_key = ? LIMIT 1')
      .bind(uid, eventKey).first();
    if (existing) {
      return json({ url, charged: 0, alreadyUnlocked: true, balance: await balance(db, uid) });
    }

    const result = await db.prepare(`
      INSERT INTO point_events (id, user_id, event_type, event_key, delta, created_at)
      SELECT ?, ?, 'exam_unlock', ?, -1, ?
      WHERE (SELECT COALESCE(SUM(delta), 0) FROM point_events WHERE user_id = ?) >= 1
      ON CONFLICT(user_id, event_key) DO NOTHING
    `).bind(crypto.randomUUID(), uid, eventKey, now.toISOString(), uid).run();
    const charged = changedRows(result) > 0 ? 1 : 0;

    if (!charged) {
      const duplicate = await db.prepare('SELECT id FROM point_events WHERE user_id = ? AND event_key = ? LIMIT 1')
        .bind(uid, eventKey).first();
      if (!duplicate) {
        return json({ error: 'insufficient_points', balance: await balance(db, uid) }, 402);
      }
    }

    return json({ url, charged, alreadyUnlocked: charged === 0, balance: await balance(db, uid) });
  } catch (error) {
    reportDatabaseFailure('unlock', error);
    return json({ error: 'points_service_unavailable' }, 503);
  }
}
