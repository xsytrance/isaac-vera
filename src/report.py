"""Render chronicler facts as a human-readable Save Report.

Presentation layer (the "app" surface), kept separate from the parser. Pure
function: facts dict in, markdown-ish text out. Shows only what the parser is
sure of; honest nulls are listed plainly rather than hidden.
"""
from __future__ import annotations

from typing import Any


def _bar(frac: float, width: int = 24) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _num(v: Any) -> str:
    return f"{v:,}" if isinstance(v, int) else "—"


def render(facts: dict) -> str:
    src = facts.get("source", {})
    comp = facts.get("completion", {})
    stats = facts.get("stats", {})
    coll = facts.get("collectibles", {})
    best = facts.get("bestiary", {})
    L: list[str] = []

    name = src.get("name", "<save>")
    game = src.get("game") or "Unknown version"
    verified = "verified" if src.get("format_verified") else "UNVERIFIED format"
    L.append(f"# Isaac Save Report — {name}")
    L.append(f"{game} · {verified} · read-only · {_num(src.get('size_bytes'))} bytes"
             f" · sha {str(src.get('sha256',''))[:8]}")
    L.append("")

    # Completion
    total = comp.get("achievements_total") or 0
    unlocked = comp.get("achievements_unlocked") or 0
    prog = comp.get("dead_god_progress") or 0.0
    dead = "YES \U0001F480" if comp.get("dead_god") else "not yet"
    L.append("## Completion")
    L.append(f"Achievements  {unlocked} / {total}  ({prog*100:.1f}%)   Dead God: {dead}")
    L.append(f"{_bar(prog)}  {prog*100:.1f}%")
    L.append("")

    # Lifetime stats
    L.append("## Lifetime stats")
    L.append(f"Deaths {_num(stats.get('deaths'))} · Mom kills {_num(stats.get('mom_kills'))}"
             f" · Best win streak {_num(stats.get('best_win_streak'))}"
             f" (current {_num(stats.get('win_streak'))})")
    L.append(f"Rocks broken {_num(stats.get('rocks_broken'))}"
             f" · Tinted {_num(stats.get('tinted_rocks_broken'))}"
             f" · Poop destroyed {_num(stats.get('poop_destroyed'))}"
             f" · Shopkeepers {_num(stats.get('shopkeeper_kills'))}")
    L.append(f"Donation machine {_num(stats.get('donation_machine_coins'))}"
             f" · Eden tokens {_num(stats.get('eden_tokens'))}")
    L.append("")

    # Collectibles
    ctot = coll.get("total") or 0
    cseen = coll.get("seen") or 0
    cfrac = cseen / ctot if ctot else 0.0
    L.append("## Collectibles")
    L.append(f"Seen {cseen} / {ctot}  ({cfrac*100:.0f}%)   {_bar(cfrac)}")
    L.append("")

    # Bestiary
    if best.get("parsed"):
        cats = best.get("categories", [])
        sums = " / ".join(str(c.get("value_sum", 0)) for c in cats)
        L.append("## Bestiary")
        L.append(f"{best.get('total_entries', 0)} entries across "
                 f"{best.get('category_count', 0)} categories (value sums: {sums})")
        L.append("")

    # What's left — sample of locked achievements with how-to-unlock hints.
    locked = comp.get("locked") or []
    if locked:
        L.append(f"## What's left — {len(locked)} achievements remaining")
        for a in locked[:12]:
            hint = a.get("unlock") or ""
            hint = (hint[:70] + "…") if len(hint) > 71 else hint
            L.append(f"  • {a['name']}" + (f" — {hint}" if hint else ""))
        if len(locked) > 12:
            L.append(f"  …and {len(locked) - 12} more")
        L.append("")

    # Honest nulls
    unknowns = facts.get("unknowns") or []
    if unknowns:
        L.append("## Not yet mapped (honest nulls)")
        for u in unknowns:
            L.append(f"  • {u['field']}: {u['reason']}")
    return "\n".join(L)
