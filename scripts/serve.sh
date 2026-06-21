#!/usr/bin/env bash
# Run isaac-vera and reach it over your tailnet on ONE port (default 8765).
#
#   scripts/serve.sh <save.dat | remote/ folder> [PORT]
#
# Everything — the dashboard AND the Vera chat — is on this single port. The
# server reaches Ollama server-side, so your devices only ever need this one
# port. Read-only: it never writes to your .dat.
set -euo pipefail

SAVE="${1:?usage: scripts/serve.sh <save.dat | remote/ folder> [port]}"
PORT="${2:-8765}"
cd "$(dirname "$0")/.."

echo "isaac-vera → http://0.0.0.0:${PORT}/  (read-only)"
if command -v tailscale >/dev/null 2>&1; then
  ip="$(tailscale ip -4 2>/dev/null | head -1 || true)"
  [ -n "${ip:-}" ] && echo "tailnet     → http://${ip}:${PORT}/   (same port on every device)"
  echo "clean HTTPS → run:  tailscale serve --bg ${PORT}   then open https://<host>.<tailnet>.ts.net/"
  echo "            (do NOT use 'tailscale funnel' — that would expose your save to the public internet)"
fi

# Pass OLLAMA_HOST / OLLAMA_MODEL through for the Vera chat (optional).
exec python3 -m src.server.app "$SAVE" --bind 0.0.0.0 --port "${PORT}"
