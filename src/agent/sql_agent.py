"""LangChain SQL LCEL Chain - Token-efficient pipeline (hardened)."""

from loguru import logger

from langchain_community.utilities import SQLDatabase
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmCategory,
    HarmBlockThreshold,
)
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from src.config import get_settings
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.sql_guard import sanitize_sql, UnsafeSQLError

settings = get_settings()

_db = None
_llm = None
_execute_query_tool = None
_sql_query_chain = None
_answer_chain = None

# ── Klasifikasi error transient (layak di-retry) ──────────────────────
_TRANSIENT_MARKERS = (
    "429", "RESOURCE_EXHAUSTED",       # rate limit / quota
    "503", "UNAVAILABLE",              # server overload
    "500", "DeadlineExceeded", "504",  # internal / timeout
)

def _is_transient(exc: BaseException) -> bool:
    """True hanya untuk error API sementara — bukan error logika/SQL."""
    if isinstance(exc, UnsafeSQLError):
        return False
    return any(marker in str(exc) for marker in _TRANSIENT_MARKERS)

# Decorator retry: exponential backoff 2s → 4s → 8s ... maks 30s, 4 attempt.
# reraise=True → setelah attempt habis, exception asli dilempar (bukan RetryError).
_transient_retry = retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)

def _init_components():
    global _db, _llm, _execute_query_tool, _sql_query_chain, _answer_chain
    if _db is not None:
        return

    # Database: koneksi READ-ONLY (role llm_readonly), bukan kredensial admin.
    _db = SQLDatabase.from_uri(
        settings.agent_database_url,
        sample_rows_in_table_info=0,  # hemat token
    )

    model_id = settings.LLM_MODEL
    if not model_id.startswith("models/"):
        model_id = f"models/{model_id}"

    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    }

    _llm = ChatGoogleGenerativeAI(
        model=model_id,
        temperature=0,
        api_key=settings.GOOGLE_API_KEY,
        safety_settings=safety_settings,
    )

    _execute_query_tool = QuerySQLDataBaseTool(db=_db)
    _sql_query_chain = create_sql_query_chain(_llm, _db)

    answer_prompt = PromptTemplate.from_template(
        "Based on the user's question, the SQL query, and the SQL result, "
        "write a natural language response.\n"
        "Question: {question}\n"
        "SQL Query: {query}\n"
        "SQL Result: {result}\n"
        "If the result is empty, say so politely. Be direct and format numbers clearly.\n"
        "Answer: "
    )
    _answer_chain = answer_prompt | _llm | StrOutputParser()

# ── Panggilan LLM yang dibungkus retry (transient-only) ───────────────
@_transient_retry
def _generate_sql(question: str) -> str:
    enhanced_question = f"{SYSTEM_PROMPT}\n\nQuestion: {question}"
    return _sql_query_chain.invoke({"question": enhanced_question})

@_transient_retry
def _formulate_answer(question: str, query: str, result) -> str:
    return _answer_chain.invoke(
        {"question": question, "query": query, "result": result}
    )

def _clean_sql(generated_sql: str) -> str:
    clean = generated_sql.replace("```sql", "").replace("```", "").strip()
    if clean.startswith("SQLQuery:"):
        clean = clean.replace("SQLQuery:", "").strip()
    return clean

def ask(question: str) -> dict:
    """Pipeline: Generate SQL -> Guard -> Run DB -> Formulate Answer.

    Catatan: fungsi ini SINKRON (blocking I/O). Panggil via
    fastapi.concurrency.run_in_threadpool dari endpoint async.
    Retry transient ditangani oleh @_transient_retry, BUKAN time.sleep manual.
    """
    _init_components()
    clean_sql = None

    try:
        # 1. Generate SQL (retry otomatis kalau API 429/503)
        clean_sql = _clean_sql(_generate_sql(question))

        # 2. GUARD: tolak non-SELECT, blokir stacked query, paksa LIMIT.
        #    UnsafeSQLError TIDAK di-retry (bukan transient).
        try:
            safe_sql = sanitize_sql(clean_sql, dialect="postgres")
        except UnsafeSQLError as guard_err:
            logger.warning(f"Blocked unsafe SQL: {guard_err} | sql={clean_sql!r}")
            return {
                "error": "Query ditolak oleh guard keamanan (hanya SELECT diizinkan).",
                "detail": str(guard_err),
                "sql_query": clean_sql,
            }

        # 3. Eksekusi SQL yang sudah aman
        raw_data = _execute_query_tool.invoke(safe_sql)

        # 4. Generate jawaban natural language (retry otomatis)
        final_answer = _formulate_answer(question, safe_sql, raw_data)

        return {
            "question": question,
            "answer": final_answer,
            "sql_query": safe_sql,
            "raw_data": str(raw_data) if raw_data else None,
        }

    except Exception as e:
        error_str = str(e)
        logger.error(f"Pipeline failed: {error_str[:300]}")
        # SQL invalid yang lolos guard tapi ditolak Postgres → 400, bukan crash.
        if "SQL" in error_str or "syntax" in error_str.lower():
            return {
                "error": "Invalid SQL generated by AI",
                "detail": error_str,
                "sql_query": locals().get("safe_sql") or clean_sql,
            }
        raise  # error tak terduga → biarkan endpoint balas 500