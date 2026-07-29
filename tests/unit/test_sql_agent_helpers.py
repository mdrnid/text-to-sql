"""Test helper murni di sql_agent (tanpa memanggil LLM/DB)."""
from src.agent.sql_agent import _clean_sql, _is_transient
from src.agent.sql_guard import UnsafeSQLError

def test_clean_sql_strips_markdown_fence():
    raw = "```sql\nSELECT 1\n```"
    assert _clean_sql(raw) == "SELECT 1"

def test_clean_sql_strips_sqlquery_prefix():
    assert _clean_sql("SQLQuery: SELECT 1") == "SELECT 1"

def test_transient_classifier_true_on_rate_limit():
    assert _is_transient(Exception("429 RESOURCE_EXHAUSTED")) is True
    assert _is_transient(Exception("503 UNAVAILABLE")) is True

def test_transient_classifier_false_on_logic_error():
    assert _is_transient(Exception("syntax error near SELECT")) is False

def test_unsafe_sql_is_never_retried():
    assert _is_transient(UnsafeSQLError("blocked")) is False