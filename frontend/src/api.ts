export type Json = Record<string, any>;
let credential = '';
export function setToken(value: string) { credential = value; }
export async function api<T = Json>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/${path}`, { method, signal, headers: { Authorization: `Bearer ${credential}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) {
    const error = await response.json().catch(() => ({detail: response.statusText}));
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail ?? error));
  }
  return response.json();
}
export async function exportTrades() {
  const response = await fetch('/api/journal/export.csv', {headers: {Authorization: `Bearer ${credential}`}});
  if (!response.ok) throw new Error('CSV export failed');
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'qros_trades.csv'; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function streamOverview(onOverview: (value: Json) => void, signal: AbortSignal) {
  const response = await fetch('/api/stream', { headers: { Authorization: `Bearer ${credential}` }, signal });
  if (!response.ok || !response.body) throw new Error('Overview stream unavailable');
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
  try {
    while (!signal.aborted) {
      const {done, value} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream: true}).replace(/\r\n/g, '\n');
      let end: number;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const event = buffer.slice(0,end); buffer = buffer.slice(end+2);
        if (event.includes('event: overview')) {
          const payload = event.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
          if (payload) onOverview(JSON.parse(payload));
        }
      }
    }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
