"""Orchestrate: chronicler facts + a question -> grounded answer from Ollama."""
from __future__ import annotations

from typing import Optional

from .grounding import build_system_prompt
from .ollama_client import OllamaClient


class Companion:
    """Holds the parsed facts and a model client; answers grounded questions."""

    def __init__(self, facts: dict, client: Optional[OllamaClient] = None,
                 max_locked: int = 60):
        self.facts = facts
        self.client = client or OllamaClient()
        self.system_prompt = build_system_prompt(facts, max_locked=max_locked)

    def ask(self, question: str, history: Optional[list[dict]] = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        # Low temperature: we want the model to stick to the truth block.
        return self.client.chat(messages, options={"temperature": 0.2})


def answer(facts: dict, question: str, client: Optional[OllamaClient] = None) -> str:
    """One-shot convenience: ask a single grounded question."""
    return Companion(facts, client=client).ask(question)
