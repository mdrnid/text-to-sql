"""Bukti end-to-end: SELECT aman jalan di Postgres, DDL diblokir SEBELUM
menyentuh DB. Pakai testcontainers, bukan mock."""
import pytest
from sqlalchemy import create_engine, text

testcontainers = pytest.importorskip("testcontainers.postgres")
from testcontainers.postgres import PostgresContainer  # noqa: E402

from src.agent.sql_guard import sanitize_sql, UnsafeSQLError

pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def pg_engine(sample_schema_sql):
    with PostgresContainer("postgres:16-alpine") as pg:
        engine = create_engine(pg.get_connection_url())
        with engine.begin() as conn:
            for stmt in filter(str.strip, sample_schema_sql.split(";")):
                conn.execute(text(stmt))
        yield engine
        engine.dispose()

def test_safe_select_executes(pg_engine):
    safe = sanitize_sql(
        "SELECT customer_state, COUNT(*) AS n FROM olist_customers "
        "GROUP BY customer_state ORDER BY n DESC"
    )
    with pg_engine.connect() as conn:
        rows = conn.execute(text(safe)).fetchall()
    assert ("SP", 2) in [(r[0], r[1]) for r in rows]

def test_ddl_blocked_before_touching_db(pg_engine):
    # Guard harus nolak DULUAN; DB tidak boleh pernah lihat query ini.
    with pytest.raises(UnsafeSQLError):
        sanitize_sql("DROP TABLE olist_customers")
    # Pastikan tabel masih utuh.
    with pg_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM olist_customers")).scalar() == 3