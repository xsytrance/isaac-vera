"""Companion tests — grounding + orchestration, with a mocked model.

No network and no running Ollama: the model client is faked. This mirrors the
project rule "mock the model in CI".
"""
from __future__ import annotations

import pytest

from src.companion.grounding import build_truth_block, build_system_prompt
from src.companion.companion import Companion
from src.companion.ollama_client import OllamaClient, OllamaError

# A representative facts dict (shape matches chronicler.v1).
FACTS = {
    "schema": "chronicler.v1",
    "source": {"name": "rep+persistentgamedata1.dat", "game": "Repentance",
               "format_verified": True},
    "completion": {
        "achievements_unlocked": 111, "achievements_total": 642,
        "dead_god": False, "dead_god_progress": 0.1729,
        "locked": [
            {"id": 50, "name": "A Cross", "unlock": "Defeat Isaac as Magdalene"},
            {"id": 51, "name": "A Bag of Pennies", "unlock": "Defeat Isaac as Cain"},
        ],
    },
    "stats": {"deaths": 8, "mom_kills": 11, "best_win_streak": 2, "win_streak": 0,
              "rocks_broken": 3176, "donation_machine_coins": 0, "eden_tokens": 0,
              "greed_donation_machine": None},
    "collectibles": {"seen": 388, "total": 733},
    "bestiary": {"parsed": True, "total_entries": 739, "category_count": 4},
    "unknowns": [{"field": "stats.greed_donation_machine", "reason": "unconfirmed"}],
}


class FakeClient:
    """Stands in for OllamaClient; records messages, returns a canned reply."""
    def __init__(self, reply="You should unlock A Cross next."):
        self.reply = reply
        self.last_messages = None
        self.last_options = None

    def chat(self, messages, options=None):
        self.last_messages = messages
        self.last_options = options
        return self.reply


# ── grounding ────────────────────────────────────────────────────────────

def test_truth_block_has_real_numbers_and_whats_left():
    tb = build_truth_block(FACTS)
    assert "TRUTH BLOCK" in tb
    assert "111/642 achievements" in tb
    assert "Dead God=False" in tb
    assert "deaths 8" in tb
    assert "Collectibles seen: 388/733" in tb
    assert "WHAT'S LEFT" in tb
    assert "A Cross" in tb and "Defeat Isaac as Magdalene" in tb
    assert "NOT TRACKED" in tb  # nulls listed honestly


def test_system_prompt_sets_persona_and_rules():
    sp = build_system_prompt(FACTS)
    assert "Vera" in sp
    assert "Never invent" in sp
    assert "chronicler.v1" in sp  # rules reference the schema


# ── orchestration ────────────────────────────────────────────────────────

def test_companion_passes_grounded_messages_and_returns_reply():
    fake = FakeClient(reply="42 deaths? No — 8.")
    comp = Companion(FACTS, client=fake)
    out = comp.ask("how many deaths?")
    assert out == "42 deaths? No — 8."
    # system message first, carrying the truth block; user question last.
    assert fake.last_messages[0]["role"] == "system"
    assert "TRUTH BLOCK" in fake.last_messages[0]["content"]
    assert fake.last_messages[-1] == {"role": "user", "content": "how many deaths?"}
    # low temperature keeps it on the facts
    assert fake.last_options["temperature"] == 0.2


def test_companion_threads_history():
    fake = FakeClient()
    comp = Companion(FACTS, client=fake)
    comp.ask("second?", history=[{"role": "user", "content": "first"},
                                 {"role": "assistant", "content": "ok"}])
    roles = [m["role"] for m in fake.last_messages]
    assert roles == ["system", "user", "assistant", "user"]


# ── model resolution (no network) ────────────────────────────────────────

def test_resolve_model_prefers_explicit():
    c = OllamaClient(host="http://x", model="prime")
    assert c.resolve_model() == "prime"


def test_resolve_model_falls_back_to_first_installed(monkeypatch):
    c = OllamaClient(host="http://x", model=None)
    monkeypatch.setattr(c, "list_models", lambda: ["mistral", "llama3.1"])
    assert c.resolve_model() == "mistral"


def test_resolve_model_errors_when_none(monkeypatch):
    c = OllamaClient(host="http://x", model=None)
    monkeypatch.setattr(c, "list_models", lambda: [])
    with pytest.raises(OllamaError):
        c.resolve_model()


def test_default_host_is_prime():
    # Default points at the prime box unless OLLAMA_HOST overrides it.
    import os
    if "OLLAMA_HOST" not in os.environ:
        assert OllamaClient().host == "http://100.110.224.126:11434"
