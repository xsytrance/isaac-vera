import { useEffect, useState } from "react";
import type { Facts, Slot } from "./types";
import { getFacts, getSlots } from "./api";
import {
  CompletionCard,
  CharacterRoster,
  StatsGrid,
  BestiaryCard,
  WhatsNext,
  Collectibles,
} from "./components/Cards";
import { VeraChat } from "./components/VeraChat";

export function App() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [facts, setFacts] = useState<Facts | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load the slot list once; pick the default (most-progressed) slot.
  useEffect(() => {
    getSlots()
      .then((s) => {
        setSlots(s);
        const def = s.find((x) => x.default) ?? s[0];
        setSelected(def ? def.file : null);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // (Re)load facts whenever the selected slot changes.
  useEffect(() => {
    if (selected === null) return;
    setFacts(null);
    getFacts(selected).then(setFacts).catch((e) => setError(String(e)));
  }, [selected]);

  if (error)
    return (
      <main>
        <h1>isaac-vera</h1>
        <p className="err">
          Could not reach the server ({error}). Is it running?
          <br />
          <code>python3 -m src.server.app save.dat --bind 0.0.0.0</code>
        </p>
      </main>
    );

  return (
    <main>
      <h1>isaac-vera{facts ? ` · ${facts.source.game ?? "Isaac"} save` : ""}</h1>
      <div className="sub">
        {facts ? (
          <>
            {facts.source.name} · {facts.source.size_bytes.toLocaleString()} bytes ·{" "}
          </>
        ) : null}
        <span className="seal">read-only ✓ parser-truth</span>
      </div>

      {slots.length > 1 && (
        <div className="slots">
          {slots.map((s) => (
            <button
              key={s.file}
              className={`slottab ${s.file === selected ? "active" : ""}`}
              onClick={() => setSelected(s.file)}
              title={`${s.achievements_unlocked}/${s.achievements_total} achievements`}
            >
              {s.file}
              <span className="muted small">
                {" "}
                {s.achievements_unlocked}/{s.achievements_total}
                {s.dead_god ? " 💀" : ""}
              </span>
            </button>
          ))}
        </div>
      )}

      {!facts ? (
        <div className="muted">loading…</div>
      ) : (
        <>
          <div className="grid">
            <CompletionCard f={facts} />
            <CharacterRoster f={facts} />
            <StatsGrid f={facts} />
            <BestiaryCard f={facts} />
            <WhatsNext f={facts} />
          </div>
          <Collectibles f={facts} />
          <VeraChat slot={selected ?? undefined} />
        </>
      )}
    </main>
  );
}
