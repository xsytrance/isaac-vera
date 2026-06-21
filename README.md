# isaac-vera — The Chronicler (Spine 1, v0)

A read-only parser for **The Binding of Isaac** `persistentgamedata{N}.dat`
saves. It turns save bytes into a versioned, ground-truth facts object
(`chronicler.v0`). Facts are sacred: the parser never invents a value — anything
it can't confidently map is `null` and logged in `facts.unknowns`.

This is **Spine 1** of the two-spine plan (see `MULTIVERA_ROADMAP.md`). Spine 2
(the Commentator — a REPENTOGON live run feed, commentary, cinematics) is **not**
built here.

## Scope (chronicler.v1.2)
- ✅ Parse Repentance / Repentance+ (`ISAACNGSAVE09R`) saves into facts.
- ✅ Completion (achievements / Dead God), lifetime stats, collectibles, bestiary.
- ✅ **ID → name resolution** for achievements, collectibles, and **bestiary
  monsters** (with boss flags); `locked` achievements carry unlock hints.
  Unknown id → `Unknown_<id>`.
- ✅ **Character roster** (17 non-tainted, from unlock achievements).
- ✅ **Bestiary** named per category (deaths / kills / hits / encounters) —
  "most killed / encountered / killed you most".
- ✅ **Save Report** (`--report`) and **Vera** (grounded companion).
- ✅ Strictly read-only. No save editing, ever.
- ⬜ Honest nulls: per-character completion marks, tainted unlocks, Greed-donation
  split (see roadmap).

## Usage
```bash
# Human-readable Save Report (completion, stats, what's left + how-to)
python3 -m src.parser.cli path/to/persistentgamedata1.dat --report

# Print chronicler.v1 facts as JSON to stdout
python3 -m src.parser.cli path/to/persistentgamedata1.dat
python3 -m src.parser.cli path/to/save.dat --raw   # include raw arrays

# Or run the prime-as-brain service (stdlib only, no deps):
#   GET /facts · GET /report · POST /ask · GET /healthz
python3 -m src.server.app path/to/save.dat --port 8765
curl localhost:8765/facts
curl localhost:8765/report
curl -X POST localhost:8765/ask -d '{"question":"how close am I to Dead God?"}'
```

### Vera — grounded companion (Ollama)
Ask questions about your save; answers are grounded strictly in parsed facts
(never invents numbers). Backed by Ollama on **prime** over Tailscale
(`http://100.110.224.126:11434` by default).
```bash
python3 -m src.companion.cli save.dat "what should I unlock next?"
python3 -m src.companion.cli save.dat            # interactive
python3 -m src.companion.cli save.dat --show-prompt   # inspect grounding, no model call
OLLAMA_HOST=http://100.110.224.126:11434 OLLAMA_MODEL=llama3.1 \
  python3 -m src.companion.cli save.dat "how close am I to Dead God?"
```

```python
from src.parser import parse_file
facts = parse_file("persistentgamedata1.dat").to_dict()
```

## Tests
```bash
pip install pytest
pytest -q
```
Tests use a **synthetic** save built in-memory, so CI needs no real `.dat`. If a
real `fixtures/sample.dat` is present (gitignored), extra ground-truth
spot-checks run automatically.

## Format provenance
The byte map is sourced, not guessed (see `src/parser/format.py` for citations):
- Chunk model + chunk-type enum — [Zamiell/isaac-save-viewer](https://github.com/Zamiell/isaac-save-viewer) (reversed by "Blade" via Kaitai Struct).
- Header, element widths, counter offsets — [Demorck/Isaac-save-manager](https://github.com/Demorck/Isaac-save-manager).
- Container framing + bestiary layout — validated byte-for-byte against the public Dead God save in [Zamiell/isaac-save-installer](https://github.com/Zamiell/isaac-save-installer).

## Standing rules
1. **Parser-truth** — unknown is `null`, never a guess.
2. **Read-only** — we never write to a user's `.dat`.
3. **Allow-list commits** — save binaries and art are gitignored and never tracked.
