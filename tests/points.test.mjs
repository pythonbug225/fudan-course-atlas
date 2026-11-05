import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const index = JSON.parse(readFileSync(new URL('../public/data/exams-preview.json', import.meta.url), 'utf8'));
const files = index.sets.flatMap((set) => set.files);
const firstFile = files.find((file) => file.githubUrl);
const secondFile = files.find((file) => file.githubUrl && file.id !== firstFile?.id);
const unavailableFile = files.find((file) => !file.githubUrl);

let points;
try {
  points = await import('../lib/points.ts');
} catch (error) {
  if (error?.code === 'ERR_MODULE_NOT_FOUND') {
    throw new Error('RED: points response handlers are not implemented yet.', { cause: error });
  }
  throw error;
}

assert.equal(typeof points.getPointsResponse, 'function');
assert.equal(typeof points.checkInResponse, 'function');
assert.equal(typeof points.unlockExamResponse, 'function');
assert.ok(firstFile && secondFile && unavailableFile, 'exam index must include valid and unavailable file fixtures');

class SqliteD1 {
  constructor() {
    this.sqlite = new DatabaseSync(':memory:');
    this.sqlite.exec(`
      CREATE TABLE point_events (
        id TEXT PRIMARY KEY NOT NULL,
        user_id TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK (event_type IN ('checkin', 'exam_unlock')),
        event_key TEXT NOT NULL,
        delta INTEGER NOT NULL CHECK (delta <> 0),
        created_at TEXT NOT NULL,
        UNIQUE (user_id, event_key)
      );
      CREATE INDEX point_events_user_created ON point_events (user_id, created_at DESC);
    `);
  }

  prepare(sql) {
    return {
      bind: (...values) => ({
        first: async () => this.sqlite.prepare(sql).get(...values) ?? null,
        all: async () => ({ results: this.sqlite.prepare(sql).all(...values) }),
        run: async () => this.sqlite.prepare(sql).run(...values),
      }),
    };
  }

  countEvents() {
    return this.sqlite.prepare('SELECT COUNT(*) AS count FROM point_events').get().count;
  }

  close() {
    this.sqlite.close();
  }
}

