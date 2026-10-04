"""
LLM Provider Abstraction — Updated Base

All providers implement this interface.
The orchestration layer (chat_service) only calls methods on this base.

Two key methods drive the new architecture:
  1. parse_intent()   → returns StructuredIntent (validated)
  2. generate_response() → returns natural-language string from structured data

SRS K2 (CONFIRMED): No external cloud AI in production.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from app.llm.intent_schema import StructuredIntent


@dataclass
class LLMResponse:
    """Raw response from an LLM provider (before parsing)."""
    content: str
    model_used: Optional[str] = None
    provider: str = "unknown"
    is_mock: bool = False
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None


class LLMProviderBase(ABC):
    """
    Abstract LLM provider.

    CONSTRAINT (K2: CONFIRMED): MUST NEVER send MES/company data
    to an external cloud AI service in production.
    """

    CLOUD_PROHIBITION_NOTE = (
        "K2 (CONFIRMED): Production AI processing shall not send MES/company data "
        "to an external cloud AI service unless explicitly approved."
    )

    # ── New primary interface (structured) ──────────────────────────────────

    @abstractmethod
    async def parse_intent(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> StructuredIntent:
        """
        Convert natural language to a validated StructuredIntent.
        Must raise ValueError if parsing fails after retries.
        Must NEVER return unvalidated output to the caller.
        """
        ...

    @abstractmethod
    async def generate_response(
        self,
        question: str,
        intent: StructuredIntent,
        mes_result: dict,
    ) -> str:
        """
        Generate a natural-language answer from structured MES data.
        Must use ONLY the provided mes_result — never invent values.
        """
        ...

    # ── Availability ────────────────────────────────────────────────────────

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is reachable."""
        ...

    # ── Legacy interface (kept for backward compatibility) ──────────────────

    async def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        raise NotImplementedError

    async def classify_intent(
        self, user_message: str, context: Optional[list] = None
    ) -> LLMResponse:
        raise NotImplementedError

    async def interpret_question(
        self, question: str, schema_context: dict, session_context: Optional[list] = None
    ) -> LLMResponse:
        raise NotImplementedError

    async def generate_sql(
        self,
        question: str,
        schema_context: dict,
        date_context: dict,
        filters: Optional[dict] = None,
    ) -> LLMResponse:
        raise NotImplementedError

    async def format_answer(
        self, question: str, query_result: dict, data_type: str
    ) -> LLMResponse:
        raise NotImplementedError
