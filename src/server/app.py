"""Minimal read-only facts server (stdlib only — cheapest seam).

Mirrors fft-psx-vera's server-as-brain seam without pulling FastAPI or any
runtime deps (keeps the smoke test install-free). Spine 2 can swap this for the
real service.

    python -m src.server.app fixtures/sample.dat --port 8765
    curl localhost:8765/facts

Endpoints (GET only; the save corpus is strictly read-only):
    /healthz  -> {"ok": true, "schema": "chronicler.v0"}
    /facts    -> the parsed chronicler.v0 facts object
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..parser.chronicler import parse_file, SCHEMA_VERSION


def build_handler(facts_dict: dict):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (stdlib naming)
            if self.path.rstrip("/") in ("", "/healthz"):
                self._send(200, {"ok": True, "schema": SCHEMA_VERSION})
            elif self.path.rstrip("/") == "/facts":
                self._send(200, facts_dict)
            else:
                self._send(404, {"error": "not found", "paths": ["/healthz", "/facts"]})

        def log_message(self, *args):  # quiet by default
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Serve chronicler facts (read-only).")
    ap.add_argument("path", help="path to persistentgamedata{N}.dat")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)

    facts = parse_file(args.path).to_dict()
    httpd = HTTPServer(("127.0.0.1", args.port), build_handler(facts))
    print(f"chronicler serving facts on http://127.0.0.1:{args.port}/facts")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
