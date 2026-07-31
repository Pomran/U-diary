export const BUCKET_BASE = 'https://pub-af6cc2aa40a64382b17825de8e4a74e0.r2.dev';

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

export function shanghaiToday() {
  return new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
}

export function randomSalt(len = 8) {
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  return [...arr].map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function hashSecret(secret, salt) {
  const data = new TextEncoder().encode(`${salt}:${secret}`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function claimNick(env, nickname, secret, device) {
  const name = String(nickname || '').trim();
  if (!name) return { ok: false, error: '请输入昵称' };
  if (!/^[\u4e00-\u9fa5A-Za-z0-9_-]{1,20}$/.test(name)) {
    return { ok: false, error: '昵称限 1-20 字，中英文/数字/下划线' };
  }

  const key = `nick:${name}`;
  const raw = await env.DIARY_KV.get(key);

  if (!raw) {
    const sec = String(secret || '').trim();
    if (sec.length < 4) return { ok: false, error: '新昵称请设置至少 4 位口令' };
    const salt = randomSalt();
    const hash = await hashSecret(sec, salt);
    await env.DIARY_KV.put(key, JSON.stringify({
      salt,
      hash,
      device: String(device || ''),
      createdAt: Date.now(),
    }));
    return { ok: true, created: true, nickname: name };
  }

  const rec = JSON.parse(raw);
  if (device && rec.device && device === rec.device) {
    return { ok: true, nickname: name };
  }
  const sec = String(secret || '').trim();
  if (!sec) return { ok: false, error: '该昵称已被占用，请输入正确口令' };
  const hash = await hashSecret(sec, rec.salt);
  if (hash === rec.hash) return { ok: true, nickname: name };
  return { ok: false, error: '昵称或口令不正确' };
}
