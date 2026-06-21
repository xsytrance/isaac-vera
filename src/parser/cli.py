"""CLI: parse a persistentgamedata.dat (or a whole remote/ folder) to facts/report.

Usage:
    python -m src.parser.cli save.dat            # facts JSON
    python -m src.parser.cli save.dat --report   # human-readable Save Report
    python -m src.parser.cli save.dat --raw      # include raw arrays
    python -m src.parser.cli remote/             # multi-slot table (a directory)

The facts object is the client/server seam contract (prime-as-brain): the
parser holds the truth; everything downstream reads this JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .chronicler import parse_file, SaveParseError
from .slots import scan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chronicle an Isaac save (read-only).")
    ap.add_argument("path", help="path to a .dat, or a folder of saves")
    ap.add_argument("--raw", action="store_true",
                    help="include raw counter/achievement arrays")
    ap.add_argument("--report", action="store_true",
                    help="print a human-readable Save Report instead of JSON")
    args = ap.parse_args(argv)

    # A directory -> scan every slot and print a summary table (or JSON).
    if os.path.isdir(args.path):
        from ..report import render_slots
        results = scan(args.path)
        if not results:
            print(f"error: no persistentgamedata*.dat in {args.path}", file=sys.stderr)
            return 1
        if args.report or not args.raw:
            print(render_slots(results))
        else:
            json.dump(results, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 0

    try:
        facts = parse_file(args.path)
    except (SaveParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.report:
        from ..report import render
        print(render(facts.to_dict()))
        return 0

    out = facts.to_dict()
    if not args.raw:
        out.pop("raw", None)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
