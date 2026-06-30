"""Tes guard SQL: pastikan hanya SELECT read-only yang lolos."""

import pytest
from src.agent.sql_guard import sanitize_sql, UnsafeSQLError


def test_select_lolos_dan_dapat_limit():
    out = sanitize_sql("SELECT * FROM olist_orders")
    assert "LIMIT" in out.upper()


def test_select_dengan_limit_tidak_ditimpa():
    out = sanitize_sql("SELECT * FROM olist_orders LIMIT 5")
    assert "5" in out


@pytest.mark.parametrize(
    "query",
    [
        "DROP TABLE olist_orders",
        "DELETE FROM olist_orders",
        "UPDATE olist_orders SET order_status = 'x'",
        "INSERT INTO olist_orders (order_id) VALUES ('x')",
        "TRUNCATE olist_orders",
        "SELECT 1; DROP TABLE olist_orders",
        "WITH x AS (DELETE FROM olist_orders RETURNING *) SELECT * FROM x",
        "",
    ],
)
def test_query_berbahaya_ditolak(query):
    with pytest.raises(UnsafeSQLError):
        sanitize_sql(query)
        