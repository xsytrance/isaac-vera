"""prime-as-brain: a read-only service + dashboard over one save or a whole folder.

Stdlib only (no deps, no build step). Holds the parsed chronicler facts for one
or more save slots, serves the frontend (built SPA if present, else a zero-build
dashboard), and answers grounded questions via Ollama on prime. Routing is a pure
function (`route`) so it can be unit-tested without a socket or a live model.

    python -m src.server.app save.dat --port 8765 [--bind 0.0.0.0]
    python -m src.server.app /path/to/userdata/250900/remote/   # all slots

Endpoints:
    GET  /            -> frontend (SPA or dashboard)
    GET  /healthz     -> {ok, schema, model}
    GET  /slots       -> [{file, game, achievements_*, dead_god, default}]
    GET  /facts[?slot=FILE]   -> chronicler facts for a slot (default = best)
    GET  /report[?slot=FILE]  -> Save Report (text) for a slot
    POST /ask         -> {answer, model} from {question, slot?, history?}
"""
from __future__ import annotations

import argparse
import json
import os
from collections import namedtuple
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from ..parser.chronicler import parse_file, SCHEMA_VERSION
from ..parser.slots import scan, most_progressed
from ..companion.companion import Companion
from ..companion.ollama_client import OllamaClient, OllamaError
from ..report import render

_DASHBOARD = Path(__file__).parent / "dashboard.html"
# Built SPA (frontend/dist) lives at the repo root; gitignored, present after
# `npm run build`. When present, it is served in preference to dashboard.html.
_SPA_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

_CTYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
           ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json",
           ".ico": "image/x-icon", ".woff2": "font/woff2", ".map": "application/json"}

Static = namedtuple("Static", "content_type body")


class Html(str):
    """Marker so the handler serves a string as text/html (vs text/plain)."""


def _load_spa(dist: Path) -> dict:
    """Map url paths -> Static(content_type, bytes) for a built SPA, or {}."""
    if not (dist / "index.html").is_file():
        return {}
    out: dict[str, Static] = {}
    for f in dist.rglob("*"):
        if f.is_file():
            url = "/" + f.relative_to(dist).as_posix()
            out[url] = Static(_CTYPES.get(f.suffix, "application/octet-stream"),
                              f.read_bytes())
    out["/"] = out["/index.html"]  # SPA entry
    return out


def _slot_entry(facts: dict, client) -> dict:
    return {"facts": facts, "report": render(facts),
            "companion": Companion(facts, client=client)}


def make_state(path: str, host: str | None = None, model: str | None = None) -> dict:
    client = OllamaClient(host=host, model=model)
    slots: dict[str, dict] = {}
    order: list[str] = []

    if os.path.isdir(path):
        results = scan(path)
        for r in results:
            if r.get("ok"):
                slots[r["file"]] = _slot_entry(r["facts"], client)
                order.append(r["file"])
        if not slots:
            raise SystemExit(f"no parseable saves in {path}")
        best = most_progressed(results)
        default = best["file"] if best else order[0]
    else:
        facts = parse_file(path).to_dict()
        name = facts["source"]["name"]
        slots[name] = _slot_entry(facts, client)
        order.append(name)
        default = name

    return {
        "slots": slots, "order": order, "default": default, "client": client,
        "dashboard": Html(_DASHBOARD.read_text(encoding="utf-8")),
        "static": _load_spa(_SPA_DIST),
    }


def _slot(state: dict, name: str | None) -> dict:
    slots = state["slots"]
    return slots[name] if name in slots else slots[state["default"]]


def _slot_summaries(state: dict) -> list[dict]:
    out = []
    for f in state["order"]:
        c = state["slots"][f]["facts"]["completion"]
        out.append({
            "file": f,
            "game": state["slots"][f]["facts"]["source"].get("game"),
            "achievements_unlocked": c.get("achievements_unlocked"),
            "achievements_total": c.get("achievements_total"),
            "dead_god": c.get("dead_god"),
            "default": f == state["default"],
        })
    return out


def route(method: str, path: str, body: bytes, state: dict):
    """Pure router: returns (status:int, payload). payload is a dict (-> JSON),
    an Html/Static (binary), or a plain str (-> text/plain). Never fabricates: a
    model failure becomes 503."""
    u = urlsplit(path)
    p = "/" + u.path.strip("/")
    slot = parse_qs(u.query).get("slot", [None])[0]
    static = state.get("static") or {}

    if method == "GET" and p in static:          # built SPA asset (or its index)
        return 200, static[p]
    if method == "GET" and p in ("/", "/dashboard"):
        return 200, static.get("/", state["dashboard"])
    if method == "GET" and p == "/healthz":
        return 200, {"ok": True, "schema": SCHEMA_VERSION,
                     "model": state["client"].model}
    if method == "GET" and p == "/slots":
        return 200, _slot_summaries(state)
    if method == "GET" and p == "/facts":
        return 200, _slot(state, slot)["facts"]
    if method == "GET" and p == "/report":
        return 200, _slot(state, slot)["report"]
    if method == "POST" and p == "/ask":
        try:
            data = json.loads(body or b"{}")
        except (ValueError, TypeError):
            return 400, {"error": "body must be JSON"}
        question = (data.get("question") or "").strip()
        if not question:
            return 400, {"error": "missing 'question'"}
        entry = _slot(state, data.get("slot") or slot)
        try:
            ans = entry["companion"].ask(question, history=data.get("history"))
        except OllamaError as exc:
            return 503, {"error": str(exc)}
        return 200, {"answer": ans, "model": state["client"].model}
    return 404, {"error": "not found",
                 "endpoints": ["GET /", "GET /slots", "GET /facts", "GET /report",
                               "POST /ask"]}


def _build_handler(state: dict):
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, payload) -> None:
            if isinstance(payload, Static):
                body, ctype = payload.body, payload.content_type
            elif isinstance(payload, Html):
                body, ctype = payload.encode("utf-8"), "text/html; charset=utf-8"
            elif isinstance(payload, str):
                body, ctype = payload.encode("utf-8"), "text/plain; charset=utf-8"
            else:
                body, ctype = json.dumps(payload).encode("utf-8"), "application/json"
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            status, payload = route("GET", self.path, b"", state)
            self._respond(status, payload)

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            status, payload = route("POST", self.path, body, state)
            self._respond(status, payload)

        def log_message(self, *args):  # quiet
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Serve the chronicler dashboard + Vera (read-only).")
    ap.add_argument("path", help="a save .dat, or a folder of saves (remote/)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--bind", default="127.0.0.1",
                    help="bind address (use 0.0.0.0 to reach it over your tailnet)")
    ap.add_argument("--host", default=None, help="Ollama host (default: prime / $OLLAMA_HOST)")
    ap.add_argument("--model", default=None, help="Ollama model (default: $OLLAMA_MODEL or first installed)")
    args = ap.parse_args(argv)

    state = make_state(args.path, host=args.host, model=args.model)
    httpd = HTTPServer((args.bind, args.port), _build_handler(state))
    print(f"isaac-vera on http://{args.bind}:{args.port}/  "
          f"({len(state['order'])} slot(s) · / · /slots /facts /report · POST /ask)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
