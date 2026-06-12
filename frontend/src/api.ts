import type { DigestResponse, Entity, EntityDetail, Meta } from "./types";

const BASE = "http://127.0.0.1:8000/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // fresh=true forces real LLM calls (ignores the cache) for a live demo,
  // without overwriting the cached responses.
  triggerDigest: async (fresh = false): Promise<unknown> => {
    const res = await fetch(`${BASE}/digest${fresh ? "?fresh=true" : ""}`, { method: "POST" });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Review failed (${res.status})`);
    }
    return res.json();
  },
  clearDigest: async (): Promise<unknown> => {
    const res = await fetch(`${BASE}/digest`, { method: "DELETE" });
    if (!res.ok) throw new Error(`Clear failed: ${res.status}`);
    return res.json();
  },
  getDigest: () => get<DigestResponse>("/digest"),
  getEntities: (params: Record<string, string>) =>
    get<Entity[]>(`/entities?${new URLSearchParams(params)}`),
  getEntity: (id: string) => get<EntityDetail>(`/entities/${id}`),
  getMeta: () => get<Meta>("/meta"),
};
