# BUILDLOG

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
