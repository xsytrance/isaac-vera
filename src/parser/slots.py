"""Scan a whole Steam ``remote/`` folder and summarize every save slot.

A real install holds several `(rep|rep+)persistentgamedata{N}.dat` files (one per
slot, sometimes one per game version). This reads them all, read-only, so the
Report / companion can talk about a folder rather than a single file. Files that
fail to parse are reported as errors, not silently dropped.
"""
from __future__ import annotations

import glob
import os

from .chronicler import parse_file, SaveParseError

# Matches rep_persistentgamedata1.dat, rep+persistentgamedata2.dat, etc.
SAVE_GLOB = "*persistentgamedata*.dat"


def find_saves(folder: str) -> list[str]:
    return sorted(glob.glob(os.path.join(folder, SAVE_GLOB)))


def scan(folder: str) -> list[dict]:
    """Parse every save in ``folder``. Returns one entry per file."""
    results: list[dict] = []
    for path in find_saves(folder):
        try:
            facts = parse_file(path).to_dict()
            results.append({"file": os.path.basename(path), "ok": True, "facts": facts})
        except (SaveParseError, OSError) as exc:
            results.append({"file": os.path.basename(path), "ok": False,
                            "error": str(exc)})
    return results


def most_progressed(results: list[dict]) -> dict | None:
    """The slot with the most achievements unlocked (the 'main' save), or None."""
    parsed = [r for r in results if r.get("ok")]
    if not parsed:
        return None
    return max(parsed,
               key=lambda r: r["facts"]["completion"].get("achievements_unlocked", 0))
