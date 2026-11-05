import type { D1Database } from '@cloudflare/workers-types';

export type CompassSnapshotState = {
  profile: {
    goal: 'research' | 'industry' | 'explore' | 'balanced';
    plan: string;
    term: string;
    maxCredits: number;
    hours: number;
    freeWednesday: boolean;
    completed: string[];
    englishTier: 'A' | 'B' | 'Y';
    development: string;
    branches: Record<string, string>;
  };
  activeSlot: 'A' | 'B';
  records: JsonValue[];
  recognitions: JsonValue[];
  checks: Record<string, JsonValue>;
  allocations: Record<string, JsonValue>;
  planProfiles: Record<string, JsonValue>;
  plans: { A: { course: string; section: string }[]; B: { course: string; section: string }[] };
};

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type SnapshotRow = {
  snapshot_id: string;
  user_id: string;
  label: string;
  state_json: string;
  version: number;
  source: string;
  import_key: string | null;
  created_at: string;
  updated_at: string;
};
type ProfileRow = { user_id: string; active_snapshot_id: string | null; version: number; updated_at: string };

export class CompassStateError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

const plainObject = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;

function boundedJson(value: unknown, depth = 0): JsonValue {
  if (depth > 8) throw new CompassStateError('规划状态嵌套过深。', 400);
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    if (value.length > 12_000) throw new CompassStateError('单个规划字段过长。', 400);
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length > 2_000) throw new CompassStateError('规划记录数量过多。', 400);
    return value.map(item => boundedJson(item, depth + 1));
  }
  if (plainObject(value)) {
    const entries = Object.entries(value);
    if (entries.length > 1_000) throw new CompassStateError('规划字段数量过多。', 400);
    const output: Record<string, JsonValue> = {};
    for (const [key, item] of entries) {
      if (/(api.?key|deepseek)/i.test(key) || /^(messages|history|trace)$/i.test(key)) {
        throw new CompassStateError('快照不能包含 API Key 或聊天记录。', 400);
      }
      if (key.length > 160) throw new CompassStateError('规划字段名称过长。', 400);
      output[key] = boundedJson(item, depth + 1);
    }
    return output;
  }
  throw new CompassStateError('规划状态包含不支持的数据。', 400);
}

function recordMap(value: unknown, name: string): Record<string, JsonValue> {
  if (!plainObject(value)) throw new CompassStateError(`规划状态的 ${name} 格式不正确。`, 400);
  return boundedJson(value) as Record<string, JsonValue>;
}

export function parseCompassSnapshot(input: unknown): CompassSnapshotState {
  if (!plainObject(input)) throw new CompassStateError('规划快照格式不正确。', 400);
  const allowed = ['profile', 'activeSlot', 'records', 'recognitions', 'checks', 'allocations', 'planProfiles', 'plans'];
  if (Object.keys(input).some(key => !allowed.includes(key))) {
    throw new CompassStateError('规划快照包含不支持的字段；聊天记录与 API Key 不会保存。', 400);
  }
  const p = input.profile;
  if (!plainObject(p)) throw new CompassStateError('规划者资料格式不正确。', 400);
  const allowedProfile = ['goal', 'plan', 'term', 'maxCredits', 'hours', 'freeWednesday', 'completed', 'englishTier', 'development', 'branches'];
  if (Object.keys(p).some(key => !allowedProfile.includes(key))) {
    throw new CompassStateError('规划资料包含不支持的字段；API Key 不会保存。', 400);
  }
  const goals = ['research', 'industry', 'explore', 'balanced'];
  const completed = p.completed;
  if (!Array.isArray(completed) || completed.length > 300 || completed.some(item => typeof item !== 'string' || item.length > 100)) {
    throw new CompassStateError('已修课程列表格式不正确。', 400);
  }
  const branches = p.branches === undefined ? {} : p.branches;
  if (!plainObject(branches) || Object.keys(branches).length > 150 || Object.keys(branches).some(key => /(api.?key|deepseek)/i.test(key)) || Object.values(branches).some(v => typeof v !== 'string' || v.length > 100)) {
    throw new CompassStateError('培养方案选择格式不正确。', 400);
  }
  if (!goals.includes(String(p.goal)) || typeof p.plan !== 'string' || p.plan.length > 100 ||
      typeof p.term !== 'string' || !/^20\d{2}(春|秋|暑)$/.test(p.term) ||
      typeof p.maxCredits !== 'number' || p.maxCredits < 1 || p.maxCredits > 40 ||
      typeof p.hours !== 'number' || p.hours < 1 || p.hours > 80 ||
      typeof p.freeWednesday !== 'boolean' || !['A', 'B', 'Y'].includes(String(p.englishTier)) ||
      typeof p.development !== 'string' || p.development.length > 100 ||
      !['A', 'B'].includes(String(input.activeSlot))) {
    throw new CompassStateError('规划目标或学期设置格式不正确。', 400);
  }

  const plans = input.plans;
  if (!plainObject(plans)) throw new CompassStateError('候选方案格式不正确。', 400);
  const parsePlan = (slot: unknown) => {
    if (!Array.isArray(slot) || slot.length > 150) throw new CompassStateError('候选课程数量不正确。', 400);
    return slot.map(item => {
      if (!plainObject(item) || typeof item.course !== 'string' || item.course.length > 100 ||
          typeof item.section !== 'string' || item.section.length > 100) {
        throw new CompassStateError('候选课程格式不正确。', 400);
      }
      return { course: item.course, section: item.section };
    });
  };
  const records = input.records ?? [];
  const recognitions = input.recognitions ?? [];
  if (!Array.isArray(records) || records.length > 2_000 || !Array.isArray(recognitions) || recognitions.length > 500) {
    throw new CompassStateError('修读与认定记录数量不正确。', 400);
  }
  const state: CompassSnapshotState = {
    profile: {
      goal: p.goal as CompassSnapshotState['profile']['goal'],
      plan: p.plan,
      term: p.term,
      maxCredits: p.maxCredits,
      hours: p.hours,
      freeWednesday: p.freeWednesday,
      completed: completed as string[],
      englishTier: p.englishTier as CompassSnapshotState['profile']['englishTier'],
      development: p.development,
      branches: branches as Record<string, string>,
    },
    activeSlot: input.activeSlot as 'A' | 'B',
    records: boundedJson(records) as JsonValue[],
    recognitions: boundedJson(recognitions) as JsonValue[],
    checks: recordMap(input.checks ?? {}, '核对状态'),
    allocations: recordMap(input.allocations ?? {}, '学分分配'),
    planProfiles: recordMap(input.planProfiles ?? {}, '方案设置'),
    plans: { A: parsePlan(plans.A ?? []), B: parsePlan(plans.B ?? []) },
  };
  if (new TextEncoder().encode(JSON.stringify(state)).byteLength > 512 * 1024) {
    throw new CompassStateError('规划快照超过 512 KB。', 413);
  }
  return state;
}

