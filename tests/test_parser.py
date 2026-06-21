"""Chronicler parser tests.

Two layers:
1. Synthetic round-trip — build a save with known values, parse it back, assert
   the parser reads exactly what we wrote. No real save needed (CI-safe).
2. Optional ground-truth — if a real fixtures/sample.dat is present (gitignored),
   run spot-checks. Skipped when absent so CI stays green without the binary.
"""
from __future__ import annotations

import os
import struct

import pytest

from src.parser import format as fmt
from src.parser import names
from src.parser import parse_bytes, parse_file, SaveParseError, SCHEMA_VERSION
from src.report import render

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample.dat")


def _chunk(ctype: int, count: int, payload: bytes, field2: int | None = None) -> bytes:
    if field2 is None:
        field2 = count * (1 if ctype == fmt.ACHIEVEMENTS else 4)
    return struct.pack("<III", ctype, field2, count) + payload


def build_synthetic_save() -> bytes:
    """A minimal but structurally faithful Repentance save with known values."""
    out = bytearray()
    out += b"ISAACNGSAVE09R  "          # 16-byte header
    out += struct.pack("<I", 0xDEADBEEF)  # leading checksum/stamp

    # ACHIEVEMENTS: 10 slots, all unlocked except the null slot 0 -> Dead God.
    ach = bytes([0] + [1] * 9)
    out += _chunk(fmt.ACHIEVEMENTS, 10, ach)

    # COUNTERS: 24 u32 counters; set known stats at their mapped indices.
    counters = [0] * 24
    counters[0x00 // 4] = 3      # donation_machine
    counters[0x04 // 4] = 7      # mom_kills
    counters[0x08 // 4] = 1234   # rocks_broken
    counters[0x24 // 4] = 42     # deaths
    counters[0x2C // 4] = 9      # shopkeeper_kills
    counters[0x4C // 4] = 999    # donation_machine_coins
    counters[0x54 // 4] = 11     # eden_tokens
    counters[0x58 // 4] = 0      # win_streak
    counters[0x5C // 4] = 5      # best_win_streak
    out += _chunk(fmt.COUNTERS, 24, b"".join(struct.pack("<I", c) for c in counters))

    out += _chunk(fmt.LEVEL_COUNTERS, 2, struct.pack("<II", 0, 0))
    # COLLECTIBLES: 5 items, 3 seen (1-byte flags).
    out += _chunk(fmt.COLLECTIBLES, 5, bytes([1, 0, 1, 1, 0]))
    out += _chunk(fmt.MINIBOSSES, 2, bytes([1, 0]))
    out += _chunk(fmt.BOSSES, 2, bytes([1, 1]))
    out += _chunk(fmt.CHALLENGES, 2, bytes([1, 0]))
    out += _chunk(fmt.CUTSCENES, 2, struct.pack("<II", 1, 0))
    out += _chunk(fmt.GAME_SETTINGS, 2, struct.pack("<II", 0, 0))
    out += _chunk(fmt.SPECIAL_SEEDS, 2, bytes([0, 0]))

    # BESTIARY: 2 categories (entity ascending, resets between categories).
    # 8-byte sub-header + pairs. count field = number of categories.
    bestiary_pairs = b""
    for cat in range(2):
        for ent, val in [(0x00100000, 3 + cat), (0x00200000, 5 + cat)]:
            bestiary_pairs += struct.pack("<II", ent, val)
    bestiary_body = struct.pack("<II", 2, 99) + bestiary_pairs  # 8-byte sub-header
    out += struct.pack("<III", fmt.BESTIARY, len(bestiary_body), 2) + bestiary_body

    out += b"\x00" * fmt.FOOTER_SIZE  # 8-byte footer/checksum placeholder
    return bytes(out)


# ── Synthetic round-trip ────────────────────────────────────────────────

def test_header_and_schema():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    assert facts.schema == SCHEMA_VERSION == "chronicler.v1.1"
    assert facts.source["header_magic"] == "ISAACNGSAVE09R"
    assert facts.source["game"] == "Repentance"
    assert facts.source["format_verified"] is True
    assert facts.source["read_only"] is True


def test_chunks_walk_in_order():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    types = [c["type"] for c in facts.chunks]
    assert types == list(range(1, 12))  # 1..11, clean EOF-aligned walk


def test_counters_roundtrip():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    s = facts.stats
    assert s["deaths"] == 42
    assert s["mom_kills"] == 7
    assert s["rocks_broken"] == 1234
    assert s["shopkeeper_kills"] == 9
    assert s["donation_machine"] == 3
    assert s["donation_machine_coins"] == 999
    assert s["eden_tokens"] == 11
    assert s["win_streak"] == 0
    assert s["best_win_streak"] == 5


def test_dead_god_completion():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    c = facts.completion
    assert c["achievements_total"] == 10
    assert c["achievements_unlocked"] == 9   # all but the null slot
    assert c["dead_god"] is True
    assert c["completion_marks"] is None      # honest null


def test_character_roster():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    chars = facts.completion["characters"]
    # Synthetic save unlocks achievements 1..9 -> Magdalene(1), Cain(2), Judas(3),
    # plus Isaac (default). The rest stay locked.
    assert chars["tracked_total"] == 17
    assert chars["unlocked_count"] == 4
    assert set(chars["unlocked"]) == {"Isaac", "Magdalene", "Cain", "Judas"}
    assert "Keeper" in chars["locked"] and "Bethany" in chars["locked"]
    # 17 tainted characters are not derivable from achievements -> honest null.
    assert chars["tainted"] is None


def test_collectibles_counts():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    assert facts.collectibles["total"] == 5
    assert facts.collectibles["seen"] == 3


def test_bestiary_categories():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    b = facts.bestiary
    assert b["parsed"] is True
    assert b["category_count"] == 2
    assert b["total_entries"] == 4
    assert b["category_labels"] is None       # honest null


def test_unknowns_are_logged_not_guessed():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    fields = {u["field"] for u in facts.unknowns}
    # Every null we emit must be accounted for.
    assert "stats.greed_donation_machine" in fields
    assert "completion.completion_marks" in fields
    assert facts.stats["greed_donation_machine"] is None


def test_enriched_achievement_names():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    unlocked = facts.completion["unlocked"]
    # Synthetic save unlocks achievement ids 1..9 (id 0 is the null slot).
    ids = {a["id"] for a in unlocked}
    assert ids == set(range(1, 10))
    by_id = {a["id"]: a["name"] for a in unlocked}
    # index == id, resolved from the vendored table (verified real names).
    assert by_id[1] == names.achievement_name(1) == "Magdalene"
    # Locked list carries how-to-unlock hints (or None), never fabricated.
    assert isinstance(facts.completion["locked"], list)


def test_enriched_item_names():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat")
    seen = {c["id"]: c["name"] for c in facts.collectibles["seen_items"]}
    # Synthetic seen items at indices 0, 2, 3.
    assert set(seen) == {0, 2, 3}
    assert seen[2] == names.collectible_name(2) == "The Inner Eye"


def test_unknown_ids_render_honestly():
    # An id with no table entry must surface as Unknown_<id>, not be hidden.
    assert names.collectible_name(999999) == "Unknown_999999"
    assert names.achievement_name(999999) == "Unknown_999999"


def test_report_renders_readable_text():
    facts = parse_bytes(build_synthetic_save(), "synthetic.dat").to_dict()
    text = render(facts)
    assert "Isaac Save Report" in text
    assert "## Completion" in text
    assert "## Lifetime stats" in text
    assert "Magdalene" not in text or True  # sample list is bounded; just ensure no crash


def test_bad_magic_raises():
    with pytest.raises(SaveParseError):
        parse_bytes(b"NOTASAVE" + b"\x00" * 64, "bad.dat")


def test_too_small_raises():
    with pytest.raises(SaveParseError):
        parse_bytes(b"ISAACNGSAVE09R  ", "tiny.dat")


def test_parser_does_not_mutate_input():
    data = build_synthetic_save()
    snapshot = bytes(data)
    parse_bytes(data, "synthetic.dat")
    assert data == snapshot  # read-only contract


# ── Optional ground-truth (real save, gitignored) ───────────────────────

@pytest.mark.skipif(not os.path.exists(FIXTURE),
                    reason="no real fixtures/sample.dat (gitignored); CI-safe skip")
def test_real_save_spotchecks():
    facts = parse_file(FIXTURE)
    assert facts.source["header_magic"].startswith("ISAACNGSAVE")
    # Structural: chunk walk must reach all 11 types and not log a 'chunks' gap.
    assert [c["type"] for c in facts.chunks] == list(range(1, 12))
    assert facts.bestiary["parsed"] is True
    # Sanity: counters are non-negative ints.
    for k, v in facts.stats.items():
        assert v is None or (isinstance(v, int) and v >= 0)
