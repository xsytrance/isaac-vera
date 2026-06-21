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

### Spine 2 — The Commentator  ⛔ not started
Live run feed via **REPENTOGON**. Real-time events (item pickups, boss kills,
deaths) → commentary / cinematics / Living Text.
- Extends, never replaces, the `chronicler.vN` schema.
- This is where an LLM + persona layer (ported from fft-psx-vera's prompt /
  persona bones) eventually lands.
- Gated behind Claude co-sign of Spine 1.

## Near-term backlog (post co-sign)
- Map achievement IDs → per-character hard-mode **completion marks** (currently null).
- Map COLLECTIBLES ids → item names; expose per-item touched/seen.
- Confirm bestiary **category labels** (kills / encounters / hits / deaths) and
  map entity keys → monster names.
- Disambiguate normal vs **Greed** donation machine counters.
- Add more header versions (Afterbirth/Afterbirth+) once byte-verified.
- Schema bump `chronicler.v0 → v1` when the above land.

## Guardrails carried from fft-psx-vera
- Unknown = `null`, logged, never guessed.
- Allow-list commits only; gitignore all `*.dat` / art / audio up front.
- Append a BUILDLOG entry every run.
