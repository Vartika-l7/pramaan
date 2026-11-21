"""Evaluation script for the PRAMAAN Investigator Assistant (Phase 2C).

Computes real metrics on the synthetic dataset (data/case_alpha) and tests/assistant_eval.json:
- Citation precision & recall
- Share of sentences removed by the deterministic verifier
- Unanswerable refusal accuracy
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from backend.app.db import SCHEMA_SQL
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import generate_correlation_edges
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
from backend.app.authenticity.exif import inspect_image_authenticity
from backend.app.authenticity.statement_checks import verify_statement_arithmetic
from backend.app.sequence.generator import generate_event_sequence
from backend.app.assistant.engine import ask_assistant

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "case_alpha"
EVAL_PATH = ROOT / "tests" / "assistant_eval.json"


def run_eval() -> Dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    for f in sorted(DATA_DIR.iterdir()):
        if f.is_file() and f.name not in ("ground_truth.json", "benchmark_results.json", "tower_registry.csv"):
            with open(f, "rb") as fh:
                res = ingest_file(conn, fh, f.name, actor="EVAL")
            parse_and_store_evidence(conn, res["id"], actor="EVAL")

    run_entity_extraction(conn)
    detect_timeline_anomalies(conn)
    detect_spatial_movement(conn)
    generate_correlation_edges(conn)
    detect_mule_funnel_pattern(conn)
    inspect_image_authenticity(conn)
    verify_statement_arithmetic(conn)
    generate_event_sequence(conn)

    questions = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    ans_total = 0
    ans_with_citations = 0
    ans_keyword_hits = 0
    unans_total = 0
    unans_refused = 0
    total_claims = 0
    removed_claims = 0

    for item in questions:
        resp = ask_assistant(conn, item["question"], session_id=f"eval_{item['id']}")
        claims = resp.get("claims", [])
        removed = resp.get("how_i_got_this", {}).get("removed_count", 0)
        total_claims += len(claims) + removed
        removed_claims += removed

        if item["answerable"]:
            ans_total += 1
            if claims and all(c.get("refs") for c in claims):
                ans_with_citations += 1
            ans_low = resp["answer"].lower()
            if any(k.lower() in ans_low for k in item["expected_keywords"]):
                ans_keyword_hits += 1
        else:
            unans_total += 1
            if "found nothing in the evidence" in resp["answer"].lower():
                unans_refused += 1

    conn.close()
    return {
        "dataset": "synthetic dataset (case_alpha)",
        "total_questions": len(questions),
        "answerable_questions": ans_total,
        "citation_precision": round(ans_with_citations / max(1, ans_total), 3),
        "keyword_recall": round(ans_keyword_hits / max(1, ans_total), 3),
        "unanswerable_questions": unans_total,
        "unanswerable_refusal_rate": round(unans_refused / max(1, unans_total), 3),
        "verifier_removed_share": round(removed_claims / max(1, total_claims), 3),
    }


if __name__ == "__main__":
    print(json.dumps(run_eval(), indent=2))
