"""Shared pytest configuration, CLI flags, markers, and isolated session/function fixtures."""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Iterator

import pytest

# Prevent any accidental HuggingFace / Transformers model downloads during tests
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow (e.g. 200 MB hashing, extended property examples).",
    )
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run tests marked as llm against a live local Ollama server.",
    )


def pytest_configure(config: pytest.Config) -> None:
    # Default to deterministic/fake LLM provider in tests unless --run-llm is explicitly set
    if not config.getoption("--run-llm", default=False):
        os.environ["PRAMAAN_FAKE_LLM"] = "1"
    else:
        os.environ["PRAMAAN_FAKE_LLM"] = "0"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_slow = config.getoption("--run-slow")
    run_llm = config.getoption("--run-llm")

    skip_slow = pytest.mark.skip(reason="skipped by default; pass --run-slow to run")
    skip_llm = pytest.mark.skip(reason="skipped by default; pass --run-llm to run against live Ollama")

    for item in items:
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)
        if "llm" in item.keywords and not run_llm:
            item.add_marker(skip_llm)


@pytest.fixture(scope="session")
def synthetic_dataset_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide the synthetic dataset once per test session in a temporary directory."""
    repo_data = Path(__file__).resolve().parent.parent / "data" / "case_alpha"
    dst = tmp_path_factory.mktemp("pramaan_synthetic_dataset") / "case_alpha"
    if repo_data.exists() and (repo_data / "ground_truth.json").exists():
        shutil.copytree(repo_data, dst)
    else:
        # Fallback: generate once if missing
        from scripts.make_dataset import main as generate_dataset
        generate_dataset()
        shutil.copytree(repo_data, dst)
    return dst


@pytest.fixture(autouse=True)
def isolated_storage_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Ensure every test uses isolated temporary directories for DB, evidence store, and ELA."""
    case_dir = tmp_path / "case_data"
    ev_dir = tmp_path / "evidence_store"
    ela_dir = tmp_path / "ela_heatmaps"
    case_dir.mkdir(parents=True, exist_ok=True)
    ev_dir.mkdir(parents=True, exist_ok=True)
    ela_dir.mkdir(parents=True, exist_ok=True)

    import backend.app.config as cfg
    import backend.app.db as db_mod
    import backend.app.ingest.service as ingest_svc
    import backend.app.authenticity.ela as ela_mod
    import backend.app.authenticity.exif as exif_mod

    monkeypatch.setattr(cfg, "CASE_DATA_DIR", case_dir)
    monkeypatch.setattr(cfg, "EVIDENCE_STORE_DIR", ev_dir)
    monkeypatch.setattr(db_mod, "CASE_DATA_DIR", case_dir)
    monkeypatch.setattr(ingest_svc, "EVIDENCE_STORE_DIR", ev_dir)
    monkeypatch.setattr(ela_mod, "ELA_DIR", ela_dir)
    monkeypatch.setattr(exif_mod, "ELA_DIR", ela_dir)
    return tmp_path


@pytest.fixture
def isolated_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Provide a fresh temporary SQLite database with guaranteed teardown."""
    from backend.app.db import init_db

    conn = init_db("TEST-ISOLATED")
    try:
        yield conn
    finally:
        conn.close()
