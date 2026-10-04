import pytest
from app.services.chat_service import chat_service
from app.services.session_service import session_manager
from app.llm.intent_schema import StructuredIntent
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm(monkeypatch):
    mock = AsyncMock()
    class StubResponse:
        content = "SELECT 1"
    async def mock_generate_sql(*args, **kwargs):
        return StubResponse()
    async def mock_generate_response(*args, **kwargs):
        return "Mock response"
    mock.generate_sql = mock_generate_sql
    mock.generate_response = mock_generate_response
    monkeypatch.setattr(chat_service, "llm", mock)
    chat_service.llm.parse_intent = mock
    return mock

@pytest.mark.asyncio
async def test_e2e_context_override(mock_llm):
    session = session_manager.create_session(1, "admin", "admin")
    mock_llm.return_value = StructuredIntent(
        intent="production_summary", metric="total_production",
        line="KM1", shift="C", date_expression="yesterday"
    )
    res1 = await chat_service._handle_message("How much did KM1 night shift produce yesterday?", session, "admin", "msg1")
    
    mock_llm.return_value = StructuredIntent(
        intent="unsupported", out_of_scope_reason="Ranking not supported"
    )
    res2 = await chat_service._handle_message("Which shift produced the most?", session, "admin", "msg2")
    assert res2.response_type == "text"
    assert "Ranking not supported" in res2.answer

@pytest.mark.asyncio
async def test_e2e_date_override(mock_llm):
    session = session_manager.create_session(1, "admin", "admin")
    mock_llm.return_value = StructuredIntent(
        intent="production_summary", metric="total_production", date_expression="yesterday"
    )
    res1 = await chat_service._handle_message("What was yesterday's production?", session, "admin", "msg1")
    
    mock_llm.return_value = StructuredIntent(
        intent="production_summary", metric="total_production", date_expression="today"
    )
    res2 = await chat_service._handle_message("What about today?", session, "admin", "msg2")
    assert res2.kpi_card.period == "today"

@pytest.mark.asyncio
async def test_e2e_explicit_date_parsing(mock_llm):
    session = session_manager.create_session(1, "admin", "admin")
    mock_llm.return_value = StructuredIntent(
        intent="defect_summary", metric="bad_quantity", date_expression="September 28"
    )
    res1 = await chat_service._handle_message("How many modules were rejected on September 28?", session, "admin", "msg1")
    assert res1.kpi_card.period == "September 28"

@pytest.mark.asyncio
async def test_adversarial_context_switching(mock_llm):
    session = session_manager.create_session(1, "admin", "admin")
    
    # 1. How much did KM1 produce yesterday?
    mock_llm.return_value = StructuredIntent(intent="production_summary", metric="total_production", line="KM1", date_expression="yesterday")
    res = await chat_service._handle_message("How much did KM1 produce yesterday?", session, "admin", "msg1")
    assert res.kpi_card.line == "KM1"
    
    # 2. What about the night shift? (inherits KM1, yesterday, adds Night shift)
    mock_llm.return_value = StructuredIntent(intent="production_summary", metric="total_production", line="KM1", shift="C", date_expression="yesterday")
    res = await chat_service._handle_message("What about the night shift?", session, "admin", "msg2")
    assert res.kpi_card.shift == "Night"
    assert res.kpi_card.line == "KM1"
    
    # 3. What about today? (inherits KM1, Night shift, changes date to today)
    mock_llm.return_value = StructuredIntent(intent="production_summary", metric="total_production", line="KM1", shift="C", date_expression="today")
    res = await chat_service._handle_message("What about today?", session, "admin", "msg3")
    assert res.kpi_card.period == "today"
    
    # 4. How many were rejected? (inherits KM1, Night, today, changes metric to bad_quantity)
    mock_llm.return_value = StructuredIntent(intent="defect_summary", metric="bad_quantity", line="KM1", shift="C", date_expression="today")
    res = await chat_service._handle_message("How many were rejected?", session, "admin", "msg4")
    assert res.kpi_card.kpi_name == "Bad Quantity"
    
    # 5. Which shift produced the most? (new global ranking intent, clears all context)
    mock_llm.return_value = StructuredIntent(intent="unsupported", out_of_scope_reason="Ranking not supported")
    res = await chat_service._handle_message("Which shift produced the most?", session, "admin", "msg5")
    assert res.response_type == "text"

@pytest.mark.asyncio
async def test_multi_intent_clarification(mock_llm):
    session = session_manager.create_session(1, "admin", "admin")
    mock_llm.return_value = StructuredIntent(
        intent="clarification_needed", 
        needs_clarification=True,
        clarification_reason="I can only answer one KPI at a time."
    )
    res = await chat_service._handle_message("How much did we produce today and what percentage was defective?", session, "admin", "msg")
    assert res.response_type == "clarification"
    assert "one KPI" in res.clarification_question
