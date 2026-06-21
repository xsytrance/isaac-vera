# isaac-vera — The Chronicler (Spine 1, v0)

A read-only parser for **The Binding of Isaac** `persistentgamedata{N}.dat`
saves. It turns save bytes into a versioned, ground-truth facts object
(`chronicler.v0`). Facts are sacred: the parser never invents a value — anything
it can't confidently map is `null` and logged in `facts.unknowns`.

This is **Spine 1** of the two-spine plan (see `MULTIVERA_ROADMAP.md`). Spine 2
(the Commentator — a REPENTOGON live run feed, commentary, cinematics) is **not**
built here.

## Scope (v0)
- ✅ Parse Repentance (`ISAACNGSAVE09R`) saves into facts.
- ✅ Completion (achievements / Dead God), lifetime stats (deaths, kills, rocks,
  donation, eden tokens, win streak), collectibles seen, bestiary counts.
- ✅ Strictly read-only. No save editing, ever.
- ❌ No LLM, no commentary, no live feed (Spine 2).

## Usage
```bash
# Print facts as JSON to stdout
python3 -m src.parser.cli path/to/persistentgamedata1.dat
python3 -m src.parser.cli path/to/save.dat --raw   # include raw arrays

# Or serve them read-only (stdlib only, no deps)
python3 -m src.server.app path/to/save.dat --port 8765
curl localhost:8765/facts
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
