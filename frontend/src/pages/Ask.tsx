import { useEffect, useRef, useState, type KeyboardEvent } from "react";

const BASE = "http://127.0.0.1:8000/api";

interface Source {
  kind: string;
  ref: string;
  detail: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

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

export function Ask() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // grow the composer with its content, up to a cap
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  const send = async (question: string) => {
    if (!question.trim() || busy) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.answer, sources: data.sources }]);
    } catch (e) {
      setError(String(e));
      setMessages((m) => m.slice(0, -1)); // roll back the unanswered question
    } finally {
      setBusy(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  // One compact, de-duplicated provenance line — the answer text already
  // names the entities, so sources only say WHERE the information came from.
  const sourceSummary = (sources: Source[]): string => {
    const parts = new Set<string>();
    for (const s of sources) {
      if (s.kind === "register") parts.add("the register");
      else if (s.kind === "letter") parts.add(s.ref.replace(/^letter:/i, ""));
      else if (s.kind === "board_update") parts.add("board notifications");
      else parts.add("review findings");
    }
    return [...parts].join(" · ");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="pgpt">
      <div className="pgpt-head">
        <div>
          <h1 className="pgpt-title">
            Portfolio<span>GPT</span>
          </h1>
          <p className="pgpt-sub">
            Ask across the register and the agent letters. Every answer reads the
            source text and cites where it came from.
          </p>
        </div>
        {!empty && (
          <button className="pgpt-new" onClick={() => { setMessages([]); setError(null); }}>
            New chat
          </button>
        )}
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
                    {sourceSummary(m.sources)}
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
              <div className="pgpt-typing"><span /><span /><span /></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <div className="pgpt-error">{error}</div>}

      <div className="pgpt-composer">
        <form onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <textarea
            ref={taRef}
            rows={1}
            value={input}
            placeholder="Ask about the register, the letters, deadlines, jurisdictions…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={busy}
          />
          <button className="pgpt-send" type="submit" disabled={busy || !input.trim()} aria-label="Send">
            ↑
          </button>
        </form>
        <p className="pgpt-disclaimer">
          PortfolioGPT only reads your register and the uploaded letters. Verify
          anything material against the cited source.
        </p>
      </div>
    </div>
  );
}