export async function ensureCompassProfile(db: D1Database, userId: string): Promise<ProfileRow> {
  const now = new Date().toISOString();
  await db.prepare('INSERT OR IGNORE INTO compass_profiles (user_id, active_snapshot_id, version, updated_at) VALUES (?, NULL, 0, ?)').bind(userId, now).run();
  const row = await db.prepare('SELECT user_id, active_snapshot_id, version, updated_at FROM compass_profiles WHERE user_id=?').bind(userId).first<ProfileRow>();
  if (!row) throw new Error('Could not initialize course planner profile');
  return row;
}

export async function listCompassProfile(db: D1Database, userId: string) {
  const profile = await ensureCompassProfile(db, userId);
  const result = await db.prepare(
    'SELECT snapshot_id, label, version, source, created_at, updated_at FROM compass_snapshots WHERE user_id=? ORDER BY updated_at DESC, created_at DESC LIMIT 30'
  ).bind(userId).all<Omit<SnapshotRow, 'user_id' | 'state_json' | 'import_key'>>();
  let activeState: CompassSnapshotState | null = null;
  let activeVersion: number | null = null;
  if (profile.active_snapshot_id) {
    const active = await db.prepare('SELECT state_json, version FROM compass_snapshots WHERE snapshot_id=? AND user_id=?').bind(profile.active_snapshot_id, userId).first<{ state_json: string; version: number }>();
    if (active) {
      activeState = parseCompassSnapshot(JSON.parse(active.state_json));
      activeVersion = active.version;
    }
  }
  return {
    profileVersion: profile.version,
    activeSnapshotId: profile.active_snapshot_id,
    activeVersion,
    activeState,
    snapshots: result.results.map(row => ({
      snapshotId: row.snapshot_id, label: row.label, version: row.version,
      source: row.source, createdAt: row.created_at, updatedAt: row.updated_at,
    })),
  };
}

export async function getCompassSnapshot(db: D1Database, userId: string, snapshotId: string) {
  const row = await db.prepare('SELECT * FROM compass_snapshots WHERE snapshot_id=? AND user_id=?').bind(snapshotId, userId).first<SnapshotRow>();
  if (!row) return null;
  return {
    snapshotId: row.snapshot_id, label: row.label, version: row.version, source: row.source,
    createdAt: row.created_at, updatedAt: row.updated_at, state: parseCompassSnapshot(JSON.parse(row.state_json)),
  };
}

