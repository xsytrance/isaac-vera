"""Vera — the grounded Isaac save companion (Spine 1.5).

A chat layer over chronicler facts: ask about your save, get answers grounded
strictly in parser-truth. Backed by Ollama (the "prime" box over Tailscale).
No fact is ever invented; nulls are reported as "not tracked".
"""
from .companion import Companion, answer
from .ollama_client import OllamaClient, OllamaError, DEFAULT_HOST, DEFAULT_MODEL

__all__ = [
    "Companion",
    "answer",
    "OllamaClient",
    "OllamaError",
    "DEFAULT_HOST",
    "DEFAULT_MODEL",
]
