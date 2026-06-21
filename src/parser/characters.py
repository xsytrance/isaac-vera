"""Non-tainted character roster, derived from unlock achievements.

Each non-tainted character (except Isaac, the default) has exactly one
"Unlocked a new character" achievement, verified by id against the vendored
achievements table (e.g. Magdalene = achievement 1, Bethany = 404). So unlock
status for all 17 non-tainted characters is parser-truth from the achievements
chunk.

The 17 *tainted* characters unlock via a different mechanism (Knife Pieces /
Red Key / "Home"), with no per-character achievement — so they are NOT trackable
from this data and are reported as null ("not tracked"), never guessed.
"""
from __future__ import annotations

# (display name, unlock achievement id) — id None == default/always unlocked.
# IDs verified against Zamiell's achievements table.
NONTAINTED: list[tuple[str, int | None]] = [
    ("Isaac", None),
    ("Magdalene", 1),
    ("Cain", 2),
    ("Judas", 3),
    ("???", 32),
    ("Eve", 42),
    ("Samson", 67),
    ("Azazel", 79),
    ("Lazarus", 80),
    ("Eden", 81),
    ("The Lost", 82),
    ("Lilith", 199),
    ("Keeper", 251),
    ("Apollyon", 340),
    ("The Forgotten", 390),
    ("Bethany", 404),
    ("Jacob & Esau", 405),
]

TRACKED_TOTAL = len(NONTAINTED)  # 17


def roster(unlocked_ids: set[int]) -> dict:
    """Resolve non-tainted character unlock status from unlocked achievement ids."""
    unlocked = [n for n, aid in NONTAINTED if aid is None or aid in unlocked_ids]
    locked = [n for n, aid in NONTAINTED if aid is not None and aid not in unlocked_ids]
    return {
        "tracked_total": TRACKED_TOTAL,
        "unlocked_count": len(unlocked),
        "unlocked": unlocked,
        "locked": locked,
        # Tainted characters cannot be derived from achievements -> honest null.
        "tainted": None,
    }
