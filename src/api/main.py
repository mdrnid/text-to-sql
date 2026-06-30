"""FastAPI application - Text-to-SQL AI Agent."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool 
from loguru import logger
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.db.connection import check_connection
from src.agent.sql_agent import ask

app = FastAPI(
    title="Text-to-SQL AI Agent",
    description="Natural-language Business Intelligence queries over the Olist E-Commerce dataset.",
    version="0.1.0",
)

# CORS (allow frontend dev servers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


class QueryResponse(BaseModel):
    question: str
    answer: str
    sql_query: str | None = None
    raw_data: str | None = None


# Mount static files folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Front-End UI
@app.get("/", tags=["ui"], response_class=FileResponse)
def serve_ui():
    """Serve the main Chat Assistant UI."""
    return os.path.join(STATIC_DIR, "index.html")


# System Info
@app.get("/api/info", tags=["system"])
def system_info():
    return {
        "title": app.title,
        "version": app.version,
        "docs_url": "/docs",
        "health_url": "/health",
        "query_url": "/query",
    }


# Health Check
@app.get("/health", tags=["system"])
def health():
    db_ok = check_connection()
    return {"status": "healthy" if db_ok else "degraded", "database": db_ok}


# Query Endpoint
@app.post("/query", tags=["agent"])
async def query(payload: QueryRequest):
    """Terima pertanyaan natural language, balas jawaban AI."""
    question = payload.question
    logger.info(f"Received question: {question}")

    try:
        # ask() sinkron & blocking → jalankan di worker thread,
        # event loop tetap bebas melayani request lain.
        result = await run_in_threadpool(ask, question)
    except Exception as e:
        logger.error(f"Agent crashed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Agent failed to process the request", "detail": str(e)},
        )

    if isinstance(result, dict) and "error" in result:
        logger.warning(f"Query rejected: {result.get('error')} | {result.get('detail')}")
        return JSONResponse(status_code=400, content=result)

    return result