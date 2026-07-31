async function buildHeatAll(env) {
  const [likesKeys, commentsKeys] = await Promise.all([
    env.DIARY_KV.list({ prefix: 'likes:' }),
    env.DIARY_KV.list({ prefix: 'comments:' }),
  ]);

  const all = {};

  for (const { name } of likesKeys.keys) {
    const id = name.slice('likes:'.length);
    const val = await env.DIARY_KV.get(name);
    all[id] = { likes: parseInt(val || '0', 10), comments: 0 };
  }

  for (const { name } of commentsKeys.keys) {
    const id = name.slice('comments:'.length);
    const val = await env.DIARY_KV.get(name);
    const count = val ? JSON.parse(val).length : 0;
    all[id] = { likes: all[id]?.likes || 0, comments: count };
  }

  const jsonStr = JSON.stringify(all);
  await env.DIARY_KV.put('heat:all', jsonStr);
  return all;
}

export async function onRequestGet({ env }) {
  const raw = await env.DIARY_KV.get('heat:all');
  if (raw) {
    try {
      return Response.json(JSON.parse(raw));
    } catch {
      /* 数据损坏，重建 */
    }
  }
  const all = await buildHeatAll(env);
  return Response.json(all);
}
