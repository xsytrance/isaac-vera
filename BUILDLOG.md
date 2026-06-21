# BUILDLOG

## multi-slot + SPA switcher + mobile — 2026-06-21

- **Server** now takes a save *or* a whole `remote/` folder. New `GET /slots`
  lists every slot (game, achievements, Dead God, which is default = most
  progressed). `/facts`, `/report` accept `?slot=FILE`; `/ask` accepts `slot` in
  the body — each slot gets its own grounded companion (sharing one Ollama
  client). Single-file mode unchanged.
- **SPA**: a slot switcher (tabs) when >1 slot; selecting one re-fetches facts and
  routes chat to that slot. Plus a mobile breakpoint (single-column grid,
  full-width tabs/messages). Rebuilds clean.
- Tests: 38 passed, 1 skipped (added /slots, ?slot= selection, slot-scoped ask).
- Verified live on the real 3-slot export (slot 1 default at 111/642).

## real frontend — React/Vite SPA — 2026-06-21

`frontend/` is a proper Vite + React + TypeScript app (strict mode; `npm run
build` → 148 KB, verified compiling here). Components: completion, character
roster, stats, named bestiary, prioritized "what's next" (from `facts.next`),
and an **Ask Vera** chat (POST `/ask`, honest on failure). Dev uses a Vite proxy
to the prime-as-brain server; for prod, the Python server now **serves the built
`frontend/dist`** at `/` (with correct content-types) and falls back to the
zero-build `dashboard.html` when no build is present. node_modules / dist /
*.tsbuildinfo are gitignored — source only. Server tests cover SPA-serving;
35 passed, 1 skipped.

## what's-next intelligence — 2026-06-21

`src/parser/priorities.py` groups the locked achievements into impact-ordered
buckets (characters → challenges → greed → boss-completions → donation → other),
each with a count + concrete examples carrying their real unlock hints, plus a
headline. Pure derivation over the real locked list — categorizes, never invents.
Exposed at `facts.next`, shown in the Report and Vera's truth block. On the real
save: 6 characters, 49 challenges, 52 greed, 270 boss-completions, 6 donation,
147 other. Tests: 34 passed, 1 skipped.

## frontend + multi-slot — 2026-06-21

- **Dashboard frontend** (`src/server/dashboard.html`, served at `GET /`): a
  self-contained, zero-build, no-deps page (vanilla JS + inline CSS, dark theme)
  that fetches `/facts` and renders completion, character chips, lifetime stats,
  named bestiary (most killed / encountered / killed-you-most), and a scrollable
  "what's left". Also has an **Ask Vera** chat box (POST `/ask`) — so the one
  page is the full A+B surface (dashboard + grounded companion). Server serves
  `text/html` and takes `--bind` (use `0.0.0.0` to reach it over the tailnet).
  Chat shows honest errors (e.g. prime unreachable) — never a fake answer.
- **Multi-slot folder support** (`src/parser/slots.py`): point the CLI at a
  Steam `remote/` folder and it parses every `*persistentgamedata*.dat`,
  reporting a per-slot table (achv / Dead God / deaths / items / chars) and the
  most-progressed slot. Bad files are reported, not crashed on. On the real
  export: slot 1 active (111/642), slots 2 & 3 fresh.
- Tests: 33 passed, 1 skipped (added dashboard-route + folder-scan tests).

## v1.2 — bestiary names + category labels — 2026-06-21

Resolved two long-standing nulls at once, both sourced and validated:
- **Category labels** = `deaths, kills, hits, encounters` (file order from
  Demorck `SaveManager.ts` `setBestiary`; corroborated by magnitudes — kills &
  encounters dominate, deaths smallest).
- **Monster names**: entity key decode `id = ((id2<<8)|id1) >> 4`,
  `variant = byte+1` (Demorck), i.e. `id = (key>>20)&0xFFF`. Verified
  `0x00A00000 → id 10 (Frowning Gaper)`; **99% of real-save entries resolve**
  (735/739). Vendored 498 names + 134 boss flags (`data/entities.json`) from
  Demorck `IEntity.ts`. Unknown → `Unknown_<id>.<variant>`.
- Facts now expose, per category: `label`, `entries`, `value_sum`, and a named
  `top` list (id/variant/name/boss/value). Report + Vera show "most killed /
  encountered / killed you most". On the real save: most killed Spider (1,417),
  Attack Fly (1,363); killed you most Spider, Gusher, Maw.
- Schema → `chronicler.v1.2`; tests reference the constant now (no churn on
  future bumps). 31 passed, 1 skipped.

## v1.1.x — character roster — 2026-06-21

Deepened the Chronicler (schema bump `chronicler.v1` → `chronicler.v1.1`):
- `completion.characters` — the **17 non-tainted characters**, each resolved
  from its unlock achievement (verified by id: Magdalene=1 … Bethany=404,
  Jacob & Esau=405; Isaac=default). Surfaced in the Report and Vera's truth block.
- The **17 tainted** characters unlock via Knife Pieces / Red Key with no
  per-character achievement, so they are **not derivable** from this data →
  reported as `null` ("not tracked"), never guessed.
