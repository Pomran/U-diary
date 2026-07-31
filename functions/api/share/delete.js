import { claimNick, json } from '../../lib.js';

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: 'bad json' }, 400);
  }

  const photoId = String(body.photoId || '');
  const nickname = String(body.nickname || '').trim();
  const secret = String(body.secret || '').trim();
  const device = String(body.device || '');
  if (!photoId || !nickname) return json({ ok: false, error: '缺少参数' }, 400);

  const auth = await claimNick(env, nickname, secret, device);
  if (!auth.ok) return json(auth, 400);

  const list = await env.DIARY_KV.list({ prefix: `share:${nickname}:` });
  let found = null;
  for (const { name } of list.keys) {
    const raw = await env.DIARY_KV.get(name);
    if (raw) {
      try {
        const s = JSON.parse(raw);
        if (s.photoId === photoId) {
          found = { key: name, share: s };
          break;
        }
      } catch {
        /* skip */
      }
    }
  }
  if (!found) return json({ ok: false, error: '未找到该发布' }, 404);

  await env.DIARY_KV.delete(found.key);
  try {
    const rel = String(found.share.src).split('.r2.dev/')[1];
    if (rel) await env.DIARY_BUCKET.delete(rel);
  } catch {
    /* 图片删除失败不阻塞 */
  }
  return json({ ok: true });
}