export async function createCompassSnapshot(
  db: D1Database,
  userId: string,
  input: { label: string; state: unknown; source: string; importKey: string | null },
) {
  const label = input.label.trim();
  if (!label || label.length > 100) throw new CompassStateError('请填写 1—100 字的快照名称。', 400);
  if (!['local', 'browser', 'recovery'].includes(input.source)) throw new CompassStateError('快照来源不正确。', 400);
  if (input.importKey !== null && (input.importKey.length < 8 || input.importKey.length > 120 || !/^[\w:.-]+$/.test(input.importKey))) {
    throw new CompassStateError('导入标识格式不正确。', 400);
  }
  const state = parseCompassSnapshot(input.state);
  const stateJson = JSON.stringify(state);
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  const insert = input.importKey
    ? await db.prepare('INSERT INTO compass_snapshots (snapshot_id,user_id,label,state_json,version,source,import_key,created_at,updated_at) VALUES (?,?,?,?,1,?,?,?,?) ON CONFLICT(user_id,import_key) DO NOTHING')
        .bind(id, userId, label, stateJson, input.source, input.importKey, now, now).run()
    : await db.prepare('INSERT INTO compass_snapshots (snapshot_id,user_id,label,state_json,version,source,import_key,created_at,updated_at) VALUES (?,?,?,?,1,?,NULL,?,?)')
        .bind(id, userId, label, stateJson, input.source, now, now).run();
  const snapshot = input.importKey
    ? await db.prepare('SELECT * FROM compass_snapshots WHERE user_id=? AND import_key=?').bind(userId, input.importKey).first<SnapshotRow>()
    : await db.prepare('SELECT * FROM compass_snapshots WHERE snapshot_id=? AND user_id=?').bind(id, userId).first<SnapshotRow>();
  if (!snapshot) throw new Error('Could not save course planner snapshot');
  return {
    snapshot: {
      snapshotId: snapshot.snapshot_id, label: snapshot.label, version: snapshot.version,
      source: snapshot.source, createdAt: snapshot.created_at, updatedAt: snapshot.updated_at,
      state: parseCompassSnapshot(JSON.parse(snapshot.state_json)),
    },
    created: (insert.meta?.changes ?? 0) > 0,
  };
}

export async function saveCompassSnapshot(
  db: D1Database,
  userId: string,
  snapshotId: string,
  expectedVersion: number,
  input: unknown,
) {
  const state = parseCompassSnapshot(input);
  const profile = await ensureCompassProfile(db, userId);
  if (profile.active_snapshot_id !== snapshotId) {
    const active = profile.active_snapshot_id ? await getCompassSnapshot(db, userId, profile.active_snapshot_id) : null;
    throw Object.assign(new CompassStateError('账号中的活动规划已在其他设备切换。请选择载入新版本，或将本机规划另存。', 409), {
      current: active,
      profileVersion: profile.version,
    });
  }
  const now = new Date().toISOString();
  const result = await db.prepare(
    'UPDATE compass_snapshots SET state_json=?, version=version+1, updated_at=? WHERE snapshot_id=? AND user_id=? AND version=?'
  ).bind(JSON.stringify(state), now, snapshotId, userId, expectedVersion).run();
  if ((result.meta?.changes ?? 0) === 0) {
    const current = await getCompassSnapshot(db, userId, snapshotId);
    if (!current) throw new CompassStateError('规划快照不存在。', 404);
    const latestProfile = await ensureCompassProfile(db, userId);
    const active = latestProfile.active_snapshot_id === snapshotId ? current : latestProfile.active_snapshot_id
      ? await getCompassSnapshot(db, userId, latestProfile.active_snapshot_id)
      : null;
    throw Object.assign(new CompassStateError('云端规划已在其他设备更新。请选择保留哪一份。', 409), {
      current: active,
      profileVersion: latestProfile.version,
    });
  }
  const saved = await getCompassSnapshot(db, userId, snapshotId);
  if (!saved) throw new Error('Saved course planner snapshot could not be loaded');
  return saved;
}

export async function activateCompassSnapshot(db: D1Database, userId: string, snapshotId: string, expectedVersion: number) {
  const owned = await db.prepare('SELECT snapshot_id FROM compass_snapshots WHERE snapshot_id=? AND user_id=?').bind(snapshotId, userId).first();
  if (!owned) throw new CompassStateError('规划快照不存在。', 404);
  await ensureCompassProfile(db, userId);
  const now = new Date().toISOString();
  const result = await db.prepare(
    'UPDATE compass_profiles SET active_snapshot_id=?, version=version+1, updated_at=? WHERE user_id=? AND version=?'
  ).bind(snapshotId, now, userId, expectedVersion).run();
  if ((result.meta?.changes ?? 0) === 0) {
    const current = await ensureCompassProfile(db, userId);
    throw Object.assign(new CompassStateError('账号中的活动规划已在其他设备更改，请重新加载。', 409), { profileVersion: current.version });
  }
  return listCompassProfile(db, userId);
}

export function apiError(error: unknown) {
  if (error instanceof CompassStateError) {
    const details = error as CompassStateError & { current?: unknown; profileVersion?: number };
    return Response.json({ error: error.message, ...(details.current ? { current: details.current } : {}), ...(details.profileVersion !== undefined ? { profileVersion: details.profileVersion } : {}) }, {
      status: error.status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
    });
  }
  return Response.json({ error: '课途保存服务暂不可用，请稍后重试。' }, {
    status: 503, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
  });
}
