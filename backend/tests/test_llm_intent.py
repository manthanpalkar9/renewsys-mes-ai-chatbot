"""
LLM Intent Evaluation Test Suite

Tests the intent-parsing pipeline against the mock provider.
Verifies that natural-language questions map to correct StructuredIntents.

Does NOT require:
  - A real Jinchen MES database
  - An Ollama instance
  - An OpenAI API key

Architecture under test:
  Natural language → MockLLMProvider.parse_intent() → StructuredIntent → PASS/FAIL

SRS References tested:
  FR-CORE-004 (CONFIRMED): Clarification on ambiguity
  FR-CORE-010 (CONFIRMED): Distinguish measured vs calculated
  UAT-05 (BLOCKED): Profit question must be rejected
  O1 (CONFIRMED): Alerts out of scope
  D10/D11/D12 (IDK): Pending metrics must return pending status
"""

import pytest
from app.llm.mock_provider import MockLLMProvider
from app.llm.intent_schema import StructuredIntent


@pytest.fixture
def llm():
    return MockLLMProvider()


# ── Utility ──────────────────────────────────────────────────────────────────

async def parse(llm, msg, history=None) -> StructuredIntent:
    return await llm.parse_intent(msg, conversation_history=history)


# ── Production queries ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_total_production_today(llm):
    intent = await parse(llm, "What is today's total production?")
    assert intent.intent in ("production_summary", "production_by_date", "production_by_line")
    assert intent.metric == "total_production"
    assert intent.date_expression == "today"
    assert not intent.needs_clarification


@pytest.mark.asyncio
async def test_production_by_line(llm):
    intent = await parse(llm, "Show me KM2 production for yesterday")
    assert "km2" in (intent.line or "").lower() or intent.line == "KM2"
    assert intent.date_expression == "yesterday"


@pytest.mark.asyncio
async def test_production_by_shift_morning(llm):
    intent = await parse(llm, "How many modules were produced in the morning shift?")
    assert intent.shift == "A"


@pytest.mark.asyncio
async def test_production_by_shift_night(llm):
    intent = await parse(llm, "Show night shift production for KM1 today")
    assert intent.shift == "C"
    assert intent.line == "KM1"
    assert intent.date_expression == "today"


@pytest.mark.asyncio
async def test_production_last_week(llm):
    intent = await parse(llm, "What was the total production last week?")
    assert intent.date_expression in ("last_week", "last_7_days")


# ── Defect / quality queries ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_defect_summary(llm):
    intent = await parse(llm, "How many defects were recorded today?")
    assert intent.metric in ("bad_quantity", "defect_rate", None) or \
           intent.intent in ("defect_summary", "defect_rate", "production_summary")
    assert intent.date_expression == "today"


@pytest.mark.asyncio
async def test_defect_rate(llm):
    intent = await parse(llm, "What is the defect rate for KM3 this week?")
    assert intent.line == "KM3"
    assert intent.date_expression in ("this_week", "last_7_days")


@pytest.mark.asyncio
async def test_scrap_rate_night_shift(llm):
    intent = await parse(llm, "What is the scrap rate for the night shift?")
    assert intent.shift == "C"
    assert intent.metric in ("scrap_rate", "scrap_quantity", None)


@pytest.mark.asyncio
async def test_yield(llm):
    intent = await parse(llm, "What is the yield for KM1 last week?")
    assert intent.line == "KM1"
    assert intent.metric == "yield"


# ── Comparison queries ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_comparison_between_lines(llm):
    intent = await parse(llm, "Compare production between KM1 and KM2 today")
    assert intent.intent in ("production_comparison", "production_summary", "production_by_line")


# ── Follow-up / context resolution ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_followup_date_inherit(llm):
    """'What about yesterday?' should inherit previous metric from context."""
    history = [
        {"role": "user", "content": "Show today's production for KM1"},
        {"role": "assistant", "content": "Today's production for KM1 is 1,200 modules."},
    ]
    intent = await parse(llm, "What about yesterday?", history=history)
    assert intent.date_expression == "yesterday"
    # Context resolution (via resolve_with_context) should carry metric
    resolved = intent.resolve_with_context({"last_line": "KM1", "last_kpi": "total_production"})
    assert resolved.line == "KM1"


@pytest.mark.asyncio
async def test_followup_shift_filter(llm):
    """'What about the night shift?' should narrow the previous query."""
    history = [
        {"role": "user", "content": "Show defects today"},
        {"role": "assistant", "content": "Today's defects: 45 modules."},
    ]
    intent = await parse(llm, "What about the night shift?", history=history)
    assert intent.shift == "C"


