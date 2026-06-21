"""isaac-vera parser package — The Chronicler (Spine 1).

Public surface: parse a persistentgamedata.dat into versioned, read-only facts.
"""
from .chronicler import (
    SCHEMA_VERSION,
    ChroniclerFacts,
    SaveParseError,
    parse_bytes,
    parse_file,
)

__all__ = [
    "SCHEMA_VERSION",
    "ChroniclerFacts",
    "SaveParseError",
    "parse_bytes",
    "parse_file",
]
