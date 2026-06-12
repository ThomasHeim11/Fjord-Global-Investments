// PortfolioGPT conversation history, persisted in localStorage so it survives
// navigating between tabs and browser sessions — like ChatGPT's chat list.

export interface Source {
  kind: string;
  ref: string;
  detail: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}

const KEY = "pgpt.chats.v1";

export function loadChats(): Conversation[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveChats(chats: Conversation[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(chats));
  } catch {
    /* quota or private mode — history is best-effort */
  }
}

export function newId(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return `c-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

export function titleFrom(question: string): string {
  const t = question.trim().replace(/\s+/g, " ");
  return t.length > 56 ? `${t.slice(0, 56)}…` : t;
}