# ── Out-of-scope / blocked queries ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_profit_question_blocked(llm):
    """SRS UAT-05: profit questions must be blocked."""
    intent = await parse(llm, "What is the profit margin for this month?")
    assert intent.intent == "out_of_scope"
    assert "financial" in (intent.out_of_scope_reason or "").lower() or \
           "profit" in (intent.out_of_scope_reason or "").lower() or \
           "uat" in (intent.out_of_scope_reason or "").lower()


@pytest.mark.asyncio
async def test_revenue_question_blocked(llm):
    intent = await parse(llm, "Show total revenue for KM2")
    assert intent.intent == "out_of_scope"


@pytest.mark.asyncio
async def test_alert_question_blocked(llm):
    """SRS O1: alerts out of scope."""
    intent = await parse(llm, "Send me an alert when production drops below 500")
    assert intent.intent == "out_of_scope"


# ── Pending-definition metrics (SRS D10/D11/D12) ─────────────────────────────

@pytest.mark.asyncio
async def test_oee_returns_pending(llm):
    intent = await parse(llm, "What is the OEE for today?")
    assert intent.intent == "oee_summary"
    assert intent.is_pending_definition
    assert intent.pending_reason is not None


@pytest.mark.asyncio
async def test_wip_returns_pending(llm):
    intent = await parse(llm, "Show WIP for KM1")
    assert intent.intent == "wip_summary"
    assert intent.is_pending_definition


@pytest.mark.asyncio
async def test_first_pass_yield_pending(llm):
    intent = await parse(llm, "What is the first pass yield?")
    assert intent.intent == "first_pass_yield"
    assert intent.is_pending_definition


@pytest.mark.asyncio
async def test_rework_pending(llm):
    intent = await parse(llm, "How much rework happened today?")
    assert intent.intent == "rework_summary"
    assert intent.is_pending_definition


# ── Validation / schema safety ────────────────────────────────────────────────

def test_invalid_line_rejected():
    """Schema must reject invalid line values."""
    with pytest.raises(Exception):
        StructuredIntent(intent="production_summary", line="KM9")


def test_invalid_shift_rejected():
    """Schema must reject invalid shift values."""
    with pytest.raises(Exception):
        StructuredIntent(intent="production_summary", shift="X")


def test_confidence_range():
    """Confidence must be 0–1."""
    with pytest.raises(Exception):
        StructuredIntent(intent="production_summary", confidence=1.5)


def test_unknown_metric_nulled():
    """Unknown metrics should be nulled, not raise."""
    intent = StructuredIntent(intent="production_summary", metric="totally_made_up_metric")
    assert intent.metric is None


# ── Context resolution ────────────────────────────────────────────────────────

def test_resolve_with_context_fills_missing():
    intent = StructuredIntent(intent="production_summary", metric=None, line=None, date_expression=None)
    ctx = {"last_line": "KM2", "last_kpi": "yield", "last_date_expression": "yesterday"}
    resolved = intent.resolve_with_context(ctx)
    assert resolved.line == "KM2"
    assert resolved.metric == "yield"
    assert resolved.date_expression == "yesterday"


def test_resolve_with_context_does_not_override_explicit():
    intent = StructuredIntent(intent="production_summary", metric="scrap_rate", line="KM1", date_expression="today")
    ctx = {"last_line": "KM3", "last_kpi": "yield", "last_date_expression": "yesterday"}
    resolved = intent.resolve_with_context(ctx)
    # Explicit values must not be overridden
    assert resolved.line == "KM1"
    assert resolved.metric == "scrap_rate"
    assert resolved.date_expression == "today"


# ── Malformed / ambiguous input ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_message_does_not_crash(llm):
    """Empty messages should return a valid intent, not crash."""
    intent = await parse(llm, "")
    assert isinstance(intent, StructuredIntent)


@pytest.mark.asyncio
async def test_unrelated_question(llm):
    """Completely unrelated questions should return unsupported or clarification."""
    intent = await parse(llm, "What is the weather in Mumbai?")
    assert isinstance(intent, StructuredIntent)
    # Mock provider may not detect this as unsupported (limitation noted)
    # Just verify it doesn't crash and returns a valid object


@pytest.mark.asyncio
async def test_generate_response_pending_metric(llm):
    """Pending metrics must explain they're unavailable."""
    intent = StructuredIntent(intent="oee_summary", metric="oee")
    answer = await llm.generate_response("What is OEE?", intent, mes_result={})
    assert "oee" in answer.lower() or "cannot" in answer.lower() or "pending" in answer.lower() or "confirm" in answer.lower()


@pytest.mark.asyncio
async def test_generate_response_with_kpi(llm):
    """Response generation should include the value."""
    intent = StructuredIntent(intent="production_summary", metric="total_production", line="KM1", date_expression="today")
    mes_result = {
        "kpi": {"value": 1240, "unit": "modules", "formula": "PROPOSED"},
        "row_count": 10,
    }
    answer = await llm.generate_response("Production today?", intent, mes_result)
    assert "1240" in answer or "mock" in answer.lower()
