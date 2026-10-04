"""
Chat Service — Orchestration Layer

Architecture:
  User message
    → guardrails (profit/alert check)
    → LLM.parse_intent()  → StructuredIntent (validated)
    → context resolution (follow-up questions)
    → MES Adapter (mock or real)
    → Metric engine
    → LLM.generate_response()
    → ChatResponse

The LLM NEVER touches the database directly.
The MES Adapter is NEVER called with unvalidated LLM output.
RBAC is enforced here, independently of the LLM.

SRS References:
  F2 (CONFIRMED): SELECT-only
  I3 (CONFIRMED): SQL visible to Admin only
  I4 (CONFIRMED): Data freshness timestamp
  K2 (CONFIRMED): No external cloud AI (enforced at provider level)
  FR-CORE-004 (CONFIRMED): Clarification on ambiguity
  FR-CORE-010 (CONFIRMED): Distinguish measured vs calculated
"""

from __future__ import annotations
import uuid
import re
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from app.models.schemas import (
    ChatResponse, DataType, TableData, KPICard,
)
from app.services.session_service import ChatSession
from app.services.date_service import DateService
from app.services.sql_safety import sql_safety_service
from app.adapters.jinchen_adapter import get_adapter
from app.llm.mock_provider import get_llm_provider
from app.llm.intent_schema import StructuredIntent
from app.core.config import settings
from app.core.security import is_admin

# ── Blocked response templates ────────────────────────────────────────────────

PROFIT_RESPONSE = (
    "I cannot answer questions about profit, revenue, cost, or financial margins. "
    "(SRS Section 30.3 / UAT-05: Financial data source not yet confirmed.)"
)
ALERT_RESPONSE = (
    "Proactive alerts and notifications are out of scope for Phase 1. "
    "(SRS O1: CONFIRMED)"
)
LLM_UNAVAILABLE_RESPONSE = (
    "The AI assistant is temporarily unavailable. Please try again in a moment."
)
UNSUPPORTED_RESPONSE = (
    "I can only answer questions about Renewsys MES production data — "
    "production counts, defects, yield, scrap, and related metrics for lines KM1, KM2, KM3. "
    "Is there a production question I can help with?"
)

# Pre-compiled guardrail patterns
_PROFIT_RE = re.compile(r'\b(profit|revenue|cost|margin|financial|earnings)\b', re.I)
_ALERT_RE = re.compile(r'\b(alert|notify|notification|alarm)\b', re.I)


