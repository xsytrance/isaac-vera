"""Server router tests — pure `route()`, no socket, model mocked."""
from __future__ import annotations

import copy
import json

from src.parser import parse_bytes, SCHEMA_VERSION
from src.companion.companion import Companion
from src.companion.ollama_client import OllamaError
from src.report import render
from src.server.app import route, Html, Static
from tests.test_parser import build_synthetic_save

FACTS = parse_bytes(build_synthetic_save(), "synthetic.dat").to_dict()


class FakeClient:
    def __init__(self, reply="You have 8 deaths.", model="prime", raises=False):
        self.reply, self.model, self.raises = reply, model, raises

    def chat(self, messages, options=None):
        if self.raises:
            raise OllamaError("prime unreachable")
        return self.reply


def _slot(facts, client):
    return {"facts": facts, "report": render(facts),
            "companion": Companion(facts, client=client)}


def _state(client=None):
    client = client or FakeClient()
    return {"slots": {"synthetic.dat": _slot(FACTS, client)},
            "order": ["synthetic.dat"], "default": "synthetic.dat", "client": client,
            "dashboard": Html("<!doctype html><title>dash</title>")}


def _multi_state():
    client = FakeClient()
    f2 = copy.deepcopy(FACTS)
    f2["source"]["name"] = "slot2.dat"
    f2["completion"]["achievements_unlocked"] = 0
    return {"slots": {"slot1.dat": _slot(FACTS, client), "slot2.dat": _slot(f2, client)},
            "order": ["slot1.dat", "slot2.dat"], "default": "slot1.dat",
            "client": client, "dashboard": Html("x")}


def test_dashboard_served_as_html():
    status, payload = route("GET", "/", b"", _state())
    assert status == 200 and isinstance(payload, Html)
    assert "<!doctype html>" in payload.lower()


def test_built_spa_preferred_when_present():
    st = _state()
    st["static"] = {
        "/": Static("text/html; charset=utf-8", b"<html>spa</html>"),
        "/assets/app.js": Static("application/javascript", b"const x=1"),
    }
    s, p = route("GET", "/", b"", st)
    assert s == 200 and isinstance(p, Static) and p.content_type.startswith("text/html")
    s, p = route("GET", "/assets/app.js", b"", st)
    assert s == 200 and p.content_type == "application/javascript"


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


def test_slots_listing():
    status, payload = route("GET", "/slots", b"", _multi_state())
    assert status == 200 and len(payload) == 2
    assert {x["file"] for x in payload} == {"slot1.dat", "slot2.dat"}
    default = [x for x in payload if x["default"]]
    assert len(default) == 1 and default[0]["file"] == "slot1.dat"


def test_facts_slot_selection():
    st = _multi_state()
    _, p = route("GET", "/facts?slot=slot2.dat", b"", st)
    assert p["source"]["name"] == "slot2.dat"
    _, p = route("GET", "/facts", b"", st)  # default slot
    assert p["source"]["name"] == FACTS["source"]["name"]
    _, p = route("GET", "/facts?slot=nonexistent.dat", b"", st)  # falls back to default
    assert p["source"]["name"] == FACTS["source"]["name"]


def test_ask_uses_selected_slot():
    body = json.dumps({"question": "hi", "slot": "slot2.dat"}).encode()
    status, payload = route("POST", "/ask", body, _multi_state())
    assert status == 200 and "model" in payload
