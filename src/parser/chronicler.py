"""The Chronicler — Isaac ``persistentgamedata.dat`` -> ground-truth facts.

This is the parser-truth module boundary for isaac-vera (the analogue of
fft-psx-vera's ``save_parser.py`` + ``save_truth.py`` seam): raw save bytes go
in, a versioned, flat facts object comes out. It is strictly READ-ONLY and it
never invents a value. Anything it cannot confidently map is ``None`` and is
recorded in ``facts.unknowns`` with a reason.

Schema: ``chronicler.v0`` (Spine 2, the Commentator, will extend this).
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from . import format as fmt

SCHEMA_VERSION = "chronicler.v0"


class SaveParseError(Exception):
    """Raised only for structural failures (bad magic, truncation). We fail
    loudly rather than emit fabricated facts."""


@dataclass
class Chunk:
    type: int
    name: str
    count: int
    field2: int
    data_offset: int
    data_len: int


@dataclass
class ChroniclerFacts:
    schema: str = SCHEMA_VERSION
    source: dict = field(default_factory=dict)
    completion: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    collectibles: dict = field(default_factory=dict)
    bestiary: dict = field(default_factory=dict)
    chunks: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    unknowns: list = field(default_factory=list)

    def note_unknown(self, field_path: str, reason: str) -> None:
        """Record a field we deliberately left null. Truth over guessing."""
        self.unknowns.append({"field": field_path, "reason": reason})

    def to_dict(self) -> dict:
        return asdict(self)


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _walk_chunks(data: bytes) -> list[Chunk]:
    """Self-describing walk of the chunk container.

    Advances by ``count * stride`` (verified to land exactly on EOF for the
    Repentance format). On an unrecognized type we stop rather than guess, so a
    malformed/newer file degrades to "partially parsed" instead of garbage.
    """
    chunks: list[Chunk] = []
    off = fmt.CHUNKS_START
    end = len(data) - fmt.FOOTER_SIZE
    while off + fmt.CHUNK_HEADER_SIZE <= end:
        ctype, field2, count = struct.unpack_from("<III", data, off)
        if ctype not in fmt.CHUNK_NAMES:
            break  # unknown chunk type: stop cleanly, caller logs remainder
        data_off = off + fmt.CHUNK_HEADER_SIZE

        if ctype == fmt.BESTIARY:
            # Bestiary is the variable-length tail: an 8-byte sub-header then
            # (entity:u32, value:u32) pairs running up to the file footer.
            # Verified byte-for-byte on the Dead God save (4 categories, exact
            # EOF alignment).
            data_len = end - data_off
            chunks.append(Chunk(ctype, fmt.CHUNK_NAMES[ctype], count, field2,
                                data_off, data_len))
            off = end
            break

        stride = fmt.CHUNK_STRIDE[ctype]
        data_len = count * stride
        chunks.append(Chunk(ctype, fmt.CHUNK_NAMES[ctype], count, field2,
                            data_off, data_len))
        off = data_off + data_len
    return chunks


def _parse_counters(data: bytes, chunk: Chunk, facts: ChroniclerFacts) -> None:
    base = chunk.data_offset
    counters = [_u32(data, base + 4 * i) for i in range(chunk.count)]
    facts.raw["counters"] = counters

    stats: dict[str, Optional[int]] = {}
    for name, byte_off in fmt.COUNTER_OFFSETS.items():
        idx = byte_off // 4
        if idx < len(counters):
            stats[name] = counters[idx]
        else:
            stats[name] = None
            facts.note_unknown(f"stats.{name}",
                               f"counter index {idx} out of range ({len(counters)} counters)")
    # The greed-vs-normal donation machine split is not confirmed: do not guess.
    stats["greed_donation_machine"] = None
    facts.note_unknown(
        "stats.greed_donation_machine",
        "two donation counters exist (idx 0 and 19); which is Greed-mode is unconfirmed",
    )
    facts.stats = stats


def _parse_achievements(data: bytes, chunk: Chunk, facts: ChroniclerFacts) -> None:
    blob = data[chunk.data_offset:chunk.data_offset + chunk.data_len]
    locked = [i for i, b in enumerate(blob) if b == 0]
    unlocked = len(blob) - len(locked)
    # Index 0 is the null/sentinel achievement; "Dead God" == every real
    # achievement unlocked. If the only locked slot is the sentinel, it's a
    # full clear. We report the count plainly and the boolean honestly.
    real_locked = [i for i in locked if i != 0]
    facts.completion = {
        "achievements_unlocked": unlocked,
        "achievements_total": len(blob),
        "dead_god": len(real_locked) == 0 and unlocked > 0,
        "dead_god_progress": round(unlocked / len(blob), 4) if blob else None,
        # Per-character hard-mode completion marks are not yet mapped from the
        # achievement IDs -> left null rather than guessed.
        "completion_marks": None,
    }
    facts.note_unknown("completion.completion_marks",
                       "per-character mark mapping not implemented in v0")
    facts.raw["achievements_locked_indices"] = locked


def _parse_collectibles(data: bytes, chunk: Chunk, facts: ChroniclerFacts) -> None:
    blob = data[chunk.data_offset:chunk.data_offset + chunk.data_len]
    seen = sum(1 for b in blob if b != 0)
    facts.collectibles = {
        "total": chunk.count,
        "seen": seen,
        # Per-item touched/seen detail and item-name mapping deferred to a later
        # spine; v0 reports counts only.
        "by_id": None,
    }
    facts.note_unknown("collectibles.by_id",
                       "per-item id->name mapping not implemented in v0")


def _parse_bestiary(data: bytes, chunk: Chunk, facts: ChroniclerFacts) -> None:
    # Skip the 8-byte sub-header, then read (entity, value) pairs and split into
    # categories by entity-key reset. Validate hard; on any mismatch, null it.
    pairs_start = chunk.data_offset + 8
    region = (len(data) - fmt.FOOTER_SIZE) - pairs_start
    if region < 0 or region % 8 != 0:
        facts.bestiary = {"present": True, "parsed": False}
        facts.note_unknown("bestiary",
                            f"pair region not 8-aligned (got {region} bytes)")
        return

    categories: list[dict] = []
    cur_count = 0
    cur_value_sum = 0
    prev_entity = -1
    o = pairs_start
    end = len(data) - fmt.FOOTER_SIZE
    total = 0
    while o + 8 <= end:
        entity = _u32(data, o)
        value = _u32(data, o + 4)
        if entity < prev_entity:
            categories.append({"entries": cur_count, "value_sum": cur_value_sum})
            cur_count = 0
            cur_value_sum = 0
        prev_entity = entity
        cur_count += 1
        cur_value_sum += value
        total += 1
        o += 8
    categories.append({"entries": cur_count, "value_sum": cur_value_sum})

    facts.bestiary = {
        "present": True,
        "parsed": True,
        "category_count": len(categories),
        "categories": categories,
        "total_entries": total,
        # Which category is kills / encounters / hits / deaths is NOT confirmed,
        # and entity-key -> monster-name mapping is deferred. Honest nulls:
        "category_labels": None,
    }
    facts.note_unknown("bestiary.category_labels",
                       "kill/encounter/hit/death labelling unconfirmed in v0")
    if len(categories) != chunk.count:
        facts.note_unknown(
            "bestiary.category_count",
            f"detected {len(categories)} categories but chunk count={chunk.count}",
        )


def parse_bytes(data: bytes, source_name: str = "<bytes>") -> ChroniclerFacts:
    """Parse raw save bytes into ``chronicler.v0`` facts. Read-only."""
    facts = ChroniclerFacts()

    if len(data) < fmt.HEADER_SIZE + fmt.FOOTER_SIZE:
        raise SaveParseError(f"file too small ({len(data)} bytes) to be a save")

    magic_raw = data[:fmt.HEADER_SIZE]
    if not magic_raw.startswith(fmt.HEADER_MAGIC_PREFIX):
        raise SaveParseError(
            f"bad magic {magic_raw!r}: not an Isaac persistentgamedata file")
    magic = magic_raw.rstrip(b"\x00 ").decode("latin1")
    game = fmt.GAME_BY_MAGIC.get(magic)
    verified = magic in fmt.VERIFIED_MAGICS

    facts.source = {
        "name": source_name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "header_magic": magic,
        "game": game,  # None if we don't recognize the version
        "format_verified": verified,
        "read_only": True,
        "leading_value": _u32(data, fmt.LEADING_VALUE_OFFSET),  # raw, meaning unconfirmed
        "footer_hex": data[-fmt.FOOTER_SIZE:].hex(),
    }
    if game is None:
        facts.note_unknown("source.game", f"unrecognized header magic {magic!r}")
    if not verified:
        facts.note_unknown(
            "source.format_verified",
            f"field offsets are byte-verified only for Repentance (09R); {magic!r} parsed structurally",
        )

    chunks = _walk_chunks(data)
    facts.chunks = [
        {"type": c.type, "name": c.name, "count": c.count} for c in chunks
    ]
    by_type = {c.type: c for c in chunks}

    if fmt.ACHIEVEMENTS in by_type:
        _parse_achievements(data, by_type[fmt.ACHIEVEMENTS], facts)
    if fmt.COUNTERS in by_type:
        _parse_counters(data, by_type[fmt.COUNTERS], facts)
    if fmt.COLLECTIBLES in by_type:
        _parse_collectibles(data, by_type[fmt.COLLECTIBLES], facts)
    if fmt.BESTIARY in by_type:
        _parse_bestiary(data, by_type[fmt.BESTIARY], facts)

    # Record any chunk types we did not reach (e.g. parser stopped early).
    reached = set(by_type)
    expected = set(fmt.CHUNK_NAMES)
    missing = sorted(expected - reached)
    if missing:
        facts.note_unknown(
            "chunks",
            "did not parse chunk types " + ", ".join(
                f"{t}:{fmt.CHUNK_NAMES[t]}" for t in missing),
        )
    return facts


def parse_file(path: str) -> ChroniclerFacts:
    """Read a ``.dat`` from disk (read-only) and parse it."""
    with open(path, "rb") as fh:  # 'rb' — we never open for write
        data = fh.read()
    import os
    return parse_bytes(data, source_name=os.path.basename(path))
