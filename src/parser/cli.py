"""CLI: parse a persistentgamedata.dat and print chronicler.v0 facts as JSON.

Usage:
    python -m src.parser.cli fixtures/sample.dat
    python -m src.parser.cli fixtures/sample.dat --raw   # include raw arrays

The facts object is the client/server seam contract (prime-as-brain): the
parser holds the truth; everything downstream reads this JSON.
"""
from __future__ import annotations

import argparse
import json
import sys

from .chronicler import parse_file, SaveParseError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chronicle an Isaac save (read-only).")
    ap.add_argument("path", help="path to persistentgamedata{N}.dat")
    ap.add_argument("--raw", action="store_true",
                    help="include raw counter/achievement arrays")
    args = ap.parse_args(argv)

    try:
        facts = parse_file(args.path)
    except (SaveParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = facts.to_dict()
    if not args.raw:
        out.pop("raw", None)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
