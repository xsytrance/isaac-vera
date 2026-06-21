"""Minimal Ollama HTTP client (stdlib only).

Talks to the "prime" box over Tailscale by default. Host and model are
env-configurable so the same code runs from any tailnet machine:

    OLLAMA_HOST   default http://100.110.224.126:11434   (prime)
    OLLAMA_MODEL  default unset -> auto-detect first installed model

No third-party deps (keeps the project install-free); uses urllib.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# "prime" over Tailscale. Override with OLLAMA_HOST when running elsewhere.
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://100.110.224.126:11434")
# No hard-coded model: prefer OLLAMA_MODEL, else auto-detect from /api/tags.
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL")


class OllamaError(RuntimeError):
    """Raised when the model host is unreachable or returns an error. We surface
    this honestly rather than fabricating an answer."""


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None,
                 timeout: float = 120.0):
        self.host = (host or DEFAULT_HOST).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout

    # -- low-level --------------------------------------------------------
    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.host}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise OllamaError(
                f"could not reach Ollama at {self.host} ({exc}). "
                f"Is the tailnet up and is '{self.host}' the prime box?") from exc

    def _get(self, path: str) -> dict:
        url = f"{self.host}{path}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise OllamaError(f"could not reach Ollama at {self.host} ({exc})") from exc

    # -- high-level -------------------------------------------------------
    def list_models(self) -> list[str]:
        tags = self._get("/api/tags").get("models", [])
        return [m.get("name", "") for m in tags if m.get("name")]

    def resolve_model(self) -> str:
        """Pick the model to use: explicit > env > first installed."""
        if self.model:
            return self.model
        models = self.list_models()
        if not models:
            raise OllamaError(
                f"no model set and none installed on {self.host}. "
                f"Set OLLAMA_MODEL or `ollama pull <model>` on prime.")
        self.model = models[0]
        return self.model

    def chat(self, messages: list[dict], options: dict | None = None) -> str:
        """Non-streaming /api/chat. Returns the assistant message content."""
        payload = {
            "model": self.resolve_model(),
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        resp = self._post("/api/chat", payload)
        return resp.get("message", {}).get("content", "")
