"""Byte map for The Binding of Isaac ``persistentgamedata{N}.dat`` saves.

PARSER-TRUTH RULE (ported from fft-psx-vera): every constant here is sourced.
We do NOT reverse-engineer offsets from scratch and we never guess. Anything we
cannot confidently map is left for the parser to emit as ``None`` (logged).

Sources
-------
* Chunk container model + chunk-type enum:
  Zamiell/isaac-save-viewer ``src/enums/ChunkType.ts`` and
  ``src/types/IsaacSaveFile.d.ts`` (format reversed by "Blade" with Kaitai Struct).
* Header bytes, per-section element widths, and COUNTERS byte-offsets:
  Demorck/Isaac-save-manager ``js/Helpers/Constants.ts`` and
  ``js/Helpers/Statistics_offset.ts``.
* Container framing + EOF alignment + bestiary layout: empirically validated
  byte-for-byte against the public Dead God save in
  Zamiell/isaac-save-installer (``saves/Repentance/persistentgamedata.dat``).
  The chunk walk lands exactly on EOF with chunk types emitted 1..11 in order.

Only the Repentance header (``ISAACNGSAVE09R``) is byte-verified. Other game
versions parse structurally but their field mappings are flagged unverified.
"""
from __future__ import annotations

# ── Header ──────────────────────────────────────────────────────────────
# 16 bytes: the 14-char magic + two ASCII spaces (0x20 0x20) of padding.
HEADER_SIZE = 16
HEADER_MAGIC_PREFIX = b"ISAACNGSAVE"

# Magic -> human game name. Only 09R is byte-verified in this repo.
GAME_BY_MAGIC = {
    "ISAACNGSAVE09R": "Repentance",
    # Below are community-documented but NOT verified against bytes here:
    "ISAACNGSAVE08R": "Afterbirth+",  # unverified
    "ISAACNGSAVE06R": "Afterbirth",   # unverified
    "ISAACNGSAVE05R": "Rebirth",      # unverified
}
VERIFIED_MAGICS = {"ISAACNGSAVE09R"}

# A 4-byte value sits between the header and the first chunk. On the verified
# save it is 0x0B61A7BF — a checksum/stamp. We surface it raw and never claim a
# meaning we have not confirmed.
LEADING_VALUE_OFFSET = 0x10
CHUNKS_START = 0x14

# Trailing 8 bytes of the file are a global checksum/footer (not a chunk, not a
# bestiary pair). Verified: the last 8 bytes do not form a valid entity pair.
FOOTER_SIZE = 8

# ── Chunk framing ───────────────────────────────────────────────────────
# Each chunk: type:u32le, field2:u32le, count:u32le, then count*stride bytes.
# `field2` is count*4 for most chunks (count*1 for achievements); it is NOT the
# on-disk byte length, so we advance using the per-type stride table below
# (which matches Demorck's ENTRY_LENS and the verified walk).
CHUNK_HEADER_SIZE = 12

ACHIEVEMENTS = 1
COUNTERS = 2
LEVEL_COUNTERS = 3
COLLECTIBLES = 4
MINIBOSSES = 5
BOSSES = 6
CHALLENGES = 7
CUTSCENES = 8
GAME_SETTINGS = 9
SPECIAL_SEEDS = 10
BESTIARY = 11

CHUNK_NAMES = {
    ACHIEVEMENTS: "achievements",
    COUNTERS: "counters",
    LEVEL_COUNTERS: "level_counters",
    COLLECTIBLES: "collectibles",
    MINIBOSSES: "minibosses",
    BOSSES: "bosses",
    CHALLENGES: "challenges",
    CUTSCENES: "cutscenes",
    GAME_SETTINGS: "game_settings",
    SPECIAL_SEEDS: "special_seeds",
    BESTIARY: "bestiary",
}

# On-disk bytes per element, by chunk type (Demorck ENTRY_LENS, verified 1..10).
# BESTIARY (11) is variable-length and handled specially by the parser.
CHUNK_STRIDE = {
    ACHIEVEMENTS: 1,
    COUNTERS: 4,
    LEVEL_COUNTERS: 4,
    COLLECTIBLES: 1,
    MINIBOSSES: 1,
    BOSSES: 1,
    CHALLENGES: 1,
    CUTSCENES: 4,
    GAME_SETTINGS: 4,
    SPECIAL_SEEDS: 1,
}

# ── COUNTERS semantics ──────────────────────────────────────────────────
# Byte offsets INTO the counters chunk data (each counter is a u32le, so
# index == offset // 4). Sourced from Demorck/Isaac-save-manager
# Statistics_offset.ts and cross-checked for plausibility against the verified
# Dead God save (deaths=1159, mom_kills=1165, best_win_streak=112, donation=999).
#
# NOTE on donation vs greed: Demorck exposes two donation-ish counters
# (DONATION @0x00 and DONATION_COINS @0x4C). Which one is the Greed-mode machine
# is NOT confirmed, so the parser keeps both raw and leaves greed_donation = None
# rather than guess.
COUNTER_OFFSETS = {
    "donation_machine": 0x00,
    "mom_kills": 0x04,
    "rocks_broken": 0x08,
    "tinted_rocks_broken": 0x0C,
    "poop_destroyed": 0x14,
    "deaths": 0x24,
    "shopkeeper_kills": 0x2C,
    "donation_machine_coins": 0x4C,
    "eden_tokens": 0x54,
    "win_streak": 0x58,
    "best_win_streak": 0x5C,
}

# Bestiary entity key encoding (entity:u32, value:u32 pairs). The key packs
# (type << 16) | (variant << 8) | subtype. We expose counts faithfully but do
# NOT yet map keys -> monster names, nor confirm which category is
# kills/encounters/hits/deaths, so those labels stay None.
BESTIARY_KEY_TYPE_SHIFT = 16
