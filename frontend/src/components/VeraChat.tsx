import { useState } from "react";
import { ask } from "../api";

interface Msg {
  role: "you" | "vera" | "error";
  text: string;
}

export function VeraChat({ slot }: { slot?: string }) {
  const [log, setLog] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = q.trim();
    if (!text || busy) return;
    setQ("");
    setLog((l) => [...l, { role: "you", text }]);
    setBusy(true);
    const r = await ask(text, slot);
    setLog((l) => [
      ...l,
      r.ok
        ? { role: "vera", text: r.answer + (r.model ? `\n— ${r.model}` : "") }
        : { role: "error", text: "⚠ " + r.error },
    ]);
    setBusy(false);
  }

  return (
    <section className="panel chat">
      <h2>Ask Vera · grounded in this save</h2>
      <div className="chatlog">
        {log.length === 0 && (
          <div className="muted small">
            e.g. “what should I unlock next?” · “how close am I to Dead God?”
          </div>
        )}
        {log.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>
      <div className="chatbar">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="ask about your save…"
        />
        <button onClick={send} disabled={busy}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </section>
  );
}