function request(path, { method = 'GET', userId, origin = 'https://atlas.example', body } = {}) {
  const headers = new Headers();
  if (userId) headers.set('oai-authenticated-user-id', userId);
  if (origin) headers.set('origin', origin);
  if (body !== undefined) headers.set('content-type', 'application/json');
  return new Request(`https://atlas.example${path}`, {
    method,
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

async function json(response, expectedStatus = 200) {
  assert.equal(response.status, expectedStatus);
  return response.json();
}

test('checkin_uses_shanghai_calendar_day', async () => {
  const db = new SqliteD1();
  try {
    const beforeShanghaiMidnight = new Date('2026-11-03T15:59:59.000Z');
    const afterShanghaiMidnight = new Date('2026-11-03T16:00:00.000Z');

    const first = await json(await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1' }), db, beforeShanghaiMidnight));
    assert.deepEqual(first, { awarded: 5, alreadyCheckedIn: false, balance: 5 });

    const duplicate = await json(await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1' }), db, beforeShanghaiMidnight));
    assert.deepEqual(duplicate, { awarded: 0, alreadyCheckedIn: true, balance: 5 });

    const nextShanghaiDay = await json(await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1' }), db, afterShanghaiMidnight));
    assert.deepEqual(nextShanghaiDay, { awarded: 5, alreadyCheckedIn: false, balance: 10 });
  } finally {
    db.close();
  }
});

test('anonymous_and_cross_origin_writes_are_rejected', async () => {
  const db = new SqliteD1();
  try {
    await json(await points.checkInResponse(request('/api/points/checkin', { method: 'POST' }), db), 401);
    await json(await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1', origin: 'https://other.example' }), db), 403);
    await json(await points.unlockExamResponse(request(`/api/exams/${firstFile.id}/unlock`, { method: 'POST' }), db, firstFile.id), 401);
    assert.equal(db.countEvents(), 0);
  } finally {
    db.close();
  }
});

test('checkin_and_unlock_are_idempotent_per_user_key', async () => {
  const db = new SqliteD1();
  try {
    await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1' }), db);
    const url = `/api/exams/${firstFile.id}/unlock`;
    const parallel = await Promise.all([
      points.unlockExamResponse(request(url, { method: 'POST', userId: 'u1' }), db, firstFile.id),
      points.unlockExamResponse(request(url, { method: 'POST', userId: 'u1' }), db, firstFile.id),
    ]);
    const unlocks = await Promise.all(parallel.map((response) => response.json()));
    assert.deepEqual(unlocks.map((item) => item.charged).sort(), [0, 1]);
    assert.ok(unlocks.every((item) => item.balance === 4 && item.url === firstFile.githubUrl));

    const anotherFile = await json(await points.unlockExamResponse(request(`/api/exams/${secondFile.id}/unlock`, { method: 'POST', userId: 'u1' }), db, secondFile.id));
    assert.deepEqual({ charged: anotherFile.charged, balance: anotherFile.balance }, { charged: 1, balance: 3 });

    const anotherUser = await json(await points.getPointsResponse(request('/api/points', { userId: 'u2' }), db));
    assert.deepEqual({ balance: anotherUser.balance, checkedInToday: anotherUser.checkedInToday }, { balance: 0, checkedInToday: false });
    assert.equal(db.countEvents(), 3);
  } finally {
    db.close();
  }
});

test('unlock_ignores_client_supplied_identity_cost_and_url', async () => {
  const db = new SqliteD1();
  try {
    const forged = { userId: 'victim', points: 999, date: '2099-01-01', url: 'https://evil.example/file.pdf' };
    await points.checkInResponse(request('/api/points/checkin', { method: 'POST', userId: 'u1', body: forged }), db);
    const unlocked = await json(await points.unlockExamResponse(
      request(`/api/exams/${firstFile.id}/unlock`, { method: 'POST', userId: 'u1', body: forged }),
      db,
      firstFile.id,
    ));
    const victim = await json(await points.getPointsResponse(request('/api/points', { userId: 'victim' }), db));
    assert.deepEqual({ charged: unlocked.charged, balance: unlocked.balance }, { charged: 1, balance: 4 });
    assert.equal(unlocked.url, firstFile.githubUrl);
    assert.equal(victim.balance, 0);
    assert.equal(db.countEvents(), 2);
  } finally {
    db.close();
  }
});

test('insufficient_balance_and_unknown_file_do_not_write_or_return_url', async () => {
  const db = new SqliteD1();
  try {
    const insufficient = await json(await points.unlockExamResponse(
      request(`/api/exams/${firstFile.id}/unlock`, { method: 'POST', userId: 'u1' }),
      db,
      firstFile.id,
    ), 402);
    assert.equal(insufficient.error, 'insufficient_points');
    assert.equal('url' in insufficient, false);

    await json(await points.unlockExamResponse(
      request('/api/exams/unknown-file/unlock', { method: 'POST', userId: 'u1' }),
      db,
      'unknown-file',
    ), 404);
    await json(await points.unlockExamResponse(
      request(`/api/exams/${unavailableFile.id}/unlock`, { method: 'POST', userId: 'u1' }),
      db,
      unavailableFile.id,
    ), 404);
    assert.equal(db.countEvents(), 0);

    await json(await points.getPointsResponse(request('/api/points', { userId: 'u1' }), null), 503);
  } finally {
    db.close();
  }
});

test('api_routes_export_expected_methods_and_delegate_to_ledger', () => {
  const readRoute = (path) => {
    try {
      return readFileSync(new URL(path, import.meta.url), 'utf8');
    } catch (error) {
      if (error?.code === 'ENOENT') throw new Error(`RED: API route is not implemented: ${path}`, { cause: error });
      throw error;
    }
  };
  const pointsRoute = readRoute('../app/api/points/route.ts');
  const checkInRoute = readRoute('../app/api/points/checkin/route.ts');
  const unlockRoute = readRoute('../app/api/exams/[fileId]/unlock/route.ts');

  assert.match(pointsRoute, /export\s+async\s+function\s+GET\s*\(/);
  assert.match(pointsRoute, /getPointsResponse\s*\(\s*verified\s*,\s*env\.DB/);
  assert.match(checkInRoute, /export\s+async\s+function\s+POST\s*\(/);
  assert.match(checkInRoute, /checkInResponse\s*\(\s*verified\s*,\s*env\.DB/);
  assert.match(unlockRoute, /export\s+async\s+function\s+POST\s*\(/);
  assert.match(unlockRoute, /unlockExamResponse\s*\(\s*verified\s*,\s*env\.DB(?:\s*\?\?\s*null)?\s*,\s*fileId/);
});
