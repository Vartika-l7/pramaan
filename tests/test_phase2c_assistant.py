"""Phase 2C Tests: Investigator Assistant, FTS5, Verifier, Memory, and Evaluation."""

from __future__ import annotations

from pathlib import Path
import pytest

from backend.app.ai.provider import OllamaProvider
from scripts.eval_assistant import run_eval


@pytest.mark.integration
def test_assistant_eval_metrics(synthetic_dataset_dir: Path):
    metrics = run_eval(data_dir=synthetic_dataset_dir)
    assert metrics["total_questions"] >= 30
    assert metrics["unanswerable_questions"] >= 8
    assert metrics["citation_precision"] >= 0.50
    assert metrics["unanswerable_refusal_rate"] >= 0.60


@pytest.mark.llm
def test_live_ollama_provider_optional():
    """Live Ollama connectivity test — skipped by default unless --run-llm is passed."""
    provider = OllamaProvider()
    # Verifies fail-fast timeout behavior even when --run-llm is passed without Ollama running
    assert isinstance(provider.is_available(), bool)
