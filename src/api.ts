export type Message = { role: 'user' | 'assistant'; content: string };
export type Memory = { id: string; kind: string; content: string };
export type Knowledge = { id: string; title: string; kind: string; size: number };
export type State = { memories: Memory[]; conversations: { id: string; title: string }[]; knowledge: Knowledge[] };
export type Change = { action: string; content: string };
export type Reply = { answer: string; changes: Change[]; warning: string; sources: { title: string; kind: string }[] };

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.detail || 'Không hoàn tất được yêu cầu.');
  return data;
}

export function jsonBody(body: unknown, key?: string): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) }, body: JSON.stringify(body) };
}
