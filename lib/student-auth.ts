type AuthEnv = { DB?: any; STUDENT_PASSWORD_PEPPER?: string; REVIEW_ADMIN_EMAILS?: string };
type Account = { id: string; student_number: string; nickname: string; password_hash: string; salt: string; recovery_hash: string; status: string; review_note: string };
const encoder = new TextEncoder();
const maxAge = 7 * 24 * 60 * 60;
const json = (body: unknown, status = 200, headers: Record<string, string> = {}) => Response.json(body, {
  status, headers: { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', ...headers },
});
const hex = (data: ArrayBuffer | Uint8Array) => Array.from(new Uint8Array(data)).map(v => v.toString(16).padStart(2, '0')).join('');
const random = (bytes = 32) => hex(crypto.getRandomValues(new Uint8Array(bytes)));
async function digest(value: string) { return hex(await crypto.subtle.digest('SHA-256', encoder.encode(value))); }
async function passwordHash(password: string, salt: string, pepper: string) {
  const hmac = await crypto.subtle.importKey('raw', encoder.encode(pepper), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const secret = await crypto.subtle.sign('HMAC', hmac, encoder.encode(password));
  const key = await crypto.subtle.importKey('raw', secret, 'PBKDF2', false, ['deriveBits']);
  return hex(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', iterations: 100000, salt: encoder.encode(salt) }, key, 256));
}
function equal(a: string, b: string) {
  let difference = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) difference |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return difference === 0;
}
function validPassword(value: unknown): value is string { return typeof value === 'string' && value.length >= 12 && value.length <= 128; }
function publicAccount(a: Account) { return { displayName: a.nickname, studentNumber: a.student_number, status: a.status, reviewNote: a.review_note }; }
function safeReturn(value: string | null) {
  if (!value?.startsWith('/') || value.startsWith('//')) return '/index.html';
  try { const u = new URL(value, 'https://atlas.invalid'); return u.origin === 'https://atlas.invalid' && !u.pathname.startsWith('/api/') && u.pathname !== '/login.html' ? u.pathname + u.search + u.hash : '/index.html'; } catch { return '/index.html'; }
}
export function createStudentAuth(env: AuthEnv, clock = () => Date.now()) {
  function platformAdmin(req: Request) {
    const uid = req.headers.get('oai-authenticated-user-id');
    const email = req.headers.get('oai-authenticated-user-email')?.trim().toLowerCase();
    return !!uid && !!email && String(env.REVIEW_ADMIN_EMAILS || '').split(',').some(v => v.trim().toLowerCase() === email);
  }
  const cookieName = (req: Request) => new URL(req.url).protocol === 'https:' ? '__Host-atlas_session' : 'atlas_session';
  function cookie(req: Request, token: string, age = maxAge) {
    return `${cookieName(req)}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${age}${new URL(req.url).protocol === 'https:' ? '; Secure' : ''}`;
  }
  function token(req: Request) {
    const matches = (req.headers.get('cookie') || '').split(';').map(v => v.trim()).filter(v => v.startsWith(cookieName(req) + '='));
    const value = matches.length === 1 ? matches[0].slice(cookieName(req).length + 1) : '';
    return /^[a-f0-9]{64}$/.test(value) ? value : null;
  }
  async function current(req: Request): Promise<Account | null> {
    const value = token(req);
    if (!value || !env.DB) return null;
    return env.DB.prepare('SELECT a.* FROM student_accounts a JOIN student_sessions s ON s.account_id=a.id WHERE s.token_hash=? AND s.expires_at>?').bind(await digest(value), clock()).first();
  }
  async function session(req: Request, account: Account) {
    const value = random();
    await env.DB.prepare('DELETE FROM student_sessions WHERE expires_at<=?').bind(clock()).run();
    await env.DB.prepare('INSERT INTO student_sessions (token_hash,account_id,expires_at,created_at) VALUES (?,?,?,?)').bind(await digest(value), account.id, clock() + maxAge * 1000, new Date(clock()).toISOString()).run();
    return cookie(req, value);
  }
  async function limited(req: Request, action: string, studentNumber = '') {
    const ip = req.headers.get('cf-connecting-ip') || 'unknown';
    const limits = [[`ip:${action}:${ip}`, action === 'register' ? 8 : 60], ...(studentNumber ? [[`id:${action}:${studentNumber}`, 10]] : [])];
    for (const [key, limit] of limits) {
      const row = await env.DB.prepare('INSERT INTO auth_rate_limits (key,count,reset_at) VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN reset_at<=? THEN 1 ELSE count+1 END,reset_at=CASE WHEN reset_at<=? THEN excluded.reset_at ELSE reset_at END RETURNING count').bind(await digest(String(key)), clock() + 15 * 60 * 1000, clock(), clock()).first();
      if (row.count > Number(limit)) return true;
    }
    return false;
  }
  async function input(req: Request) {
    if (req.headers.get('origin') !== new URL(req.url).origin || req.headers.get('sec-fetch-site') === 'cross-site') throw new Error('origin');
    if (!req.headers.get('content-type')?.startsWith('application/json')) throw new Error('input');
    if (Number(req.headers.get('content-length') || 0) > 4096) throw new Error('input');
    const raw = await req.text();
    if (raw.length > 4096) throw new Error('input');
    const body = JSON.parse(raw);
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('input');
    return body;
  }
  async function status(req: Request) {
    const account = await current(req);
    if (account?.status === 'approved') return json({ signedIn: true, isModerator: platformAdmin(req), user: publicAccount(account), authType: 'student' });
    if (platformAdmin(req)) return json({ signedIn: true, isModerator: true, user: { displayName: '网站管理员', status: 'approved' }, authType: 'administrator' });
    return json({ signedIn: account?.status === 'approved', isModerator: false, user: account ? publicAccount(account) : null, authType: 'student' });
  }
  async function action(req: Request, path: string) {
    if (!env.DB || !env.STUDENT_PASSWORD_PEPPER) return json({ error: '账户服务正在准备，请稍后再试。' }, 503);
    const body = await input(req);
    if (path === 'logout') {
      const value = token(req);
      if (value) await env.DB.prepare('DELETE FROM student_sessions WHERE token_hash=?').bind(await digest(value)).run();
      return json({ ok: true }, 200, { 'Set-Cookie': cookie(req, '', 0) });
    }
    if (path === 'decision') {
      if (!platformAdmin(req)) return json({ error: '只有管理员可以审核账号。' }, 403);
      if (!['approved','rejected','suspended'].includes(body.status) || typeof body.id !== 'string') return json({ error: '审核参数不正确。' }, 400);
      const row = await env.DB.prepare('SELECT id FROM student_accounts WHERE id=?').bind(body.id).first();
      if (!row) return json({ error: '账号不存在。' }, 404);
      await env.DB.batch([
        env.DB.prepare('UPDATE student_accounts SET status=?,reviewed_at=?,reviewed_by=?,review_note=? WHERE id=?').bind(body.status, new Date(clock()).toISOString(), req.headers.get('oai-authenticated-user-id'), String(body.note || '').slice(0, 300), body.id),
        env.DB.prepare("DELETE FROM student_sessions WHERE account_id=? AND ?!='approved'").bind(body.id, body.status),
      ]);
      return json({ ok: true });
    }
    if (path === 'password') {
      const account = await current(req);
      if (!account || account.status !== 'approved') return json({ error: '请先登录。' }, 401);
      if (await limited(req, 'password', account.student_number)) return json({ error: '尝试次数较多，请15分钟后再试。' }, 429);
      if (typeof body.oldPassword !== 'string' || !validPassword(body.password)) return json({ error: '新密码需要12—128个字符。' }, 400);
      if (!equal(await passwordHash(body.oldPassword, account.salt, env.STUDENT_PASSWORD_PEPPER), account.password_hash)) return json({ error: '当前密码不正确。' }, 400);
      const salt = random(24);
      await env.DB.batch([
        env.DB.prepare('UPDATE student_accounts SET password_hash=?,salt=? WHERE id=?').bind(await passwordHash(body.password, salt, env.STUDENT_PASSWORD_PEPPER), salt, account.id),
        env.DB.prepare('DELETE FROM student_sessions WHERE account_id=?').bind(account.id),
      ]);
      return json({ ok: true }, 200, { 'Set-Cookie': await session(req, account) });
    }
    const number = typeof body.studentNumber === 'string' ? body.studentNumber.trim() : '';
    if (!/^\d{11}$/.test(number)) return json({ error: '请输入11位学号。' }, 400);
    if (await limited(req, path, number)) return json({ error: '尝试次数较多，请15分钟后再试。' }, 429, { 'Retry-After': '900' });
    if (path === 'register') {
      if (!validPassword(body.password)) return json({ error: '请设置12—128个字符的本站密码。' }, 400);
      const nickname = String(body.nickname || '选课同学').trim().slice(0, 30) || '选课同学';
      const existing = await env.DB.prepare('SELECT id FROM student_accounts WHERE student_number=?').bind(number).first();
      if (existing) return json({ error: '该学号已注册，请登录或使用恢复码重设密码。' }, 409);
      const salt = random(24), recovery = random(24), id = crypto.randomUUID();
      try {
        await env.DB.prepare('INSERT INTO student_accounts (id,student_number,nickname,password_hash,salt,recovery_hash,status,created_at) VALUES (?,?,?,?,?,?,?,?)').bind(id, number, nickname, await passwordHash(body.password, salt, env.STUDENT_PASSWORD_PEPPER), salt, await digest(recovery), 'pending', new Date(clock()).toISOString()).run();
      } catch (e) {
        if (String(e).includes('UNIQUE')) return json({ error: '该学号已注册。' }, 409);
        throw e;
      }
      const account = { id, student_number: number, nickname, status: 'pending', review_note: '' } as Account;
      return json({ ok: true, user: publicAccount(account), recoveryCode: recovery }, 201, { 'Set-Cookie': await session(req, account) });
    }
    const account: Account | null = await env.DB.prepare('SELECT * FROM student_accounts WHERE student_number=?').bind(number).first();
    if (path === 'recover') {
      if (!validPassword(body.password) || typeof body.recoveryCode !== 'string' || body.recoveryCode.length > 100) return json({ error: '请输入恢复码和12—128个字符的新密码。' }, 400);
      if (!account || !equal(await digest(body.recoveryCode.trim()), account.recovery_hash)) return json({ error: '学号或恢复码不正确。' }, 400);
      const salt = random(24), recovery = random(24);
      await env.DB.batch([
        env.DB.prepare('UPDATE student_accounts SET password_hash=?,salt=?,recovery_hash=? WHERE id=?').bind(await passwordHash(body.password, salt, env.STUDENT_PASSWORD_PEPPER), salt, await digest(recovery), account.id),
        env.DB.prepare('DELETE FROM student_sessions WHERE account_id=?').bind(account.id),
      ]);
      return json({ ok: true, recoveryCode: recovery }, 200, { 'Set-Cookie': cookie(req, '', 0) });
    }
    if (typeof body.password !== 'string' || body.password.length > 128) return json({ error: '学号或密码不正确。' }, 401);
    const candidate = await passwordHash(body.password, account?.salt || 'unknown-account-salt', env.STUDENT_PASSWORD_PEPPER);
    if (!account || !equal(candidate, account.password_hash)) return json({ error: '学号或密码不正确。' }, 401);
    if (account.status === 'rejected' || account.status === 'suspended') return json({ error: account.review_note || '账号暂未获准访问，请联系管理员。' }, 403);
    return json({ ok: true, user: publicAccount(account), returnTo: safeReturn(body.returnTo) }, 200, { 'Set-Cookie': await session(req, account) });
  }
  async function handle(req: Request): Promise<{ response?: Response; request?: Request }> {
    const url = new URL(req.url), path = url.pathname;
    try {
      if (path === '/api/session' || path === '/api/auth/status') return { response: req.method === 'GET' ? await status(req) : json({ error: 'Method not allowed' }, 405) };
      if (path.startsWith('/api/auth/')) {
        const name = path.slice('/api/auth/'.length);
        if (name === 'accounts' && req.method === 'GET') {
          if (!platformAdmin(req)) return { response: json({ error: '只有管理员可以查看账号审核。' }, 403) };
          if (!env.DB) return { response: json({ error: '账户服务暂不可用。' }, 503) };
          const filter = url.searchParams.get('status') || 'pending';
          if (!['pending','approved','rejected','suspended'].includes(filter)) return { response: json({ error: '状态不正确。' }, 400) };
          const rows = await env.DB.prepare('SELECT id,student_number,nickname,status,created_at,reviewed_at,review_note FROM student_accounts WHERE status=? ORDER BY created_at DESC LIMIT 200').bind(filter).all();
          return { response: json({ accounts: rows.results }) };
        }
        if (!['login','register','logout','recover','password','decision'].includes(name)) return { response: json({ error: 'Not found' }, 404) };
        if (req.method !== 'POST') return { response: json({ error: 'Method not allowed' }, 405) };
        return { response: await action(req, name) };
      }
      if (['/login.html','/assets/student-login.css','/assets/student-login.js'].includes(path)) return { request: req };
      const account = await current(req);
      if (account?.status !== 'approved' && platformAdmin(req)) return { request: req };
      if (account?.status !== 'approved') {
        if (path.startsWith('/api/') || !['GET','HEAD'].includes(req.method)) return { response: json({ error: account ? '账号尚未通过访问审核。' : '请先使用学号登录。' }, 401) };
        return { response: new Response(null, { status: 302, headers: { Location: '/login.html?return_to=' + encodeURIComponent(safeReturn(path + url.search)), 'Cache-Control': 'private, no-store' } }) };
      }
      const headers = new Headers(req.headers);
      for (const name of [...headers.keys()]) if (name.startsWith('oai-authenticated-user-')) headers.delete(name);
      headers.set('oai-authenticated-user-id', 'student:' + account.id);
      if (platformAdmin(req)) headers.set('oai-authenticated-user-email', req.headers.get('oai-authenticated-user-email')!);
      headers.set('oai-authenticated-user-full-name', encodeURIComponent(account.nickname));
      headers.set('oai-authenticated-user-full-name-encoding', 'percent-encoded-utf-8');
      return { request: new Request(req.url, { method:req.method, headers, body:['GET','HEAD'].includes(req.method)?undefined:req.body, duplex:'half' } as RequestInit) };
    } catch (error) {
      if (error instanceof Error && error.message === 'origin') return { response: json({ error: '请从本站页面提交。' }, 403) };
      if (error instanceof SyntaxError || error instanceof Error && error.message === 'input') return { response: json({ error: '提交内容格式不正确。' }, 400) };
      console.error('[student-auth] request failed', error instanceof Error ? error.name : 'unknown');
      return { response: json({ error: '账户服务暂不可用，请稍后重试。' }, 503) };
    }
  }
  return { handle };
}
