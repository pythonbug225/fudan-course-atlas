const MODEL_ENDPOINT = 'https://api.deepseek.com/chat/completions';
const MAX_REQUEST_BYTES = 256 * 1024;
const MAX_RESPONSE_BYTES = 1024 * 1024;

const json = (body: unknown, status = 200) => Response.json(body, {
  status,
  headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
});

export async function forwardDeepSeek(req: Request) {
  // Drain the submitted body before any early response so the next request can proceed.
  const bodyText = await req.text();
  if (new TextEncoder().encode(bodyText).byteLength > MAX_REQUEST_BYTES) {
    return json({ error: '模型请求过大，请缩短问题后重试。' }, 413);
  }
  const key = req.headers.get('x-deepseek-key')?.trim() ?? '';
  if (key.length < 20 || key.length > 500 || /[\r\n]/.test(key)) {
    return json({ error: '请重新输入有效的 DeepSeek API Key。' }, 400);
  }

  let input: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(bodyText);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid');
    input = parsed as Record<string, unknown>;
  } catch {
    return json({ error: '模型请求格式不正确。' }, 400);
  }
  if (!Array.isArray(input.messages) || input.messages.length < 1 || input.messages.length > 80 ||
      (input.tools !== undefined && (!Array.isArray(input.tools) || input.tools.length > 20))) {
    return json({ error: '对话或工具参数格式不正确。' }, 400);
  }

  const payload = {
    ...input,
    model: 'deepseek-flash',
    stream: false,
    max_tokens: typeof input.max_tokens === 'number' ? Math.min(2400, Math.max(1, Math.floor(input.max_tokens))) : 2400,
  };
  try {
    const upstream = await fetch(MODEL_ENDPOINT, {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(45_000),
    });
    if (upstream.status === 401 || upstream.status === 403) {
      return json({ error: 'DeepSeek API Key 无效或没有调用权限，请重新输入。' }, 401);
    }
    if (upstream.status === 429) return json({ error: 'DeepSeek 请求频率受限，请稍后重试。' }, 429);
    if (!upstream.ok) return json({ error: 'DeepSeek 暂时无法完成请求，请稍后重试。' }, 502);
    const responseText = await upstream.text();
    if (new TextEncoder().encode(responseText).byteLength > MAX_RESPONSE_BYTES) {
      return json({ error: '模型回复过大，请缩短问题后重试。' }, 502);
    }
    let response: unknown;
    try { response = JSON.parse(responseText); }
    catch { return json({ error: 'DeepSeek 返回了无法读取的响应，请稍后重试。' }, 502); }
    return json(response);
  } catch {
    return json({ error: '暂时无法连接 DeepSeek，请检查网络后重试。' }, 502);
  }
}
