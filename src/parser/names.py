"""ID -> name resolution for chronicler facts.

Maps the save's array indices (which equal in-game IDs — verified against a real
save: collectible 1 = "The Sad Onion", achievement 1 = "Magdalene") to human
names. Tables are vendored from Zamiell/isaac-save-viewer's public game metadata
(`src/data/achievements.json`, `items.json`).

Parser-truth: an ID with no table entry resolves to ``Unknown_<id>`` (the
fft-psx-vera convention for unrecognized items) — surfaced honestly, never hidden
or guessed.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"
DATA_SOURCE = "Zamiell/isaac-save-viewer (public game metadata)"


@lru_cache(maxsize=1)
def _achievements() -> dict:
    return json.loads((_DATA / "achievements.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _collectibles() -> dict:
    return json.loads((_DATA / "collectibles.json").read_text(encoding="utf-8"))


def achievement_name(achievement_id: int) -> str:
    entry = _achievements().get(str(achievement_id))
    if not entry or not entry.get("name"):
        return f"Unknown_{achievement_id}"
    return entry["name"]


def achievement_unlock(achievement_id: int) -> str | None:
    entry = _achievements().get(str(achievement_id))
    return entry.get("unlock") if entry else None


def collectible_name(item_id: int) -> str:
    name = _collectibles().get(str(item_id))
    return name if name else f"Unknown_{item_id}"


def known_achievement(achievement_id: int) -> bool:
    return str(achievement_id) in _achievements()


def known_collectible(item_id: int) -> bool:
    return str(item_id) in _collectibles()