- On the real save: 11/17 non-tainted unlocked (locked: The Lost, Keeper,
  Apollyon, The Forgotten, Bethany, Jacob & Esau). Tests: 31 passed, 1 skipped.
- Bestiary monster names and per-character completion marks remain honest nulls
  (no clean public source yet — documented in the roadmap backlog).

## v1.2 — prime-as-brain service — 2026-06-21

Unified the pieces into one read-only service (`src/server/app.py`) so a single
process on a tailnet box exposes everything:
- `GET /facts` (chronicler.v1 JSON), `GET /report` (text), `GET /healthz`,
  and `POST /ask {question, history?}` → grounded answer via Vera/Ollama.
- Routing is a pure `route()` function → unit-tested without a socket or model.
- A model failure returns **503**, never a fabricated answer (parser-truth).
- Tests: 31 passed (8 server: routes, 400/404/503 paths, model mocked). Live
  smoke against the real save: `/facts`, `/report`, `/healthz` OK; `/ask` attempts
  prime (unreachable from CI) honestly.

---

## v1.1 — Vera, the grounded companion — 2026-06-21

Capstone of the "A + B on top of the Chronicler" plan: a chat companion that
answers questions about a save, grounded strictly in chronicler facts.

- **Model backend: Ollama on `prime` over Tailscale** (`http://100.110.224.126:11434`).
  `src/companion/ollama_client.py` — stdlib-only client; host/model env-configurable
  (`OLLAMA_HOST` / `OLLAMA_MODEL`); auto-detects the installed model when unset.
  prime is a 100.x Tailscale address, unreachable from the CI/cloud container, so
  the model is mocked in tests (project rule) and runs live from any tailnet box.
- **Grounding** (`src/companion/grounding.py`): a hard TRUTH BLOCK built from
  facts — completion, stats, collectibles, bestiary, and the WHAT'S LEFT list
  (locked achievements + how-to-unlock hints). Non-negotiable rules: only use the
  truth block, report nulls as "not tracked", never invent a number. Same
  parser-truth discipline as fft-psx-vera's prompt hard-truth block.
- **CLI** (`src/companion/cli.py`): one-shot (`save.dat "what next?"`),
  interactive REPL, `--show-prompt` (inspect grounding, no model call),
  `--list-models`.
- Tests: 23 passed (8 companion: grounding content, message threading, model
  resolution; model faked — no network).
- Polish: vendored name tables HTML-unescaped (clean apostrophes/ampersands).

---

## v1 — Rich facts + Save Report — 2026-06-21

First real app surface, built on a real player save (Egi's Steam `250900` export:
`rep+persistentgamedata1.dat`, slot 1). Parser-truth held throughout.

### Real-save validation (the true STEP D)
All three save slots parse clean (11/11 chunks, walk EOF-exact) across the
638-achievement (Repentance, `rep_`) and 642-achievement (Repentance+, `rep+`)
variants — the self-describing chunk walk adapted with zero hardcoded offsets.
Slot 1 (the active save): 111/642 achievements, 8 deaths, 11 Mom kills, best
streak 2, 388/733 items seen, 739 bestiary entries. Realistic, not maxed —
proves the parser on genuine mid-progression data, not just the Dead God file.

### chronicler.v0 → v1
- **ID → name resolution** (`src/parser/names.py` + vendored
  `src/parser/data/{achievements,collectibles}.json`, trimmed from
  Zamiell/isaac-save-viewer public metadata). Verified `index == in-game ID`
  against the real save (collectible 1 = "The Sad Onion", achievement 1 =
  "Magdalene"). Unknown id → `Unknown_<id>` (never hidden/guessed).
- `completion.unlocked` / `completion.locked` now carry real names; `locked`
  includes the in-game unlock hint ("what's left + how to get it").
- `collectibles.seen_items` lists seen items by name.
- **Save Report** (`src/report.py`, `cli --report`): readable progress report
  — completion bar, lifetime stats, collectibles, bestiary, a sample of what's
  left with how-to hints, and the honest-nulls list.
- Tests: 15 passed (added name-resolution, unknown-id honesty, report render).

### Still null (logged, not guessed)
Per-character completion marks; normal-vs-Greed donation split; bestiary
category labels + monster names. Next foundation step before the companion.

---

## v0 — The Chronicler (Parser Smoke Test) — 2026-06-21

Stand up isaac-vera as its own repo and ship one thing: a verified `.dat` parser
that emits ground-truth facts. Facts are sacred; unknown = `null`, never guessed.

### STEP A — Recon of fft-psx-vera (patterns ported, not FF logic)
- **Parser-truth module boundary**: fft-psx-vera splits raw decode
  (`save_parser.py`, bytes → dataclasses) from the normalized, versioned contract
  (`save_truth.py`, `SCHEMA_VERSION`, high-risk fields, "never guess"). Ported as
  `src/parser/format.py` (sourced byte map) + `src/parser/chronicler.py`
  (`chronicler.v0` facts, `note_unknown()` for every null).
- **Client/server seam ("prime-as-brain")**: fft-psx-vera's FastAPI backend owns
  truth; clients are thin. Ported as a stdlib-only read-only facts server
  (`src/server/app.py`) — seam only, no deps, no LLM.
