"""FastAPI application – Text-to-SQL AI Agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from src.db.connection import check_connection
from src.agent.sql_agent import ask

app = FastAPI(
    title="Text-to-SQL AI Agent",
    description="Natural-language Business Intelligence queries over the Olist E-Commerce dataset.",
    version="0.1.0",
)

# ── CORS (allow frontend dev servers) ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# Mount static files folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Front-End UI ───────────────────────────────────────────────────────
@app.get("/", tags=["ui"], response_class=FileResponse)
def serve_ui():
    """Serve the main Chat Assistant UI."""
    return os.path.join(STATIC_DIR, "index.html")

# ── System Info Endpoint ───────────────────────────────────────────────
@app.get("/api/info", tags=["system"])
def system_info():
    """Return JSON metadata about the API."""
    return {
        "title": app.title,
        "version": app.version,
        "docs_url": "/docs",
        "health_url": "/health",
        "query_url": "/query"
    }


# ── Health Check ───────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
def health():
    db_ok = check_connection()
    return {"status": "healthy" if db_ok else "degraded", "database": db_ok}


# ── Query Endpoint ─────────────────────────────────────────────────────
@app.post("/query", tags=["agent"])
def query(payload: dict):
    """Accept a natural-language question and return the AI-generated answer.

    Request body:
        {"question": "Berapa total revenue bulan ini?"}
    """
    question = payload.get("question", "")
    if not question:
        return {"error": "Field 'question' is required."}

    logger.info(f"Received question: {question}")
    try:
        result = ask(question)
        logger.info(f"Agent answer: {result['answer'][:200]}")
        return result
    except Exception as e:
        logger.error(f"Agent error: {str(e)}")
        return {
            "error": "Agent failed to process the request.",
            "detail": str(e)
        }
