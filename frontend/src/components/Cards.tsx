import type { Facts } from "../types";

const num = (n: number | null | undefined) =>
  typeof n === "number" ? n.toLocaleString() : "—";

export function Panel(props: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <h2>{props.title}</h2>
      {props.children}
    </section>
  );
}

export function CompletionCard({ f }: { f: Facts }) {
  const c = f.completion;
  const pct = (c.dead_god_progress || 0) * 100;
  return (
    <Panel title="Completion">
      <div className="big">
        {c.achievements_unlocked}/{c.achievements_total}
      </div>
      <div className="muted">
        achievements · Dead God: <b>{c.dead_god ? "YES 💀" : "not yet"}</b>
      </div>
      <div className="bar">
        <div style={{ width: `${pct}%` }} />
      </div>
      <div className="muted">{pct.toFixed(1)}%</div>
    </Panel>
  );
}

export function CharacterRoster({ f }: { f: Facts }) {
  const ch = f.completion.characters;
  if (!ch) return null;
  return (
    <Panel title="Characters">
      <div className="muted">
        <b>
          {ch.unlocked_count}/{ch.tracked_total}
        </b>{" "}
        non-tainted unlocked
      </div>
      <div className="chips">
        {ch.unlocked.map((n) => (
          <span key={n} className="chip on">
            {n}
          </span>
        ))}
        {ch.locked.map((n) => (
          <span key={n} className="chip off">
            {n}
          </span>
        ))}
      </div>
      <div className="muted small">tainted: not tracked from save data</div>
    </Panel>
  );
}

export function StatsGrid({ f }: { f: Facts }) {
  const s = f.stats;
  const rows: [string, number | null][] = [
    ["Deaths", s.deaths],
    ["Mom kills", s.mom_kills],
    ["Best win streak", s.best_win_streak],
    ["Rocks broken", s.rocks_broken],
    ["Donation machine", s.donation_machine_coins],
    ["Eden tokens", s.eden_tokens],
    ["Items seen", f.collectibles.seen],
  ];
  return (
    <Panel title="Lifetime stats">
      {rows.map(([k, v]) => (
        <div className="stat" key={k}>
          <span>{k}</span>
          <b>{num(v)}</b>
        </div>
      ))}
    </Panel>
  );
}

export function BestiaryCard({ f }: { f: Facts }) {
  const b = f.bestiary;
  if (!b?.parsed) return null;
  const cat = (label: string) => b.categories.find((c) => c.label === label);
  const block = (label: string, verb: string) => {
    const c = cat(label);
    if (!c) return null;
    return (
      <div key={label}>
        <div className="muted small">{verb}</div>
        {c.top.slice(0, 5).map((t) => (
          <div className="row" key={`${t.id}:${t.variant}`}>
            <span className={t.boss ? "boss" : ""}>{t.name}</span>
            <span className="muted">{num(t.value)}</span>
          </div>
        ))}
      </div>
    );
  };
  return (
    <Panel title={`Bestiary · ${num(b.total_entries)} tracked`}>
      {block("kills", "Most killed")}
      {block("encounters", "Most encountered")}
      {block("deaths", "Killed you most")}
    </Panel>
  );
}

export function Collectibles({ f }: { f: Facts }) {
  const c = f.collectibles;
  const items = c.items ?? [];
  if (!items.length) return null;
  return (
    <Panel title={`Collectibles · ${c.seen}/${c.total} seen`}>
      <div className="muted small">
        green = seen · dim = still to find ({items.filter((i) => !i.seen).length})
      </div>
      <div className="itemgrid">
        {items.map((i) => (
          <span
            key={i.id}
            className={`cell ${i.seen ? "seen" : ""}`}
            title={`${i.name}${i.seen ? "" : " — not seen"}`}
          />
        ))}
      </div>
    </Panel>
  );
}

export function WhatsNext({ f }: { f: Facts }) {
  const n = f.next;
  if (!n?.groups?.length) return null;
  const top = n.groups[0];
  return (
    <Panel title={`What's next · ${f.completion.locked.length} left`}>
      <div className="headline">{n.headline}</div>
      <div className="chips">
        {n.groups.map((g) => (
          <span className="chip" key={g.group}>
            {g.label}: <b>{g.count}</b>
          </span>
        ))}
      </div>
      <div className="muted small" style={{ marginTop: 10 }}>
        Start here — {top.label}
      </div>
      <ul className="next">
        {top.examples.map((e, i) => (
          <li key={i}>
            <div className="n">{e.name}</div>
            {e.unlock && <div className="h">{e.unlock}</div>}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
