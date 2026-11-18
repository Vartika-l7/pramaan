"""Benchmark results API endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter
from backend.app.config import BASE_DIR

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])
BENCHMARK_PATH = BASE_DIR / "data" / "case_alpha" / "benchmark_results.json"


@router.get("/results")
def get_benchmark_results():
    if not BENCHMARK_PATH.exists():
        from scripts.benchmark import run_benchmark
        return run_benchmark()
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

