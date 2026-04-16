"""LangChain SQL Agent – core chain construction."""

import time
import os
from loguru import logger

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import get_settings
from src.agent.prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES

settings = get_settings()

# ── Module-level singletons ────────────────────────────────────────────
_db = None
_agent = None


def _get_db() -> SQLDatabase:
    """Lazy-init and cache the SQLDatabase connection."""
    global _db
    if _db is None:
        _db = SQLDatabase.from_uri(
            settings.database_url,
            sample_rows_in_table_info=3,
        )
    return _db


def _get_agent():
    """Lazy-init and cache the LangChain SQL agent."""
    global _agent
    if _agent is None:
        db = _get_db()

        # Ensure model ID has the 'models/' prefix if mission
        model_id = settings.LLM_MODEL
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        # Mask API key for safety
        masked_key = f"{settings.GOOGLE_API_KEY[:6]}...{settings.GOOGLE_API_KEY[-4:]}"
        logger.info(f"Initializing Agent with Model: {model_id} and Key: {masked_key}")

        llm = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=0,
            api_key=settings.GOOGLE_API_KEY,  # Modern param name
            max_retries=1,                  # We handle retries manually for 429s
        )

        _agent = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="tool-calling",
            prefix=SYSTEM_PROMPT,
            verbose=True,
        )
    return _agent


def ask(question: str, max_retries: int = 3) -> dict:
    """Send a question with manual retry logic for Gemini rate limits."""
    agent = _get_agent()

    for attempt in range(1, max_retries + 1):
        try:
            result = agent.invoke({"input": question})
            return {
                "question": question,
                "answer": result.get("output", ""),
            }
        except Exception as e:
            error_str = str(e)
            logger.error(f"Attempt {attempt} failed: {error_str[:300]}")

            # Check for Rate Limit (429) or Resource Exhausted
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = 20 * attempt
                logger.warning(f"Rate limit reached. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                # For non-429 errors, don't retry, just propagate
                raise e

    raise RuntimeError("Timed out waiting for Gemini API quota. Please try again in 1-2 minutes.")
