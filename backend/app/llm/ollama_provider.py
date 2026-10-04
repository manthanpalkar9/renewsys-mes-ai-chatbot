"""
Ollama LLM Provider

Connects to a locally-deployed Ollama instance.
K2 (CONFIRMED): Data stays in-network — Ollama runs on-premises.

Configuration:
  LLM_PROVIDER=ollama
  LLM_ENDPOINT=http://localhost:11434   (or wherever Ollama is running)
  LLM_MODEL=llama3                      (or any model you have pulled)

Setup:
  1. Install Ollama: https://ollama.com
  2. Pull a model: ollama pull llama3
  3. Set the env vars above
  4. Restart the backend
"""

from __future__ import annotations
import json
import httpx
from typing import Optional
from loguru import logger
from app.llm.base import LLMProviderBase, LLMResponse
from app.llm.intent_schema import StructuredIntent
from app.llm.prompt_loader import PromptLoader


class OllamaProvider(LLMProviderBase):
    PROVIDER_NAME = "OllamaProvider"
    MAX_RETRIES = 2

    def __init__(self, endpoint: str, model: str, timeout: int = 60):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._prompts = PromptLoader()

    # ── Availability check ───────────────────────────────────────────────────

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.endpoint}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # ── Core API call ────────────────────────────────────────────────────────

    async def _chat(self, system: str, user: str) -> str:
        """Call Ollama's /api/chat endpoint."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.endpoint}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    # ── Intent parsing ───────────────────────────────────────────────────────

    async def parse_intent(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> StructuredIntent:
        if not self.is_available():
            raise RuntimeError(
                f"Ollama is not available at {self.endpoint}. "
                "Check that Ollama is running and LLM_ENDPOINT is correct."
            )

        system_prompt = self._prompts.intent_system()
        context_block = self._build_context_block(conversation_history)
        user_prompt = f"{context_block}\nUser question: {user_message}"

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                raw = await self._chat(system=system_prompt, user=user_prompt)
                return self._parse_and_validate(raw, user_message)
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(
                    "Ollama intent parse attempt {}/{} failed: {}",
                    attempt, self.MAX_RETRIES, e
                )
                if attempt < self.MAX_RETRIES:
                    user_prompt = (
                        f"{user_prompt}\n\n"
                        "IMPORTANT: Return ONLY valid JSON matching the schema. "
                        "No markdown, no prose."
                    )

        raise ValueError(
            f"Ollama failed to return valid structured intent after "
            f"{self.MAX_RETRIES} attempts: {last_error}"
        )

    # ── Response generation ──────────────────────────────────────────────────

    async def generate_response(
        self,
        question: str,
        intent: StructuredIntent,
        mes_result: dict,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Ollama not available")

        system_prompt = self._prompts.response_system()
        user_prompt = (
            f"User asked: {question}\n\n"
            f"MES data result:\n{json.dumps(mes_result, default=str, indent=2)}\n\n"
            f"Intent details: {intent.model_dump_json()}\n\n"
            "Please generate a concise natural-language response."
        )
        try:
            # For response generation, don't use JSON format mode
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.endpoint}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"].strip()
        except Exception as e:
            logger.error("Ollama response generation failed: {}", e)
            raise

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_context_block(self, history: Optional[list[dict]]) -> str:
        if not history:
            return ""
        recent = history[-6:]  # Last 3 turns
        lines = ["Recent conversation:"]
        for msg in recent:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")[:200]
            lines.append(f"  {role}: {content}")
        return "\n".join(lines)

    def _parse_and_validate(self, raw: str, original_message: str) -> StructuredIntent:
        """Parse raw LLM output and validate as StructuredIntent."""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}. Raw: {raw[:200]}")

        try:
            intent = StructuredIntent(**data)
        except Exception as e:
            raise ValueError(f"LLM output failed schema validation: {e}. Data: {data}")

        return intent

    # ── Legacy compat ────────────────────────────────────────────────────────

    async def classify_intent(self, user_message: str, context=None) -> LLMResponse:
        intent = await self.parse_intent(user_message, context)
        return LLMResponse(
            content=intent.model_dump_json(),
            provider=self.PROVIDER_NAME,
        )
