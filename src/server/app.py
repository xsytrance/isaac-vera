"""prime-as-brain: a single read-only service over one parsed save.

Stdlib only (no deps). Holds the parsed chronicler facts and answers grounded
questions via Ollama on prime. Routing is a pure function (`route`) so it can be
unit-tested without a socket or a live model.

    python -m src.server.app save.dat --port 8765 [--host ...] [--model ...]

Endpoints:
    GET  /healthz  -> {ok, schema, model}
    GET  /facts    -> chronicler.v1 facts (JSON)
    GET  /report   -> human-readable Save Report (text)
    POST /ask      -> {answer, model} from {question, history?}  (grounded)
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..parser.chronicler import parse_file, SCHEMA_VERSION
from ..companion.companion import Companion
from ..companion.ollama_client import OllamaClient, OllamaError
from ..report import render


def make_state(path: str, host: str | None = None, model: str | None = None) -> dict:
    facts = parse_file(path).to_dict()
    companion = Companion(facts, client=OllamaClient(host=host, model=model))
    return {"facts": facts, "report": render(facts), "companion": companion}


def route(method: str, path: str, body: bytes, state: dict):
    """Pure router: returns (status:int, payload). payload is a dict (-> JSON)
    or str (-> text/plain). Never fabricates: a model failure becomes 503."""
    p = "/" + path.strip("/")
    if method == "GET" and p in ("/", "/healthz"):
        model = state["companion"].client.model
        return 200, {"ok": True, "schema": SCHEMA_VERSION, "model": model}
    if method == "GET" and p == "/facts":
        return 200, state["facts"]
    if method == "GET" and p == "/report":
        return 200, state["report"]
    if method == "POST" and p == "/ask":
        try:
            data = json.loads(body or b"{}")
        except (ValueError, TypeError):
            return 400, {"error": "body must be JSON"}
        question = (data.get("question") or "").strip()
        if not question:
            return 400, {"error": "missing 'question'"}
        try:
            ans = state["companion"].ask(question, history=data.get("history"))
        except OllamaError as exc:
            return 503, {"error": str(exc)}
        return 200, {"answer": ans, "model": state["companion"].client.model}
    return 404, {"error": "not found",
                 "endpoints": ["GET /facts", "GET /report", "POST /ask"]}


def _build_handler(state: dict):
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, payload) -> None:
            if isinstance(payload, str):
                body = payload.encode("utf-8")
                ctype = "text/plain; charset=utf-8"
            else:
                body = json.dumps(payload).encode("utf-8")
                ctype = "application/json"
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
    ap = argparse.ArgumentParser(description="Serve chronicler facts + Vera (read-only).")
    ap.add_argument("path", help="path to persistentgamedata{N}.dat")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default=None, help="Ollama host (default: prime / $OLLAMA_HOST)")
    ap.add_argument("--model", default=None, help="Ollama model (default: $OLLAMA_MODEL or first installed)")
    args = ap.parse_args(argv)

    state = make_state(args.path, host=args.host, model=args.model)
    httpd = HTTPServer(("127.0.0.1", args.port), _build_handler(state))
    print(f"prime-as-brain on http://127.0.0.1:{args.port}  "
          f"(GET /facts /report · POST /ask)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
