/**
 * PortfolioGPT chat page: a conversational interface for asking free-form
 * questions across the register, agent letters and board notifications.
 * Conversations are persisted server-side and cited sources open as PDFs.
 */
import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { api } from "../api";
import type { ChatMessage, ChatSummary } from "../chatStore";
import { sourceParts } from "../format";

const BASE = "http://127.0.0.1:8000/api";

// Load the PDF viewer (and PDF.js) only when a cited letter is opened.
const PdfViewer = lazy(() =>
  import("../components/PdfViewer").then((m) => ({ default: m.PdfViewer })),
);

// Questions Review and Register can't answer at a glance: summarising the
// letters, combining fields, and rolling up the portfolio. This is where the
// document retrieval and free-form reasoning earn their place.
const SUGGESTIONS = [
  {
    q: "What is each agent asking us to do in their letters, and by when?",
    hint: "Reads the agent letters",
  },
  {
    q: "Which dissolved or dormant entities still have an active board mandate?",
    hint: "Combines status and mandate",
  },
  {
    q: "What issues do the agent letters raise that our register doesn't show?",
    hint: "Letters vs the register",
  },
  {
    q: "Which jurisdictions have the most overdue or unknown filings?",
    hint: "Rolls up the portfolio",
  },
];

/** The PortfolioGPT chat page: conversation sidebar, message thread and composer. */
export function Ask() {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfFile, setPdfFile] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const empty = messages.length === 0;

  /** Re-fetch the conversation list (titles and ordering are owned by the server). */
  const refreshList = () =>
    api
      .listChats()
      .then(setChats)
      .catch(() => {});

  // load the conversation list once
  useEffect(() => {
    refreshList();
  }, []);

  // grow the composer with its content, up to a cap
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  // keep the latest turn in view as the thread grows
  useEffect(() => {
    setTimeout(
      () => bottomRef.current?.scrollIntoView({ behavior: "smooth" }),
      30,
    );
  }, [messages.length]);

  /** Load and display a stored conversation's full message history. */
  const openChat = async (id: string) => {
    if (id === activeId) return;
    setActiveId(id);
    setError(null);
    setMessages([]);
    try {
      const conv = await api.getChat(id);
      setMessages(conv.messages);
    } catch (e) {
      setError(String(e));
    }
  };

  /** Reset to a blank, unsaved conversation (no server call until the first message). */
  const newChat = () => {
    setActiveId(null);
    setMessages([]);
    setError(null);
    setInput("");
  };

  /** Delete a conversation server-side; if it was active, fall back to a new chat. */
  const deleteChat = async (id: string) => {
    try {
      await api.deleteChat(id);
    } catch {
      /* ignore — refresh will reflect the truth */
    }
    if (id === activeId) newChat();
    refreshList();
  };

  /**
   * Send a question: optimistically append it, await the answer, then store the
   * reply with its sources. On error the unanswered question is rolled back.
   */
  const send = async (question: string) => {
    if (!question.trim() || busy) return;
    const userMsg: ChatMessage = { role: "user", content: question };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const reply = await api.sendChat(question, activeId);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: reply.answer, sources: reply.sources },
      ]);
      if (reply.conversation_id !== activeId)
        setActiveId(reply.conversation_id);
      refreshList(); // titles / ordering live on the server
    } catch (e) {
      setError(String(e));
      setMessages((m) => m.slice(0, -1)); // roll back the unanswered question
    } finally {
      setBusy(false);
    }
  };

  // Enter sends, Shift+Enter inserts a newline.
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="pgpt-shell">
      <aside className="pgpt-sidebar">
        <button className="pgpt-newchat" onClick={newChat}>
          <span className="pgpt-newchat-plus">+</span> New chat
        </button>
        <div className="pgpt-history">
          {chats.length === 0 && (
            <div className="pgpt-history-empty">No conversations yet</div>
          )}
          {chats.map((c) => (
            <div
              key={c.id}
              className={`pgpt-history-item ${c.id === activeId ? "active" : ""}`}
              onClick={() => openChat(c.id)}
            >
              <span className="pgpt-history-title">{c.title}</span>
              <button
                className="pgpt-history-del"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteChat(c.id);
                }}
                aria-label="Delete conversation"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="pgpt">
        <div className="pgpt-head">
          <div>
            <h1 className="pgpt-title">
              Portfolio<span>GPT</span>
            </h1>
            <p className="pgpt-sub">Ask anything across your register, agent letters and board notifications.</p>
          </div>
        </div>

        {empty && (
          <div className="pgpt-suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s.q} className="pgpt-card" onClick={() => send(s.q)}>
                <span className="pgpt-card-q">{s.q}</span>
                <span className="pgpt-card-foot">
                  <span className="pgpt-card-hint">{s.hint}</span>
                  <span className="pgpt-card-arrow">→</span>
                </span>
              </button>
            ))}
          </div>
        )}

        <div className="pgpt-thread">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="pgpt-turn user">
                <div className="pgpt-bubble-user">{m.content}</div>
              </div>
            ) : (
              <div key={i} className="pgpt-turn answer">
                <div className="pgpt-avatar">✦</div>
                <div className="pgpt-answer-body">
                  <div className="pgpt-answer-text">{m.content}</div>
                  {m.sources && m.sources.length > 0 && (
                    <div className="pgpt-sources">
                      <span className="pgpt-sources-label">Sources</span>
                      {sourceParts(m.sources).map((p, j) => (
                        <span key={j}>
                          {j > 0 && " · "}
                          {p.file ? (
                            <button
                              type="button"
                              className="evidence-link"
                              onClick={() => setPdfFile(p.file!)}
                              title="Open this letter"
                            >
                              {p.label} ↗
                            </button>
                          ) : (
                            p.label
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ),
          )}
          {busy && (
            <div className="pgpt-turn answer">
              <div className="pgpt-avatar">✦</div>
              <div className="pgpt-answer-body">
                <div className="pgpt-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && <div className="pgpt-error">{error}</div>}

        <div className="pgpt-composer">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              ref={taRef}
              rows={1}
              value={input}
              placeholder="Ask about the register, the letters, deadlines, jurisdictions…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={busy}
            />
            <button
              className="pgpt-send"
              type="submit"
              disabled={busy || !input.trim()}
              aria-label="Send"
            >
              ↑
            </button>
          </form>
          <p className="pgpt-disclaimer">
            PortfolioGPT only uses your own data. Verify anything material
            against the cited source.
          </p>
        </div>
      </div>

      {pdfFile && (
        <Suspense
          fallback={
            <div className="pdf-overlay">
              <div className="pdf-status">Loading viewer…</div>
            </div>
          }
        >
          <PdfViewer
            url={`${BASE}/letters/${encodeURIComponent(pdfFile)}`}
            filename={pdfFile}
            highlight=""
            onClose={() => setPdfFile(null)}
          />
        </Suspense>
      )}
    </div>
  );
}
