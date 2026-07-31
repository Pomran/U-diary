function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

async function syncHeat(env, photoId) {
  const [likesRaw, commentsRaw] = await Promise.all([
    env.DIARY_KV.get(`likes:${photoId}`),
    env.DIARY_KV.get(`comments:${photoId}`),
  ]);
  const likes = parseInt(likesRaw || '0', 10);
  const commentsCount = commentsRaw ? JSON.parse(commentsRaw).length : 0;

  const allRaw = await env.DIARY_KV.get('heat:all');
  const all = allRaw ? JSON.parse(allRaw) : {};
  all[photoId] = { likes, comments: commentsCount };
  await env.DIARY_KV.put('heat:all', JSON.stringify(all));
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

  if (body.action === 'like' || body.action === 'unlike') {
    const key = `likes:${id}`;
    const current = parseInt((await env.DIARY_KV.get(key)) || '0', 10);
    const next = body.action === 'unlike' ? Math.max(0, current - 1) : current + 1;
    await env.DIARY_KV.put(key, String(next));
    await syncHeat(env, id);
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
    comments.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8), text, time: Date.now() });
    const trimmed = comments.slice(-50);
    await env.DIARY_KV.put(key, JSON.stringify(trimmed));
    await syncHeat(env, id);
    return json({ ok: true, comments: trimmed });
  }

  if (body.action === 'deleteComment') {
    const key = `comments:${id}`;
    const raw = await env.DIARY_KV.get(key);
    const comments = raw ? JSON.parse(raw) : [];
    const next = comments.filter(c => !c.id || c.id !== body.commentId);
    if (next.length === comments.length) {
      return json({ ok: false, error: '评论不存在' }, 404);
    }
    await env.DIARY_KV.put(key, JSON.stringify(next));
    await syncHeat(env, id);
    return json({ ok: true, comments: next });
  }

  return json({ ok: false, error: 'unknown action' }, 400);
}
