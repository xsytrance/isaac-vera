"""Server router tests — pure `route()`, no socket, model mocked."""
from __future__ import annotations

import json

from src.parser import parse_bytes, SCHEMA_VERSION
from src.companion.companion import Companion
from src.companion.ollama_client import OllamaError
from src.report import render
from src.server.app import route
from tests.test_parser import build_synthetic_save

FACTS = parse_bytes(build_synthetic_save(), "synthetic.dat").to_dict()


class FakeClient:
    def __init__(self, reply="You have 8 deaths.", model="prime", raises=False):
        self.reply, self.model, self.raises = reply, model, raises

    def chat(self, messages, options=None):
        if self.raises:
            raise OllamaError("prime unreachable")
        return self.reply


def _state(client=None):
    client = client or FakeClient()
    return {"facts": FACTS, "report": render(FACTS),
            "companion": Companion(FACTS, client=client)}


def test_healthz():
    status, payload = route("GET", "/healthz", b"", _state())
    assert status == 200 and payload["ok"] is True
    assert payload["schema"] == SCHEMA_VERSION and payload["model"] == "prime"


def test_facts_endpoint():
    status, payload = route("GET", "/facts", b"", _state())
    assert status == 200 and payload["schema"] == SCHEMA_VERSION


def test_report_endpoint_is_text():
    status, payload = route("GET", "/report", b"", _state())
    assert status == 200 and isinstance(payload, str)
    assert "Isaac Save Report" in payload


def test_ask_returns_grounded_answer():
    body = json.dumps({"question": "how many deaths?"}).encode()
    status, payload = route("POST", "/ask", body, _state(FakeClient(reply="8 deaths.")))
    assert status == 200
    assert payload == {"answer": "8 deaths.", "model": "prime"}


def test_ask_missing_question_is_400():
    status, payload = route("POST", "/ask", b"{}", _state())
    assert status == 400 and "question" in payload["error"]


def test_ask_bad_json_is_400():
    status, payload = route("POST", "/ask", b"not json", _state())
    assert status == 400


def test_ask_model_down_is_503_not_fabricated():
    body = json.dumps({"question": "hi"}).encode()
    status, payload = route("POST", "/ask", body, _state(FakeClient(raises=True)))
    assert status == 503 and "unreachable" in payload["error"]


def test_unknown_route_404():
    status, payload = route("GET", "/nope", b"", _state())
    assert status == 404 and "endpoints" in payload
