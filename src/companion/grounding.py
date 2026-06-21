"""Build the grounded system prompt from chronicler facts.

This is the parser-truth boundary for the companion (the analogue of
fft-psx-vera's prompt_builder hard truth block): the model may ONLY use the
facts in the truth block, must report unknowns as "not tracked", and must never
invent a number. The save is read-only and the parser is the single source of
truth.
"""
from __future__ import annotations

PERSONA = (
    "You are Vera, a companion for The Binding of Isaac. You help the player "
    "understand their save and decide what to do next."
)

RULES = """RULES (non-negotiable):
- The TRUTH BLOCK below is the only source of facts. It comes from a verified,
  read-only save parser (schema {schema}).
- Never invent or estimate a number. If a value is not in the truth block, or is
  marked "not tracked / null", say you don't have it — do not guess.
- When asked "what should I do next", draw only from the WHAT'S LEFT list.
- Be concise and specific. Quote exact counts from the truth block.
- You cannot edit the save; you only read it."""


def _fmt_stat(stats: dict, key: str) -> str:
    v = stats.get(key)
    return "not tracked" if v is None else f"{v:,}"


def build_truth_block(facts: dict, max_locked: int = 60) -> str:
    src = facts.get("source", {})
    comp = facts.get("completion", {})
    stats = facts.get("stats", {})
    coll = facts.get("collectibles", {})
    best = facts.get("bestiary", {})
    L: list[str] = ["=== TRUTH BLOCK (parser-verified, read-only) ==="]

    L.append(f"Save: {src.get('name')} · game {src.get('game')} · "
             f"format_verified={src.get('format_verified')}")
    L.append(
        f"Completion: {comp.get('achievements_unlocked')}/"
        f"{comp.get('achievements_total')} achievements "
        f"({(comp.get('dead_god_progress') or 0)*100:.1f}%), "
        f"Dead God={comp.get('dead_god')}")
    L.append(
        "Stats: deaths " + _fmt_stat(stats, "deaths")
        + ", mom_kills " + _fmt_stat(stats, "mom_kills")
        + ", best_win_streak " + _fmt_stat(stats, "best_win_streak")
        + ", win_streak " + _fmt_stat(stats, "win_streak")
        + ", rocks_broken " + _fmt_stat(stats, "rocks_broken")
        + ", donation_machine " + _fmt_stat(stats, "donation_machine_coins")
        + ", eden_tokens " + _fmt_stat(stats, "eden_tokens"))
    chars = comp.get("characters")
    if chars:
        locked = chars.get("locked") or []
        L.append(
            f"Characters (non-tainted): {chars.get('unlocked_count')}/"
            f"{chars.get('tracked_total')} unlocked"
            + (f"; still locked: {', '.join(locked)}" if locked else "; all unlocked")
            + ". Tainted characters: not tracked.")
    L.append(f"Collectibles seen: {coll.get('seen')}/{coll.get('total')}")
    if best.get("parsed"):
        cats = {c.get("label"): c for c in best.get("categories", [])}
        L.append(f"Bestiary: {best.get('total_entries')} entities tracked.")
        for label, verb in (("kills", "most killed"), ("deaths", "killed you most")):
            c = cats.get(label)
            if c and c.get("top"):
                hi = ", ".join(f"{t['name']} ({t['value']})" for t in c["top"][:3])
                L.append(f"  {verb}: {hi}")

    locked = comp.get("locked") or []
    if locked:
        L.append(f"\nWHAT'S LEFT ({len(locked)} achievements remaining; "
                 f"showing up to {max_locked}):")
        for a in locked[:max_locked]:
            hint = a.get("unlock") or "unlock condition not tracked"
            L.append(f"  - {a['name']}: {hint}")
        if len(locked) > max_locked:
            L.append(f"  ...and {len(locked) - max_locked} more not shown.")

    nulls = [u["field"] for u in (facts.get("unknowns") or [])]
    if nulls:
        L.append("\nNOT TRACKED (do not guess these): " + ", ".join(nulls))
    return "\n".join(L)


def build_system_prompt(facts: dict, max_locked: int = 60) -> str:
    schema = facts.get("schema", "chronicler")
    return (
        PERSONA + "\n\n"
        + RULES.format(schema=schema) + "\n\n"
        + build_truth_block(facts, max_locked=max_locked)
    )
