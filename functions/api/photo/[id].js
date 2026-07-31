function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

export async function onRequestGet({ params, env }) {
  const id = params.id;
  const [likesRaw, commentsRaw] = await Promise.all([
    env.DIARY_KV.get(`likes:${id}`),
    env.DIARY_KV.get(`comments:${id}`),
  ]);
  return json({
    id,
    likes: parseInt(likesRaw || '0', 10),
    comments: commentsRaw ? JSON.parse(commentsRaw) : [],
  });
}

export async function onRequestPost({ request, params, env }) {
  const id = params.id;

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: 'bad json' }, 400);
  }

  if (body.action === 'like') {
    const key = `likes:${id}`;
    const current = parseInt((await env.DIARY_KV.get(key)) || '0', 10);
    const next = current + 1;
    await env.DIARY_KV.put(key, String(next));
    return json({ ok: true, likes: next });
  }

  if (body.action === 'comment') {
    const text = typeof body.text === 'string' ? body.text.trim() : '';
    if (!text) {
      return json({ ok: false, error: '评论不能为空' }, 400);
    }
    if (text.length > 200) {
      return json({ ok: false, error: '最多 200 字' }, 400);
    }

    const key = `comments:${id}`;
    const raw = await env.DIARY_KV.get(key);
    const comments = raw ? JSON.parse(raw) : [];
    comments.push({ text, time: Date.now() });
    const trimmed = comments.slice(-50);
    await env.DIARY_KV.put(key, JSON.stringify(trimmed));
    return json({ ok: true, comments: trimmed });
  }

  return json({ ok: false, error: 'unknown action' }, 400);
}
