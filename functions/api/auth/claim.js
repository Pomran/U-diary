import { claimNick, json } from '../../lib.js';

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: 'bad json' }, 400);
  }
  const result = await claimNick(env, body.nickname, body.secret, body.device);
  return json(result, result.ok ? 200 : 400);
}
