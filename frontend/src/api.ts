import type { ChatSummary, Conversation, Source } from "./chatStore";
import type { DigestResponse, Entity, EntityDetail, Meta } from "./types";

const BASE = "http://127.0.0.1:8000/api";

interface ChatReply {
  conversation_id: string;
  answer: string;
  sources: Source[];
}

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
  getDigest: () => get<DigestResponse>("/digest"),
  getEntities: (params: Record<string, string>) =>
    get<Entity[]>(`/entities?${new URLSearchParams(params)}`),
  getEntity: (id: string) => get<EntityDetail>(`/entities/${id}`),
  getMeta: () => get<Meta>("/meta"),

  // PortfolioGPT — chat history persisted server-side
  listChats: () => get<ChatSummary[]>("/chats"),
  getChat: (id: string) => get<Conversation>(`/chats/${id}`),
  deleteChat: async (id: string): Promise<void> => {
    const res = await fetch(`${BASE}/chats/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  },
  sendChat: async (question: string, conversationId: string | null): Promise<ChatReply> => {
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
    }
    return res.json();
  },
};