- **BUILDLOG + roadmap convention**: fft-psx-vera keeps planning docs (GRAND_PLAN,
  LESSONS_LEARNED, etc.) and a gitignored `dogfood-output/` scratch area. Ported
  as this `BUILDLOG.md` + `MULTIVERA_ROADMAP.md`.
- **Gitignore hardening**: fft-psx-vera ignores save uploads, art, audio, mp3,
  webp. Ported and tightened to ignore `*.dat`, `fixtures/*.dat`, `art/`, `audio/`
  and image/audio binaries **before the first commit**.
- **Reusable vs FFT-specific**: ported the *patterns* (versioned schema,
  null-for-unknown, read-only, sourced offsets, seam). Left behind all FF content
  (job tables, zodiac, personas, lore/RAG).

### STEP B — Scaffold
```
src/parser/{format,chronicler,cli}.py   src/server/app.py
tests/test_parser.py   README.md   BUILDLOG.md   MULTIVERA_ROADMAP.md   .gitignore
```
Python (zero-install, stdlib only) — cheapest path and matches the ported bones.
`.gitignore` hardened first; `MULTIVERA_ROADMAP.md` records the two-spine plan.

### STEP C — The Chronicler parser
Sourced byte map (no from-scratch reversing):
- Chunk model + `ChunkType` enum — Zamiell/isaac-save-viewer (Kaitai, by "Blade").
- Header, element widths (`ENTRY_LENS`), COUNTERS offsets — Demorck/Isaac-save-manager.
- Container framing + bestiary layout — validated byte-for-byte against the public
  Dead God save (Zamiell/isaac-save-installer).

Format (Repentance `ISAACNGSAVE09R`, verified): 16-byte header, u32 stamp @0x10,
then chunks @0x14 = `type:u32, field2:u32, count:u32, count*stride bytes`
(stride per type: achv 1, counters 4, level 4, collect 1, miniboss 1, boss 1,
chall 1, cutscene 4, settings 4, specialseed 1). Bestiary (type 11) = 8-byte
sub-header + `(entity:u32,value:u32)` pairs in 4 categories, then an 8-byte file
footer/checksum. The walk lands **exactly on EOF** with chunk types 1..11 in order.

### STEP D — Smoke test (the gate)
Fixture: the public **Dead God** save from Zamiell/isaac-save-installer
(`saves/Repentance/persistentgamedata.dat`, 17,924 bytes,
sha256 `2f6610…c0a`). Kept at `fixtures/sample.dat` (gitignored — never committed).
Parsed to stdout via `python3 -m src.parser.cli fixtures/sample.dat`.

**Human-verifiable spot-checks** (parsed value):

| Fact | Parsed | Note |
|---|---|---|
| Header magic | `ISAACNGSAVE09R` | → Repentance ✓ |
| Achievements unlocked | **637 / 638** | only the null slot (idx 0) locked → **Dead God: true** ✓ |
| Total deaths | **1159** | plausible for a maxed file ✓ |
| Mom kills | **1165** | ✓ |
| Best win streak | **112** | ✓ |
| Donation machine (coins) | **999** | maxed ✓ |
| Rocks broken | 314109 · Collectibles seen 722/733 · Bestiary 1749 entries (4 cats) | container exact to EOF ✓ |

- **Zero fabricated fields** — every null is in `facts.unknowns` with a reason.
- **Unknowns are null** — `completion_marks`, `greed_donation_machine`,
  `collectibles.by_id`, `bestiary.category_labels`.
- **No write occurred** — opened `rb` only; sha256 unchanged after parse; a unit
  test asserts the input buffer is not mutated.
- Note: this is the installer's *fully-unlocked* file, so some values are
  artificial maxes (e.g. eden_tokens 10,000,000). That verifies the parser reads
  correctly; a natural playthrough save (Egi's) would add organic spot-checks.

### Coverage
- **Container**: 11/11 chunk types parsed; walk EOF-exact. 100% structural.
- **Named facts (runbook targets)**: completion ✓, deaths ✓, mom kills ✓, rocks ✓
  (+tinted, poop), shopkeeper ✓, donation (coins) ✓, eden tokens ✓, win/best
  streak ✓, collectibles seen ✓, bestiary counts ✓, Dead God ✓.
- **Still null/unknown (logged, not guessed)**: per-character completion marks;
  normal-vs-Greed donation split; per-item collectible id→name; bestiary category
  labels + entity→monster names; non-Repentance header versions (parse
  structurally but field mappings flagged unverified).

### Tests
`pytest -q` → **11 passed** (10 synthetic round-trip/invariant + 1 real-save
spot-check that auto-skips when the gitignored fixture is absent).

### Open decision for co-sign
`MULTIVERA_ROADMAP.md` was described as "gitignored dogfood-output style" in the
runbook but is also on the COMMIT ALLOW-LIST. Treated the allow-list as
authoritative and committed it. Say the word to gitignore it instead.

**CO-SIGN GATE reached. Stopping before Spine 2 (REPENTOGON live feed).**
