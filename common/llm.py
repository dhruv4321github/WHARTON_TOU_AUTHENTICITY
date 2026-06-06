"""
Shared LLM client abstraction.

A single thin seam between our analysis code and whichever provider/model is in
use. Both Part 1 (theme tagging) and Part 2 (tone/commitment coding) talk to the
model only through `LLMClient`, so changing provider or model is a one-class edit
that never touches analysis logic.

Default provider: OpenAI. Reads OPENAI_API_KEY from the environment and the model
from OPENAI_MODEL (fallback gpt-4o-mini). The import of `openai` is lazy so that
the data-collection steps, which need no model, don't require the package or a key.
"""

from __future__ import annotations

import json
import os
from typing import Protocol


class LLMClient(Protocol):
    """Anything that turns (system, user) prompts into a parsed JSON dict."""
    model: str
    def complete_json(self, system: str, user: str) -> dict: ...


class OpenAIClient:
    """OpenAI-backed client using Chat Completions JSON mode."""

    def __init__(self, model: str | None = None, temperature: float = 0.0):
        from openai import OpenAI  # lazy: only needed for the LLM passes
        self.client = OpenAI()      # picks up OPENAI_API_KEY from env
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature

    def complete_json(self, system: str, user: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp.choices[0].message.content)
