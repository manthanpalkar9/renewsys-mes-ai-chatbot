"""
Prompt Loader — loads prompt files from app/llm/prompts/

Separates prompts from code. Prompts are maintainable text files.
"""

from __future__ import annotations
import os
from functools import lru_cache

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


class PromptLoader:
    """Load and cache prompt files."""

    @lru_cache(maxsize=16)
    def _load(self, filename: str) -> str:
        path = os.path.join(PROMPT_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def intent_system(self) -> str:
        return self._load("intent_system.txt")

    def response_system(self) -> str:
        return self._load("response_system.txt")
