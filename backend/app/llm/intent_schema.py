"""
Structured Intent Schema

This is the validated Pydantic model that ALL LLM providers must produce.
The orchestration layer (chat_service) ONLY accepts StructuredIntent objects —
it never consumes raw LLM text directly.

Architecture: LLM → raw JSON string → parse+validate here → StructuredIntent
              → chat_service uses StructuredIntent → MES adapter

If validation fails, the orchestration layer returns a controlled error.
The MES adapter is NEVER called with unvalidated LLM output.
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


# ── Valid domain values ─────────────────────────────────────────────────────

LINE_VALUES = {"KM1", "KM2", "KM3"}
SHIFT_VALUES = {"A", "B", "C"}
DATE_EXPRESSIONS = {
    "today", "yesterday", "current_shift", "previous_shift",
    "this_week", "last_week", "last_7_days", "last_30_days",
    "this_month", "last_month",
}

# Intents that require data from the MES adapter
DATA_INTENTS = {
    "production_summary", "production_by_date", "production_by_shift",
    "production_by_line", "production_comparison",
    "defect_summary", "defect_rate", "scrap_summary", "scrap_rate",
    "yield_summary", "departure_summary", "getin_summary", "throughput_summary",
    "oee_summary", "wip_summary", "downtime_summary",
    "first_pass_yield", "rework_summary", "process_loss",
}

# Intents that are pending business-rule clarification (SRS open items)
PENDING_DEFINITION_INTENTS = {
    "oee_summary": "OEE data source not yet confirmed (Section 14.2)",
    "wip_summary": "WIP quantity semantics undefined (D10: IDK)",
    "downtime_summary": "Downtime event log source unconfirmed",
    "first_pass_yield": "First Pass Yield depends on rework definition (D12: IDK)",
    "rework_summary": "Rework definition unresolved (D12: IDK)",
    "process_loss": "Process loss definition unresolved (D11: IDK)",
}

SUPPORTED_METRICS = {
    "total_production", "get_in_quantity", "departure_quantity",
    "bad_quantity", "scrap_quantity", "yield", "defect_rate", "scrap_rate",
    "oee", "wip", "downtime", "throughput", "first_pass_yield",
    "rework_rate", "process_loss", "availability", "cycle_time",
}


class ComparisonParams(BaseModel):
    """Parameters for a comparison query."""
    period_a: Optional[str] = None
    period_b: Optional[str] = None
    line_a: Optional[str] = None
    line_b: Optional[str] = None
    shift_a: Optional[str] = None
    shift_b: Optional[str] = None


IntentType = Literal[
    "production_summary", "production_by_date", "production_by_shift",
    "production_by_line", "production_comparison",
    "defect_summary", "defect_rate", "scrap_summary", "scrap_rate",
    "yield_summary", "departure_summary", "getin_summary", "throughput_summary",
    "oee_summary", "wip_summary", "downtime_summary",
    "first_pass_yield", "rework_summary", "process_loss",
    "out_of_scope", "unsupported", "clarification_needed",
]


class StructuredIntent(BaseModel):
    """
    Validated representation of a user's intent.

    This is the ONLY object the chat_service accepts from the LLM layer.
    All fields are validated here before any MES adapter is called.
    """
    intent: IntentType
    metric: Optional[str] = None
    line: Optional[str] = None
    shift: Optional[str] = None
    date_expression: Optional[str] = None
    comparison: Optional[ComparisonParams] = None
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    out_of_scope_reason: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_domain_values(self) -> "StructuredIntent":
        if self.line and self.line not in LINE_VALUES:
            raise ValueError(f"Invalid line: {self.line!r}. Must be one of {LINE_VALUES}")
        if self.shift and self.shift not in SHIFT_VALUES:
            raise ValueError(f"Invalid shift: {self.shift!r}. Must be one of {SHIFT_VALUES}")
        if self.metric and self.metric not in SUPPORTED_METRICS:
            # Don't hard-fail — just null it out to be safe
            self.metric = None
        return self

    @property
    def is_data_intent(self) -> bool:
        return self.intent in DATA_INTENTS

    @property
    def is_pending_definition(self) -> bool:
        return self.intent in PENDING_DEFINITION_INTENTS

    @property
    def pending_reason(self) -> Optional[str]:
        return PENDING_DEFINITION_INTENTS.get(self.intent)

    @property
    def is_out_of_scope(self) -> bool:
        return self.intent in ("out_of_scope", "unsupported")

    def resolve_with_context(self, ctx: dict) -> "StructuredIntent":
        """
        Fill in missing fields from session context (for follow-up questions).
        Returns a new instance with inherited values. Does not mutate self.
        """
        data = self.model_dump()
        if not data["line"] and ctx.get("last_line"):
            data["line"] = ctx["last_line"]
        if not data["shift"] and ctx.get("last_shift"):
            data["shift"] = ctx["last_shift"]
        if not data["date_expression"] and ctx.get("last_date_expression"):
            data["date_expression"] = ctx["last_date_expression"]
        if not data["metric"] and ctx.get("last_kpi"):
            data["metric"] = ctx["last_kpi"]
        return StructuredIntent(**data)
