"""Integration test endpoint FastAPI tanpa memanggil Gemini asli."""
import pytest
from fastapi.testclient import TestClient

from src.api import main as main_module

client = TestClient(main_module.app)

def test_health_healthy(monkeypatch):
    monkeypatch.setattr(main_module, "check_connection", lambda: True)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "database": True}

def test_health_degraded(monkeypatch):
    monkeypatch.setattr(main_module, "check_connection", lambda: False)
    assert client.get("/health").json()["status"] == "degraded"

def test_query_success(monkeypatch):
    monkeypatch.setattr(
        main_module, "ask",
        lambda q: {"question": q, "answer": "3 customer", "sql_query": "SELECT ...", "raw_data": "[(3,)]"},
    )
    r = client.post("/query", json={"question": "berapa jumlah customer?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "3 customer"

def test_query_guard_rejection_returns_400(monkeypatch):
    monkeypatch.setattr(
        main_module, "ask",
        lambda q: {"error": "Query ditolak oleh guard keamanan.", "sql_query": "DROP ..."},
    )
    r = client.post("/query", json={"question": "hapus semua data"})
    assert r.status_code == 400
    assert "guard" in r.json()["error"].lower()

def test_query_agent_crash_returns_500(monkeypatch):
    def boom(_q):
        raise RuntimeError("gemini meledak")
    monkeypatch.setattr(main_module, "ask", boom)
    r = client.post("/query", json={"question": "pertanyaan valid"})
    assert r.status_code == 500

@pytest.mark.parametrize("bad", ["", "ab"])  # min_length=3
def test_query_input_validation_422(bad):
    assert client.post("/query", json={"question": bad}).status_code == 422