"""
OpenAI LLM Provider

⚠️  SRS K2 (CONFIRMED): MES/company production data MUST NOT be sent to
external cloud AI services in production without explicit approval.

This provider is provided for:
  - Development/testing against non-production data
  - Future use if K2 is formally relaxed and approved by stakeholders

API key is NEVER hard-coded. It comes ONLY from OPENAI_API_KEY env var.
The key is NEVER logged, NEVER sent to the frontend.

Configuration:
  LLM_PROVIDER=openai
  OPENAI_API_KEY=sk-...        (set as environment variable / .env file)
  LLM_MODEL=gpt-4o-mini        (or gpt-4o, etc.)
"""

from __future__ import annotations
import json
import os
from typing import Optional
from loguru import logger
from app.llm.base import LLMProviderBase, LLMResponse
from app.llm.intent_schema import StructuredIntent
from app.llm.prompt_loader import PromptLoader


class OpenAIProvider(LLMProviderBase):
    PROVIDER_NAME = "OpenAIProvider"
    MAX_RETRIES = 2
    K2_WARNING = (
        "⚠️  K2 WARNING: OpenAI is an external cloud AI provider. "
        "Ensure company policy permits sending this data externally before using in production."
    )

    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 60):
        self.model = model
        self.timeout = timeout
        self._prompts = PromptLoader()
        self._client = None  # Lazy init

    def _get_client(self):
        """Lazy-initialize OpenAI client. Fails fast if key not set."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                )
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY environment variable is not set. "
                    "Set it in your .env file. NEVER hard-code API keys."
                )
            self._client = AsyncOpenAI(api_key=api_key, timeout=self.timeout)
        return self._client

    def is_available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    # ── Intent parsing ───────────────────────────────────────────────────────

    async def parse_intent(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> StructuredIntent:
        logger.warning(self.K2_WARNING)

        client = self._get_client()
        system_prompt = self._prompts.intent_system()
        messages = [{"role": "system", "content": system_prompt}]

        # Add bounded conversation context (max 6 messages)
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = msg.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({
                        "role": role,
                        "content": str(msg.get("content", ""))[:500],
                    })

        messages.append({"role": "user", "content": user_message})

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw = response.choices[0].message.content or ""
                return self._parse_and_validate(raw, user_message)
            except (ValueError, Exception) as e:
                last_error = e
                logger.warning(
                    "OpenAI intent parse attempt {}/{} failed: {}",
                    attempt, self.MAX_RETRIES, type(e).__name__
                )
                if attempt < self.MAX_RETRIES:
                    messages.append({
                        "role": "user",
                        "content": "Please return ONLY valid JSON matching the schema. No prose.",
                    })

        raise ValueError(
            f"OpenAI failed to return valid structured intent after "
            f"{self.MAX_RETRIES} attempts: {last_error}"
        )

    # ── Response generation ──────────────────────────────────────────────────

    async def generate_response(
        self,
        question: str,
        intent: StructuredIntent,
        mes_result: dict,
    ) -> str:
        logger.warning(self.K2_WARNING)
        client = self._get_client()
        system_prompt = self._prompts.response_system()
        user_prompt = (
            f"User asked: {question}\n\n"
            f"MES data result:\n{json.dumps(mes_result, default=str, indent=2)}\n\n"
            f"Intent: {intent.model_dump_json()}\n\n"
            "Generate a concise natural-language response."
        )
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    # ── Validation helper ────────────────────────────────────────────────────

    def _parse_and_validate(self, raw: str, original_message: str) -> StructuredIntent:
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"OpenAI returned invalid JSON: {e}")
        try:
            return StructuredIntent(**data)
        except Exception as e:
            raise ValueError(f"OpenAI output failed schema validation: {e}")

    # ── Legacy compat ────────────────────────────────────────────────────────

    async def classify_intent(self, user_message: str, context=None) -> LLMResponse:
        intent = await self.parse_intent(user_message, context)
        return LLMResponse(content=intent.model_dump_json(), provider=self.PROVIDER_NAME)
