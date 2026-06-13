/**
 * PortfolioGPT chat types. History is persisted server-side (see backend
 * chat_store.py); the client just renders what the API returns.
 */

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

export interface ChatSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Conversation extends ChatSummary {
  messages: ChatMessage[];
}
