"""
Updated Mock LLM Provider

Now implements the new structured interface (parse_intent / generate_response).
Uses deterministic rule-based pattern matching — no AI required.
Fully backward compatible with existing orchestration.

SRS K1 (CONFIRMED): LLM not decided — mock for development.
SRS K2 (CONFIRMED): No external cloud AI.
"""

from __future__ import annotations
import json
import re
from typing import Optional
from app.llm.base import LLMProviderBase, LLMResponse
from app.llm.intent_schema import (
    StructuredIntent, ComparisonParams,
    PENDING_DEFINITION_INTENTS,
)
from loguru import logger


class MockLLMProvider(LLMProviderBase):
    PROVIDER_NAME = "MockLLMProvider"

    # ── Pattern dictionaries ─────────────────────────────────────────────────

    KPI_PATTERNS: dict[str, list[str]] = {
        "total_production":   [r"total production", r"production count", r"how many.*produced", r"modules produced"],
        "get_in_quantity":    [r"get.?in", r"getin", r"\bentered\b", r"entering"],
        "departure_quantity": [r"\bdeparture", r"left.*station", r"leaving"],
        "bad_quantity":       [r"\bbad\b", r"\bdefect\b", r"defective"],
        "scrap_quantity":     [r"\bscrap\b"],
        "first_pass_yield":   [r"first pass yield", r"\bfpy\b"],   # Must be BEFORE yield
        "yield":              [r"\byield\b"],
        "defect_rate":        [r"defect rate", r"defect ratio"],
        "scrap_rate":         [r"scrap rate"],
        "oee":                [r"\boee\b", r"overall equipment"],
        "downtime":           [r"\bdowntime\b"],
        "wip":                [r"\bwip\b", r"work.in.progress", r"in process"],
        "throughput":         [r"\bthroughput\b"],
        "rework_rate":        [r"\brework\b"],
        "process_loss":       [r"process loss"],
    }

    LINE_PATTERNS: dict[str, list[str]] = {
        "KM1": [r"\bkm1\b", r"line.?1\b", r"line one"],
        "KM2": [r"\bkm2\b", r"line.?2\b", r"line two"],
        "KM3": [r"\bkm3\b", r"line.?3\b", r"line three"],
    }

    SHIFT_PATTERNS: dict[str, list[str]] = {
        "A": [r"\bshift a\b", r"morning shift", r"\bmorning\b"],
        "B": [r"\bshift b\b", r"second shift", r"afternoon"],
        "C": [r"\bshift c\b", r"night shift", r"\bnight\b"],
    }

    DATE_PATTERNS: dict[str, list[str]] = {
        "today":          [r"\btoday\b"],
        "yesterday":      [r"\byesterday\b"],
        "current_shift":  [r"current shift", r"this shift"],
        "previous_shift": [r"previous shift", r"last shift"],
        "last_7_days":    [r"last 7 days", r"past 7 days"],
        "last_30_days":   [r"last 30 days", r"past 30 days"],
        "this_week":      [r"\bthis week\b"],
        "last_week":      [r"\blast week\b"],
        "this_month":     [r"\bthis month\b"],
        "last_month":     [r"\blast month\b"],
    }

    OUT_OF_SCOPE = re.compile(r"\b(profit|revenue|cost|margin|financial|earnings)\b")
    ALERTS = re.compile(r"\b(alert|notify|notification|alarm)\b")
    COMPARISON = re.compile(r"\b(compare|comparison|vs\.?|versus)\b")

    def _match(self, text: str, patterns: dict[str, list[str]]) -> Optional[str]:
        text = text.lower()
        for key, pats in patterns.items():
            for p in pats:
                if re.search(p, text):
                    return key
        return None

    # ── New primary interface ────────────────────────────────────────────────

    async def parse_intent(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> StructuredIntent:
        msg = user_message.lower()

        # Out of scope
        if self.OUT_OF_SCOPE.search(msg):
            return StructuredIntent(
                intent="out_of_scope",
                out_of_scope_reason="Financial data is not available in the MES (SRS UAT-05)",
                confidence=0.99,
            )
        if self.ALERTS.search(msg):
            return StructuredIntent(
                intent="out_of_scope",
                out_of_scope_reason="Proactive alerts are out of scope for Phase 1",
                confidence=0.99,
            )

        metric = self._match(user_message, self.KPI_PATTERNS)
        line = self._match(user_message, self.LINE_PATTERNS)
        shift = self._match(user_message, self.SHIFT_PATTERNS)
        date_expr = self._match(user_message, self.DATE_PATTERNS)
        is_comparison = bool(self.COMPARISON.search(msg))

        # Resolve intent
        if is_comparison:
            intent = "production_comparison"
        elif metric in ("oee", "wip", "downtime", "first_pass_yield", "rework_rate", "process_loss"):
            intent_map = {
                "oee": "oee_summary", "wip": "wip_summary",
                "downtime": "downtime_summary", "first_pass_yield": "first_pass_yield",
                "rework_rate": "rework_summary", "process_loss": "process_loss",
            }
            intent = intent_map[metric]
        elif metric in ("yield",):
            intent = "yield_summary"
        elif metric in ("defect_rate",):
            intent = "defect_rate"
        elif metric in ("scrap_rate",):
            intent = "scrap_rate"
        elif metric in ("bad_quantity",):
            intent = "defect_summary"
        elif metric in ("scrap_quantity",):
            intent = "scrap_summary"
        elif metric in ("departure_quantity",):
            intent = "departure_summary"
        elif metric in ("get_in_quantity",):
            intent = "getin_summary"
        elif metric in ("throughput",):
            intent = "throughput_summary"
        elif re.search(r"\b(production|produced|output|modules)\b", msg):
            if shift:
                intent = "production_by_shift"
            elif line:
                intent = "production_by_line"
            elif date_expr:
                intent = "production_by_date"
            else:
                intent = "production_summary"
        else:
            intent = "production_summary"

        # Clarification needed?
        needs_clarification = False
        clarification_reason = None
        if intent in ("production_summary", "defect_summary") and not date_expr:
            # If no date and no context, ask — but only for open-ended queries
            if not conversation_history:
                needs_clarification = True
                clarification_reason = "Please specify a time period (e.g., today, yesterday, this week)."

        comparison = None
        if is_comparison:
            comparison = ComparisonParams(line_a=line)

        return StructuredIntent(
            intent=intent,
            metric=metric or "total_production",
            line=line,
            shift=shift,
            date_expression=date_expr,
            comparison=comparison,
            needs_clarification=needs_clarification,
            clarification_reason=clarification_reason,
            confidence=0.80,
        )

    async def generate_response(
        self,
        question: str,
        intent: StructuredIntent,
        mes_result: dict,
    ) -> str:
        """Generate a natural-language response from structured MES result."""
        if intent.is_pending_definition:
            return (
                f"The metric '{intent.metric}' cannot be calculated yet. "
                f"Reason: {intent.pending_reason}"
            )

        kpi = mes_result.get("kpi")
        if kpi:
            value = kpi.get("value")
            unit = kpi.get("unit", "")
            kpi_name = intent.metric.replace("_", " ").title() if intent.metric else "Value"
            period = intent.date_expression or "today"
            scope_parts = []
            if intent.line:
                scope_parts.append(f"Line {intent.line}")
            if intent.shift:
                shift_names = {"A": "Morning", "B": "Second", "C": "Night"}
                scope_parts.append(f"{shift_names.get(intent.shift, intent.shift)} Shift")
            scope = ", ".join(scope_parts) if scope_parts else "all lines"

            if value is None:
                return f"{kpi_name} for {scope} ({period}): data is not available. {kpi.get('note', '')}"

            note = kpi.get("formula", "PROPOSED - REQUIRES BUSINESS VALIDATION")
            return (
                f"[MOCK DATA] {kpi_name} for {scope} ({period}): {value} {unit}. "
                f"Formula note: {note}."
            )

        row_count = mes_result.get("row_count", 0)
        if row_count == 0:
            return "No data was found for your query in the selected scope."
        return (
            f"[MOCK DATA] Found {row_count} records for your query. "
            f"Note: This is conceptual mock data — not actual Jinchen MES data."
        )

    def is_available(self) -> bool:
        return True

    # ── Legacy compat ────────────────────────────────────────────────────────

    async def classify_intent(self, user_message: str, context=None) -> LLMResponse:
        intent = await self.parse_intent(user_message, context)
        return LLMResponse(
            content=intent.model_dump_json(),
            provider=self.PROVIDER_NAME,
            is_mock=True,
        )

    async def generate_sql(
        self,
        question: str,
        schema_context: dict,
        date_context: dict,
        filters: Optional[dict] = None,
    ) -> LLMResponse:
        filters = filters or {}
        where_clauses = []
        if filters.get("line"):
            where_clauses.append(f"mock_line = '{filters['line']}'")
        if filters.get("shift"):
            where_clauses.append(f"mock_shift = '{filters['shift']}'")
        if date_context.get("date_from"):
            where_clauses.append(f"mock_date >= '{date_context['date_from']}'")
        if date_context.get("date_to"):
            where_clauses.append(f"mock_date <= '{date_context['date_to']}'")
        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = (
            f"SELECT mock_line, mock_shift, mock_area,\n"
            f"       SUM(mock_getin) AS total_getin,\n"
            f"       SUM(mock_departures) AS total_departures,\n"
            f"       SUM(mock_bad) AS total_bad,\n"
            f"       SUM(mock_scrap) AS total_scrap\n"
            f"FROM mock_production_events\n"
            f"{where_str}\n"
            f"GROUP BY mock_line, mock_shift, mock_area"
        )
        return LLMResponse(content=sql, provider=self.PROVIDER_NAME, is_mock=True)

    async def format_answer(self, question: str, query_result: dict, data_type: str) -> LLMResponse:
        answer = await self.generate_response(
            question,
            StructuredIntent(intent="production_summary", metric="total_production"),
            query_result,
        )
        return LLMResponse(content=answer, provider=self.PROVIDER_NAME, is_mock=True)


# ── Factory ──────────────────────────────────────────────────────────────────

def get_llm_provider(provider_type: str, **kwargs) -> LLMProviderBase:
    """
    Factory function for LLM providers.
    Selects provider based on LLM_PROVIDER env var.
    Default is 'mock' (safe, no network required).
    """
    from app.core.config import settings

    pt = (provider_type or "mock").lower()

    if pt == "mock":
        return MockLLMProvider()

    elif pt == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        return OllamaProvider(
            endpoint=kwargs.get("endpoint", settings.llm_endpoint),
            model=kwargs.get("model", settings.llm_model or "llama3"),
            timeout=kwargs.get("timeout", settings.llm_timeout_seconds),
        )

    elif pt == "openai":
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model=kwargs.get("model", settings.llm_model or "gpt-4o-mini"),
            timeout=kwargs.get("timeout", settings.llm_timeout_seconds),
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider_type}'. "
            f"Valid values: 'mock', 'ollama', 'openai'. "
            f"K2 (CONFIRMED): External cloud AI prohibited in production."
        )
