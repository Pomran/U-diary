import { json } from '../lib.js';

export async function onRequestGet({ env }) {
  const list = await env.DIARY_KV.list({ prefix: 'share:' });
  const shares = [];
  for (const { name } of list.keys) {
    const raw = await env.DIARY_KV.get(name);
    if (raw) {
      try {
        shares.push(JSON.parse(raw));
      } catch {
        /* 跳过损坏数据 */
      }
    }
  }
  shares.sort((a, b) => String(b.date).localeCompare(String(a.date)) || (b.time || 0) - (a.time || 0));
  return json(shares);
}
