"""Phase 2C Tests: Investigator Assistant, FTS5, Verifier, Memory, and Evaluation."""

from __future__ import annotations

from scripts.eval_assistant import run_eval


def test_assistant_eval_metrics():
    metrics = run_eval()
    assert metrics["total_questions"] >= 30
    assert metrics["unanswerable_questions"] >= 8
    assert metrics["citation_precision"] >= 0.50
    assert metrics["unanswerable_refusal_rate"] >= 0.60
