import { json } from '../lib.js';

const MASTER_KEY = 'ud-diary-2024';

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const key = url.searchParams.get('key');
  if (key !== MASTER_KEY) {
    return json({ ok: false, error: '密钥不正确' }, 403);
  }

  const list = await env.DIARY_KV.list({ prefix: 'feedback:' });
  const items = [];
  for (const { name } of list.keys) {
    const raw = await env.DIARY_KV.get(name);
    if (raw) {
      try {
        items.push({ id: name.slice(9), ...JSON.parse(raw) });
      } catch { /* skip */ }
    }
  }
  items.sort((a, b) => b.time - a.time);
  return json(items);
}

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: 'bad json' }, 400);
  }

  const text = String(body.text || '').trim();
  if (!text || text.length > 500) {
    return json({ ok: false, error: '反馈内容需在 1-500 字之间' }, 400);
  }

  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  await env.DIARY_KV.put(`feedback:${id}`, JSON.stringify({ text, time: Date.now() }));
  return json({ ok: true, id });
}
