"""Eval harness akurasi text-to-SQL (execution accuracy).

Untuk tiap pertanyaan: generate SQL via pipeline asli -> guard -> eksekusi,
lalu bandingkan result set-nya dengan hasil gold_sql. Non-deterministik &
berbayar, jadi di-skip default. Jalankan sengaja:

    pytest -m eval

Butuh: GOOGLE_API_KEY valid + DB Olist terisi (DATABASE_URL / .env).
"""
import os
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.eval

if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "test-dummy-key":
    pytest.skip("GOOGLE_API_KEY asli tidak diset — lewati eval.", allow_module_level=True)

from src.config import get_settings                                  # noqa: E402
from src.agent import sql_agent                                       # noqa: E402
from src.agent.sql_guard import sanitize_sql                          # noqa: E402

EVAL_THRESHOLD = 0.70  # naikkan seiring kualitas prompt membaik
DATASET = yaml.safe_load((Path(__file__).parent / "golden_dataset.yaml").read_text())

def _run(engine, sql: str):
    with engine.connect() as conn:
        return sorted(str(r) for r in conn.execute(text(sql)).fetchall())

def _pipeline_sql(question: str) -> str:
    sql_agent._init_components()
    generated = sql_agent._clean_sql(sql_agent._generate_sql(question))
    return sanitize_sql(generated, dialect="postgres")

def test_execution_accuracy_meets_threshold():
    engine = create_engine(get_settings().database_url)
    passed, report = 0, []

    for case in DATASET:
        try:
            expected = _run(engine, case["gold_sql"])
            actual = _run(engine, _pipeline_sql(case["question"]))
            ok = expected == actual
        except Exception as e:                       # noqa: BLE001
            ok = False
            report.append(f"  ✗ {case['id']}: ERROR {str(e)[:80]}")
        else:
            report.append(f"  {'✓' if ok else '✗'} {case['id']}")
        passed += int(ok)

    engine.dispose()
    accuracy = passed / len(DATASET)
    print(f"\nExecution accuracy: {accuracy:.0%} ({passed}/{len(DATASET)})")
    print("\n".join(report))
    assert accuracy >= EVAL_THRESHOLD, f"Akurasi {accuracy:.0%} < target {EVAL_THRESHOLD:.0%}"