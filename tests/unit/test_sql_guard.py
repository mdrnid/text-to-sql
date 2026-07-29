"""Unit test untuk guard keamanan SQL (src/agent/sql_guard.py).

Membuktikan klaim keamanan repo: hanya SELECT read-only, blokir stacked
query & DDL/DML, dan paksa LIMIT default. Murni, tanpa DB/LLM.
"""
import pytest

from src.agent.sql_guard import sanitize_sql, UnsafeSQLError, DEFAULT_LIMIT

# ── 1. Happy path ──────────────────────────────────────────────────────
def test_plain_select_gets_default_limit():
    out = sanitize_sql("SELECT * FROM olist_customers")
    assert f"LIMIT {DEFAULT_LIMIT}" in out.upper()

def test_existing_limit_is_preserved():
    out = sanitize_sql("SELECT * FROM olist_customers LIMIT 5").upper()
    assert "LIMIT 5" in out
    assert f"LIMIT {DEFAULT_LIMIT}" not in out

def test_trailing_semicolon_is_stripped():
    # Tidak boleh nge-raise "banyak statement" hanya karena titik koma.
    out = sanitize_sql("SELECT customer_id FROM olist_customers;")
    assert "customer_id" in out.lower()

def test_cte_with_is_allowed():
    out = sanitize_sql(
        "WITH c AS (SELECT customer_state AS s FROM olist_customers) "
        "SELECT * FROM c"
    )
    assert "select" in out.lower()

def test_subquery_in_from_is_allowed():
    out = sanitize_sql("SELECT * FROM (SELECT 1 AS x) sub")
    assert "select" in out.lower()

def test_inline_comment_single_statement_ok():
    out = sanitize_sql("SELECT 1 AS x -- komentar iseng")
    assert "select" in out.lower()

# ── 2. Serangan / operasi terlarang WAJIB ditolak ──────────────────────
STACKED_INJECTION = "SELECT * FROM olist_customers; DROP TABLE olist_customers"

@pytest.mark.parametrize(
    "malicious_sql",
    [
        pytest.param(STACKED_INJECTION, id="stacked-drop"),
        pytest.param("DROP TABLE olist_customers", id="drop"),
        pytest.param("DELETE FROM olist_customers", id="delete"),
        pytest.param("UPDATE olist_customers SET customer_city='x'", id="update"),
        pytest.param("INSERT INTO olist_customers VALUES ('x')", id="insert"),
        pytest.param("TRUNCATE TABLE olist_customers", id="truncate"),
        pytest.param("ALTER TABLE olist_customers ADD c INT", id="alter"),
        pytest.param("CREATE TABLE hack (id INT)", id="create"),
        pytest.param("GRANT ALL ON olist_customers TO llm_readonly", id="grant"),
        pytest.param("INSERT INTO t SELECT * FROM olist_customers", id="insert-select"),
        pytest.param("   ", id="empty"),
    ],
)
def test_dangerous_sql_is_rejected(malicious_sql):
    with pytest.raises(UnsafeSQLError):
        sanitize_sql(malicious_sql)

def test_stacked_query_message_is_specific():
    with pytest.raises(UnsafeSQLError, match="satu statement"):
        sanitize_sql(STACKED_INJECTION)

# ── 3. Known gap (dokumentasi bug, biar nggak "diam-diam") ─────────────
@pytest.mark.xfail(
    reason="GAP: sqlglot.ParseError belum dibungkus jadi UnsafeSQLError. "
           "Guard harus catch parse error & re-raise UnsafeSQLError.",
    strict=False,
)
def test_malformed_sql_should_raise_unsafe_not_parseerror():
    with pytest.raises(UnsafeSQLError):
        sanitize_sql("SELEKT bukan sql yang valid $$$")