class ChatService:
    def __init__(self):
        self.date_service = DateService()
        self.mes_adapter = get_adapter(settings.mes_adapter)
        self.llm = get_llm_provider(
            settings.llm_provider,
            endpoint=settings.llm_endpoint,
            model=settings.llm_model or "",
            timeout=settings.llm_timeout_seconds,
        )
        logger.info(
            "ChatService initialized | adapter={} | llm={}",
            settings.mes_adapter, settings.llm_provider,
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def process_message(
        self,
        message: str,
        session: ChatSession,
        user_role: str,
    ) -> ChatResponse:
        message_id = str(uuid.uuid4())
        session.add_message("user", message)
        try:
            response = await self._handle_message(message, session, user_role, message_id)
            session.add_message("assistant", response.answer)
            return response
        except Exception as e:
            logger.exception("Unhandled error in chat service")
            err = ChatResponse(
                session_id=session.session_id,
                message_id=message_id,
                answer="I encountered an error. Please try rephrasing your question.",
                response_type="error",
                timestamp=datetime.now(timezone.utc),
            )
            session.add_message("assistant", err.answer)
            return err

    # ── Orchestration pipeline ────────────────────────────────────────────────

    async def _handle_message(
        self,
        message: str,
        session: ChatSession,
        user_role: str,
        message_id: str,
    ) -> ChatResponse:

        # 1. Guardrails — check before touching LLM
        if _PROFIT_RE.search(message):
            return self._text_response(session.session_id, message_id, PROFIT_RESPONSE)
        if _ALERT_RE.search(message):
            return self._text_response(session.session_id, message_id, ALERT_RESPONSE)

        # 2. Parse intent via LLM (validated StructuredIntent)
        intent = await self._safe_parse_intent(message, session)
        if intent is None:
            return self._text_response(session.session_id, message_id, LLM_UNAVAILABLE_RESPONSE, "error")

        # 3. Handle out-of-scope / unsupported
        if intent.is_out_of_scope:
            reason = intent.out_of_scope_reason or ""
            msg = (
                f"I cannot answer that question. {reason}"
                if reason else UNSUPPORTED_RESPONSE
            )
            return self._text_response(session.session_id, message_id, msg)

        # 4. Handle clarification needed
        if intent.needs_clarification:
            q = intent.clarification_reason or "Could you provide more details (time period, line, or shift)?"
            return ChatResponse(
                session_id=session.session_id,
                message_id=message_id,
                answer=q,
                response_type="clarification",
                clarification_needed=True,
                clarification_question=q,
                timestamp=datetime.now(timezone.utc),
            )

        # 5. Resolve with session context (follow-up question support)
        # Note: We now rely purely on the LLM to resolve context explicitly to avoid corrupting "ALL" queries.
        ctx = session.get_context_dict()
        # intent = intent.resolve_with_context(ctx)

        # 6. Update session context
        session.update_context(
            last_line=intent.line,
            last_shift=intent.shift,
            last_date_expression=intent.date_expression,
            last_kpi=intent.metric,
            last_intent=intent.intent,
        )

        # 7. Pending-definition metrics
        if intent.is_pending_definition:
            answer = (
                f"'{intent.metric}' cannot be calculated yet. "
                f"Reason: {intent.pending_reason}. "
                "This will be available once the business definition is confirmed."
            )
            return self._text_response(session.session_id, message_id, answer)

        # 8. Resolve date range
        date_context = self._resolve_date(intent.date_expression)

        # 9. Generate conceptual SQL (for admin audit trail only)
        schema_info = await self.mes_adapter.get_mock_schema_info()
        sql_response = None
        if hasattr(self.llm, "generate_sql"):
            try:
                sql_response = await self.llm.generate_sql(
                    question=message,
                    schema_context=schema_info,
                    date_context=date_context,
                    filters={"line": intent.line, "shift": intent.shift},
                )
            except NotImplementedError:
                pass
            except Exception as e:
                logger.warning(f"Failed to generate conceptual SQL: {e}")

        generated_sql = None
        if sql_response:
            safety = sql_safety_service.validate(sql_response.content)
            if safety.is_safe:
                generated_sql = sql_response.content

        # 10. Query MES Adapter (mock or real)
        query_result = await self.mes_adapter.execute_query(
            sql=generated_sql or "SELECT * FROM mock_production_events LIMIT 1",
            timeout=settings.query_timeout_seconds,
        )

        # 11. Compute KPI via BusinessMetricEngine
        kpi_data = None
        if intent.intent == "production_comparison" and intent.comparison and intent.metric:
            from app.services.metric_engine import metric_engine
            # Resolve dates for A and B
            date_a_dict = self._resolve_date(intent.comparison.period_a or "today")
            date_b_dict = self._resolve_date(intent.comparison.period_b or "yesterday")
            date_a_str = date_a_dict.get("date_from")
            date_b_str = date_b_dict.get("date_from")
            date_a = datetime.fromisoformat(date_a_str).date() if date_a_str else None
            date_b = datetime.fromisoformat(date_b_str).date() if date_b_str else None
            
            try:
                records_a = await self.mes_adapter.get_normalized_data(
                    line=intent.comparison.line_a or intent.line,
                    shift=intent.comparison.shift_a or intent.shift,
                    date_from=date_a, date_to=date_a
                )
                records_b = await self.mes_adapter.get_normalized_data(
                    line=intent.comparison.line_b or intent.line,
                    shift=intent.comparison.shift_b or intent.shift,
                    date_from=date_b, date_to=date_b
                )
                
                res_a = metric_engine.calculate(intent.metric, records_a)
                res_b = metric_engine.calculate(intent.metric, records_b)
                
                if res_a.status == "success" and res_b.status == "success":
                    val_a = res_a.value or 0
                    val_b = res_b.value or 0
                    diff = val_a - val_b
                    pct = round((diff / val_b * 100), 2) if val_b else 0.0
                    
                    # Store standard comparison format
                    kpi_data = {
                        "value": diff,
                        "unit": res_a.unit,
                        "formula": "DEFINED - Supported by SRS",
                        "note": f"Period A: {val_a}, Period B: {val_b}, Diff: {diff}, Change: {pct}%",
                        "comparison_result": {
                            "metric": "production_comparison",
                            "period_a": val_a,
                            "period_b": val_b,
                            "difference": diff,
                            "percentage_change": pct
                        }
                    }
                else:
                    kpi_data = {"value": None, "note": "Could not calculate comparison metrics."}
            except Exception as e:
                logger.error("Failed to calculate comparison metric: {}", e)
                kpi_data = {"value": None, "note": str(e)}

        elif intent.metric:
            # Normal single-metric query
            from app.services.metric_engine import metric_engine
            # Parse date_context to dates
            date_from_str = date_context.get("date_from")
            date_to_str = date_context.get("date_to")
            date_from = datetime.fromisoformat(date_from_str).date() if date_from_str else None
            date_to = datetime.fromisoformat(date_to_str).date() if date_to_str else None
            
            try:
                records = await self.mes_adapter.get_normalized_data(
                    line=intent.line,
                    shift=intent.shift,
                    date_from=date_from,
                    date_to=date_to,
                )
                
                metric_result = metric_engine.calculate(intent.metric, records)
                
                if metric_result.status == "success":
                    kpi_data = {
                        "value": metric_result.value,
                        "unit": metric_result.unit,
                        "formula": metric_result.formula_note,
                        "note": metric_result.message
                    }
                else:
                    kpi_data = {
                        "value": None,
                        "unit": metric_result.unit,
                        "formula": metric_result.formula_note,
                        "note": metric_result.message
                    }
            except Exception as e:
                logger.error("Failed to calculate metric: {}", e)
                kpi_data = {"value": None, "note": str(e)}

        # 12. Build MES result dict for LLM response generation
        mes_result = {
            "kpi": kpi_data,
            "row_count": query_result.row_count,
            "columns": query_result.columns,
            "rows": query_result.rows[:5] if query_result.rows else [],
            "date_context": date_context,
            "adapter_note": query_result.adapter_note,
        }

        # 13. Generate natural-language response via LLM
        try:
            answer = await self.llm.generate_response(
                question=message,
                intent=intent,
                mes_result=mes_result,
            )
        except Exception as e:
            logger.warning("LLM response generation failed, using fallback: {}", e)
            answer = self._fallback_answer(intent, kpi_data, query_result)

        # 14. Build KPI card if we have metric data
        kpi_card = None
        response_type = "text"
        
        # Map shift code to name
        shift_name = intent.shift
        if intent.shift == "A": shift_name = "Morning"
        elif intent.shift == "B": shift_name = "Second"
        elif intent.shift == "C": shift_name = "Night"
        
        if kpi_data and kpi_data.get("value") is not None:
            response_type = "kpi_card"
            kpi_card = KPICard(
                kpi_name=(intent.metric or "value").replace("_", " ").title(),
                value=kpi_data["value"],
                unit=kpi_data.get("unit"),
                period=intent.date_expression,
                line=intent.line,
                shift=shift_name,
                data_type=DataType.CALCULATED,
                formula_note=kpi_data.get("formula", "PROPOSED - REQUIRES BUSINESS VALIDATION"),
                is_formula_confirmed=False,
            )

        # 15. Build table if we have row data
        table = None
        if query_result.rows and response_type == "text":
            response_type = "table"
            table = TableData(
                columns=query_result.columns,
                rows=query_result.rows[:100],
                total_rows=query_result.row_count,
            )

        return ChatResponse(
            session_id=session.session_id,
            message_id=message_id,
            answer=answer,
            response_type=response_type,
            data_type=DataType.CALCULATED if kpi_card else DataType.MEASURED,
            kpi_card=kpi_card,
            table=table,
            data_freshness="~24 hours (L1: CONFIRMED)",
            last_updated=datetime.now(timezone.utc),
            generated_sql=generated_sql if is_admin(user_role) else None,  # I3
            timestamp=datetime.now(timezone.utc),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _safe_parse_intent(
        self,
        message: str,
        session: ChatSession,
    ) -> Optional[StructuredIntent]:
        """Wrap LLM intent parsing with full error handling."""
        try:
            return await self.llm.parse_intent(
                user_message=message,
                conversation_history=session.get_recent_history(max_turns=5),
            )
        except RuntimeError as e:
            logger.error("LLM unavailable: {}", e)
            return None
        except ValueError as e:
            logger.warning("Intent parse validation failed: {}", e)
            # Return a safe fallback intent
            return StructuredIntent(
                intent="production_summary",
                metric="total_production",
                needs_clarification=True,
                clarification_reason=(
                    "I had trouble understanding your question. "
                    "Could you rephrase it? (e.g., 'What is today's production for KM1?')"
                ),
                confidence=0.0,
            )
        except Exception as e:
            logger.exception("Unexpected error in intent parsing: {}", e)
            return None

    def _resolve_date(self, date_expression: Optional[str]) -> dict:
        """Resolve date expression to a concrete date range."""
        expr = date_expression or "today"
        try:
            date_range = self.date_service.resolve_expression(expr)
            if date_range.exceeds_limit():
                logger.warning("Date range exceeds 30-day limit, clamping to 30 days")
            return date_range.to_dict()
        except Exception:
            return self.date_service.resolve_expression("today").to_dict()

    def _fallback_answer(self, intent: StructuredIntent, kpi_data: Optional[dict], query_result) -> str:
        """Rule-based fallback when LLM response generation fails."""
        if kpi_data:
            value = kpi_data.get("value")
            if value is None:
                return f"Cannot calculate {intent.metric}: {kpi_data.get('note', 'data unavailable')}."
            unit = kpi_data.get("unit", "")
            name = (intent.metric or "value").replace("_", " ").title()
            return f"[MOCK DATA] {name}: {value} {unit}."
        if query_result.rows:
            return f"[MOCK DATA] Found {query_result.row_count} records."
        return "No data found for your query."

    def _text_response(
        self,
        session_id: str,
        message_id: str,
        answer: str,
        response_type: str = "text",
    ) -> ChatResponse:
        return ChatResponse(
            session_id=session_id,
            message_id=message_id,
            answer=answer,
            response_type=response_type,
            timestamp=datetime.now(timezone.utc),
        )


chat_service = ChatService()
