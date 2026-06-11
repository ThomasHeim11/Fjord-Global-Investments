import { useRef, useState } from "react";
import { Link } from "react-router-dom";

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

const SUGGESTIONS = [
  "Which entities have the most urgent problems right now?",
  "What do the agent letters say that contradicts our register?",
  "Which Singapore entities have open compliance issues?",
  "Which board mandates expire in the next 60 days?",
];

export function Ask() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

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

  const sourceLink = (s: Source) =>
    s.kind === "register" && s.ref.startsWith("FGI-")
      ? <Link to={`/entities/${s.ref}`} className="badge info">{s.ref}</Link>
      : <span className="badge neutral">{s.kind}:{s.ref}</span>;

  return (
    <div className="page" style={{ maxWidth: 860 }}>
      <h1>Ask the portfolio</h1>
      <p className="muted">
        Natural-language questions over the register, agent letters and notifications.
        Answers cite their sources.
      </p>

      {messages.length === 0 && (
        <div className="controls" style={{ marginTop: 24 }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <div style={{ margin: "20px 0" }}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="who">{m.role === "user" ? "You" : "Assistant"}</div>
            <div className="bubble">
              {m.content}
              {m.sources && m.sources.length > 0 && (
                <div className="chat-sources">
                  {m.sources.map((s, j) => (
                    <div key={j} className="chat-source">
                      {sourceLink(s)}
                      <span className="muted"> {s.detail}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="chat-msg assistant"><div className="bubble muted">Reading the portfolio…</div></div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="card" style={{ borderColor: "var(--red)", marginBottom: 16 }}>{error}</div>}

      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input type="text" value={input} placeholder="e.g. Which entities in Luxembourg need attention?"
               onChange={(e) => setInput(e.target.value)} disabled={busy} />
        <button className="primary" type="submit" disabled={busy || !input.trim()}>Ask</button>
      </form>
    </div>
  );
}
