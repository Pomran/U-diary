export async function onRequestGet({ env }) {
  const [likesKeys, commentsKeys] = await Promise.all([
    env.DIARY_KV.list({ prefix: 'likes:' }),
    env.DIARY_KV.list({ prefix: 'comments:' }),
  ]);

  const result = {};

  await Promise.all(likesKeys.keys.map(async ({ name }) => {
    const id = name.slice('likes:'.length);
    const val = await env.DIARY_KV.get(name);
    result[id] = { likes: parseInt(val || '0', 10), comments: 0 };
  }));

  await Promise.all(commentsKeys.keys.map(async ({ name }) => {
    const id = name.slice('comments:'.length);
    const val = await env.DIARY_KV.get(name);
    const arr = val ? JSON.parse(val) : [];
    result[id] = { likes: result[id]?.likes || 0, comments: arr.length };
  }));

  return Response.json(result);
}
