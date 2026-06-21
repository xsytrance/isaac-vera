import { useEffect, useState } from "react";
import type { Facts } from "./types";
import { getFacts } from "./api";
import {
  CompletionCard,
  CharacterRoster,
  StatsGrid,
  BestiaryCard,
  WhatsNext,
} from "./components/Cards";
import { VeraChat } from "./components/VeraChat";

export function App() {
  const [facts, setFacts] = useState<Facts | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFacts().then(setFacts).catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <main>
        <h1>isaac-vera</h1>
        <p className="err">
          Could not load <code>/facts</code> ({error}). Is the server running?
          <br />
          <code>python3 -m src.server.app save.dat --bind 0.0.0.0</code>
        </p>
      </main>
    );
  if (!facts) return <main className="muted">loading…</main>;

  return (
    <main>
      <h1>isaac-vera · {facts.source.game ?? "Isaac"} save</h1>
      <div className="sub">
        {facts.source.name} · {facts.source.size_bytes.toLocaleString()} bytes ·{" "}
        <span className="seal">read-only ✓ parser-truth</span>
      </div>
      <div className="grid">
        <CompletionCard f={facts} />
        <CharacterRoster f={facts} />
        <StatsGrid f={facts} />
        <BestiaryCard f={facts} />
        <WhatsNext f={facts} />
      </div>
      <VeraChat />
    </main>
  );
}
