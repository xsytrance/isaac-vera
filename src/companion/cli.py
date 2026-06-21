"""Vera companion CLI.

    # one-shot
    python -m src.companion.cli save.dat "what should I unlock next?"
    # interactive
    python -m src.companion.cli save.dat
    # inspect the exact grounded prompt (no model call)
    python -m src.companion.cli save.dat --show-prompt
    # talk to a specific host/model
    OLLAMA_MODEL=llama3.1 python -m src.companion.cli save.dat "how close to Dead God?"

Defaults to the prime box (http://100.110.224.126:11434) over Tailscale.
"""
from __future__ import annotations

import argparse
import sys

from ..parser.chronicler import parse_file, SaveParseError
from .companion import Companion
from .grounding import build_system_prompt
from .ollama_client import OllamaClient, OllamaError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Vera — grounded Isaac save companion.")
    ap.add_argument("path", help="path to persistentgamedata{N}.dat")
    ap.add_argument("question", nargs="*", help="question (omit for interactive mode)")
    ap.add_argument("--host", default=None, help="Ollama host (default: prime / $OLLAMA_HOST)")
    ap.add_argument("--model", default=None, help="model name (default: $OLLAMA_MODEL or first installed)")
    ap.add_argument("--show-prompt", action="store_true",
                    help="print the grounded system prompt and exit (no model call)")
    ap.add_argument("--list-models", action="store_true",
                    help="list models installed on the host and exit")
    args = ap.parse_args(argv)

    try:
        facts = parse_file(args.path).to_dict()
    except (SaveParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.show_prompt:
        print(build_system_prompt(facts))
        return 0

    client = OllamaClient(host=args.host, model=args.model)

    if args.list_models:
        try:
            for m in client.list_models():
                print(m)
        except OllamaError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    companion = Companion(facts, client=client)

    if args.question:
        try:
            print(companion.ask(" ".join(args.question)))
        except OllamaError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    # Interactive REPL
    print(f"Vera is reading {facts['source']['name']} "
          f"({facts['completion']['achievements_unlocked']}/"
          f"{facts['completion']['achievements_total']} achievements). "
          f"Ask away — Ctrl-D to quit.")
    history: list[dict] = []
    while True:
        try:
            q = input("you> ").strip()
        except EOFError:
            print()
            break
        if not q:
            continue
        try:
            a = companion.ask(q, history=history)
        except OllamaError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"vera> {a}")
        history += [{"role": "user", "content": q},
                    {"role": "assistant", "content": a}]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
