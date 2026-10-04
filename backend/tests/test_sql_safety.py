import pytest
from app.services.sql_safety import sql_safety_service

def test_safe_select():
    sql = "SELECT * FROM mock_production_events WHERE shift = 'A'"
    result = sql_safety_service.validate(sql)
    assert result.is_safe is True
    assert len(result.violations) == 0

def test_prohibited_insert():
    sql = "INSERT INTO mock_production_events (line, shift) VALUES ('KM1', 'A')"
    result = sql_safety_service.validate(sql)
    assert result.is_safe is False
    assert any("prohibited keyword 'insert'" in v.lower() for v in result.violations)

def test_prohibited_delete():
    sql = "DELETE FROM mock_production_events WHERE line = 'KM1'"
    result = sql_safety_service.validate(sql)
    assert result.is_safe is False

def test_prohibited_drop():
    sql = "DROP TABLE mock_production_events"
    result = sql_safety_service.validate(sql)
    assert result.is_safe is False

def test_multiple_statements():
    sql = "SELECT * FROM users; DROP TABLE events;"
    result = sql_safety_service.validate(sql)
    assert result.is_safe is False
    assert any("multiple sql statements" in v.lower() for v in result.violations)

def test_must_start_with_select():
    sql = "WITH cte AS (SELECT * FROM t) SELECT * FROM cte"
    # Our simple safety layer requires SELECT first.
    # If CTEs are needed later, safety rules must be adjusted, but currently it blocks it.
    result = sql_safety_service.validate(sql)
    assert result.is_safe is False
    assert any("must start with select" in v.lower() for v in result.violations)
