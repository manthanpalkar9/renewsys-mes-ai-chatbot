

# =====================================================================
# Phase 2.5 / UI Issues Regression Tests
# =====================================================================

def test_regression_defect_rate(client):
    # Issue 2: defect rate returns bad quantity.
    # We mock the LLM to return metric="defect_rate" and verify it generates a KPI card for Defect Rate.
    with patch("app.llm.mock_provider.MockLLMProvider.parse_intent") as mock_parse:
        from app.llm.intent_schema import StructuredIntent
        mock_parse.return_value = StructuredIntent(
            intent="defect_rate",
            metric="defect_rate",
            date_expression="yesterday"
        )
        response = client.post("/api/chat/", json={"session_id": "reg_sess_1", "message": "What was our defect rate yesterday?"})
        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "kpi_card"
        assert data["kpi_card"]["kpi_name"] == "Defect Rate"
        assert data["kpi_card"]["unit"] == "%"

def test_regression_production_comparison(client):
    # Issue 3: Comparison query
    with patch("app.llm.mock_provider.MockLLMProvider.parse_intent") as mock_parse:
        from app.llm.intent_schema import StructuredIntent, ComparisonParams
        mock_parse.return_value = StructuredIntent(
            intent="production_comparison",
            metric="total_production",
            comparison=ComparisonParams(period_a="today", period_b="yesterday")
        )
        response = client.post("/api/chat/", json={"session_id": "reg_sess_2", "message": "Compare today's production with yesterday's"})
        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "kpi_card"
        assert data["kpi_card"]["kpi_name"] == "Total Production"
        assert "Diff:" in data["kpi_card"]["note"]

def test_regression_ambiguous_performance(client):
    # Issue 4: Ambiguous performance query
    with patch("app.llm.mock_provider.MockLLMProvider.parse_intent") as mock_parse:
        from app.llm.intent_schema import StructuredIntent
        mock_parse.return_value = StructuredIntent(
            intent="clarification_needed",
            needs_clarification=True,
            clarification_reason="I can summarize production, defects, FPY, or other available KPIs. Which would you like?"
        )
        response = client.post("/api/chat/", json={"session_id": "reg_sess_3", "message": "How did we perform today?"})
        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "clarification"

def test_regression_sequential_multiturn(client):
    # Issue 5: Sequential context tests
    with patch("app.llm.mock_provider.MockLLMProvider.parse_intent") as mock_parse:
        from app.llm.intent_schema import StructuredIntent
        # Turn 1
        mock_parse.return_value = StructuredIntent(intent="production_summary", metric="total_production", date_expression="today")
        r1 = client.post("/api/chat/", json={"session_id": "reg_sess_4", "message": "Show me today's production"})
        assert r1.status_code == 200
        
        # Turn 2
        mock_parse.return_value = StructuredIntent(intent="production_summary", metric="total_production", date_expression="yesterday")
        r2 = client.post("/api/chat/", json={"session_id": "reg_sess_4", "message": "What about yesterday?"})
        assert r2.status_code == 200
        assert r2.json()["kpi_card"]["period"] == "yesterday"

def test_regression_machine_ranking(client):
    # Issue 1: Machine ranking unsupported
    with patch("app.llm.mock_provider.MockLLMProvider.parse_intent") as mock_parse:
        from app.llm.intent_schema import StructuredIntent
        mock_parse.return_value = StructuredIntent(
            intent="unsupported",
            out_of_scope_reason="Machine-level ranking is not supported; data is tracked at the Line level."
        )
        response = client.post("/api/chat/", json={"session_id": "reg_sess_5", "message": "Which machine had the highest production today?"})
        assert response.status_code == 200
        assert response.json()["response_type"] == "text"
        assert "not supported" in response.json()["answer"].lower()
