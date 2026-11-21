"""Benchmark and Trust Report results API endpoint."""

from __future__ import annotations

import json
import re
from pathlib import Path
from fastapi import APIRouter
from backend.app.config import BASE_DIR

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])
BENCHMARK_PATH = BASE_DIR / "data" / "case_alpha" / "benchmark_results.json"
ASSISTANT_EVAL_PATH = BASE_DIR / "data" / "case_alpha" / "assistant_eval_results.json"
COVERAGE_PATH = BASE_DIR / "docs" / "coverage.txt"


@router.get("/results")
def get_benchmark_results():
    if not BENCHMARK_PATH.exists():
        from scripts.benchmark import run_benchmark
        bench = run_benchmark()
    else:
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            bench = json.load(f)

    if ASSISTANT_EVAL_PATH.exists():
        try:
            with open(ASSISTANT_EVAL_PATH, "r", encoding="utf-8") as f:
                bench["assistant_eval"] = json.load(f)
        except Exception:
            pass

    if COVERAGE_PATH.exists():
        try:
            cov_text = COVERAGE_PATH.read_text(encoding="utf-8")
            m = re.search(r"TOTAL\s+.*?(\d+(?:\.\d+)?%)", cov_text)
            if m:
                bench["backend_coverage"] = m.group(1)
        except Exception:
            pass

    return bench

