# tests/conftest.py
"""Fixture & env global untuk semua test."""
import os
import pytest

# Set env dummy SEBELUM src.config di-import di mana pun,
# supaya import module berat (langchain) tidak gagal di CI.
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key")
os.environ.setdefault("DB_READONLY_PASSWORD", "test-readonly-pw")

@pytest.fixture(scope="session")
def sample_schema_sql() -> str:
    """Skema mini + data buat integration test (subset Olist)."""
    return """
    CREATE TABLE olist_customers (
        customer_id TEXT PRIMARY KEY,
        customer_city TEXT,
        customer_state TEXT
    );
    INSERT INTO olist_customers VALUES
        ('c1', 'sao paulo', 'SP'),
        ('c2', 'rio de janeiro', 'RJ'),
        ('c3', 'sao paulo', 'SP');
    """