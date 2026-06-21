"""'What's next' intelligence — group the locked achievements into actionable
buckets, ordered by impact.

Pure derivation over the real locked list (each item keeps its true in-game
unlock hint); this categorizes, it never invents goals. Classification is by
keyword in the unlock description plus the known character-unlock ids.
"""
from __future__ import annotations

from .characters import NONTAINTED

CHARACTER_ACHIEVEMENT_IDS = {aid for _, aid in NONTAINTED if aid is not None}

# Bucket order = suggested priority (high-impact / discrete goals first).
GROUP_ORDER = [
    "characters",       # unlock a whole new character — biggest impact
    "challenges",       # discrete, self-contained runs
    "greed_mode",       # Greed/Greedier-specific
    "boss_completion",  # "defeat X as Y" — the completion-mark grind
    "donation",         # feed the machines
    "other",
]

GROUP_LABEL = {
    "characters": "Unlock characters",
    "challenges": "Beat challenges",
    "greed_mode": "Greed mode",
    "boss_completion": "Boss completions (defeat … as …)",
    "donation": "Donation machines",
    "other": "Other",
}


def _bucket(ach: dict) -> str:
    if ach.get("id") in CHARACTER_ACHIEVEMENT_IDS:
        return "characters"
    u = (ach.get("unlock") or "").lower()
    if "challenge" in u:
        return "challenges"
    if "greed" in u:
        return "greed_mode"
    if "donat" in u:
        return "donation"
    if "defeat" in u and " as " in u:
        return "boss_completion"
    return "other"


def whats_next(locked: list[dict], max_examples: int = 6) -> dict:
    """Group `locked` (list of {id, name, unlock}) into ordered buckets."""
    buckets: dict[str, list] = {g: [] for g in GROUP_ORDER}
    for ach in locked:
        buckets[_bucket(ach)].append(ach)

    groups = []
    for g in GROUP_ORDER:
        items = buckets[g]
        if not items:
            continue
        groups.append({
            "group": g,
            "label": GROUP_LABEL[g],
            "count": len(items),
            "examples": [
                {"name": x["name"], "unlock": x.get("unlock")}
                for x in items[:max_examples]
            ],
        })

    # Headline: the highest-priority non-empty bucket, with its first concrete pick.
    headline = "All tracked achievements unlocked — Dead God territory."
    if groups:
        top = groups[0]
        pick = top["examples"][0]
        hint = f" — e.g. {pick['name']}" if pick else ""
        headline = f"{top['count']} to go in “{top['label']}”{hint}."
    return {"headline": headline, "groups": groups}
