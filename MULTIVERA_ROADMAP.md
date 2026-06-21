# MULTIVERA ROADMAP

> Dogfood / planning notes (fft-psx-vera "dogfood-output" style). Internal
> direction, not a spec. The COMMIT ALLOW-LIST in the v0 runbook lists this file
> as committable, so it lives in-tree as the shared north star.

## The two spines

isaac-vera grows along two spines that share one sacred rule — **parser-truth**
(the system never invents a fact about a player's save / run).

### Spine 1 — The Chronicler  ✅ v0 (this runbook)
Static save analysis. `persistentgamedata{N}.dat` → `chronicler.v0` facts.
- Cheapest path to "it parses." Read-only. No feelings, no LLM.
- Output is the seam contract every later layer reads (prime-as-brain).
- **Status: shipped (smoke test).** See `BUILDLOG.md`.

### Spine 1.5 — Vera, the companion  ✅ v1.1
Grounded chat over chronicler facts (Save Report + Q&A). Backed by Ollama on
`prime` over Tailscale. Parser-truth: only answers from the truth block, never
invents numbers. This is the "A + B" surface on top of the Chronicler.

### Spine 2 — The Commentator  ⛔ not started
Live run feed via **REPENTOGON**. Real-time events (item pickups, boss kills,
deaths) → commentary / cinematics / Living Text.
- Extends, never replaces, the `chronicler.vN` schema.
- This is where an LLM + persona layer (ported from fft-psx-vera's prompt /
  persona bones) eventually lands.
- Gated behind Claude co-sign of Spine 1.

## Near-term backlog
- ✅ Map COLLECTIBLES ids → item names (v1).
- ✅ Character roster (17 non-tainted from unlock achievements) (v1.1).
- ✅ Bestiary **category labels** + entity→monster names, 99% resolve (v1.2).
- ⬜ Per-character hard-mode **completion marks** — *spiked: the marks grid does
  not appear in the documented chunk format as a clean per-character structure;
  likely not extractable without new reversing. Stays honest null for now.*
- ⬜ **Tainted** character unlocks (no per-character achievement; needs another
  signal).
- ⬜ Disambiguate normal vs **Greed** donation machine counters.
- ⬜ Add more header versions (Afterbirth/Afterbirth+) once byte-verified.

## Guardrails carried from fft-psx-vera
- Unknown = `null`, logged, never guessed.
- Allow-list commits only; gitignore all `*.dat` / art / audio up front.
- Append a BUILDLOG entry every run.
