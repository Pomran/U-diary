import { claimNick, shanghaiToday, randomSalt, json, BUCKET_BASE } from '../lib.js';

export async function onRequestPost({ request, env }) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: '请求格式错误' }, 400);
  }

  const nickname = String(form.get('nickname') || '').trim();
  const secret = String(form.get('secret') || '').trim();
  const device = String(form.get('device') || '');
  const caption = String(form.get('caption') || '').trim().slice(0, 120);
  const file = form.get('file');

  const auth = await claimNick(env, nickname, secret, device);
  if (!auth.ok) return json(auth, 400);

  if (!file || typeof file.arrayBuffer !== 'function') {
    return json({ ok: false, error: '请选择图片' }, 400);
  }
  if (!file.type || !file.type.startsWith('image/')) {
    return json({ ok: false, error: '仅支持图片文件' }, 400);
  }
  if (file.size > 10 * 1024 * 1024) {
    return json({ ok: false, error: '图片不能超过 10MB' }, 400);
  }

  const today = shanghaiToday();
  const quotaKey = `share:${nickname}:${today}`;
  if (await env.DIARY_KV.get(quotaKey)) {
    return json({ ok: false, error: '今天已经发过一张啦，明天再来' }, 400);
  }

  const photoId = 'pub-' + Date.now().toString(36) + randomSalt(3);
  const ext = (file.name ? file.name.split('.').pop() : 'jpg').toLowerCase().replace(/[^a-z0-9]/g, '') || 'jpg';
  const key = `shares/${today}/${photoId}.${ext}`;

  await env.DIARY_BUCKET.put(key, file.stream(), {
    httpMetadata: { contentType: file.type || 'image/jpeg' },
  });

  const share = {
    photoId,
    src: `${BUCKET_BASE}/${key}`,
    caption,
    nickname: auth.nickname || nickname,
    date: today,
    time: Date.now(),
  };
  await env.DIARY_KV.put(quotaKey, JSON.stringify(share));
  return json({ ok: true, share });
}
