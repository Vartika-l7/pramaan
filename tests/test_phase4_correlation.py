"""Acceptance tests for Phase 4: Correlation, Edges, Funnel Pattern & Graph API."""

from pathlib import Path
import pytest

from backend.app.db import init_db
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import generate_correlation_edges
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.correlate.graph import get_cytoscape_graph

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


@pytest.fixture
def correlate_db():
    case_id = "TEST-CASE-CORRELATE"
    conn = init_db(case_id)
    yield conn
    conn.close()
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{case_id}.db"
    for f in db_file.parent.glob(f"{case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_correlation_pipeline_and_planted_facts(correlate_db):
    test_files = [
        ("whatsapp_chat_meera_vikram.txt", "whatsapp"),
        ("bank_statement_mule_A.pdf", "bank_pdf"),
        ("call_log_device1.csv", "calllog"),
        ("call_log_device2.csv", "calllog"),
        ("screenshot_reused_a.png", "image"),
        ("screenshot_reused_b.jpg", "image"),
    ]

    for fname, stype in test_files:
        fpath = DATA_DIR / fname
        with open(fpath, "rb") as f:
            ev_meta = ingest_file(correlate_db, f, filename=fname, source_type=stype)
        parse_and_store_evidence(correlate_db, ev_meta["id"])

    # Extract entities & mentions
    run_entity_extraction(correlate_db)

    # Generate correlation edges
    edge_counts = generate_correlation_edges(correlate_db)
    assert edge_counts["same_identifier"] > 0, "GT-01: Cross-source identifier link not created"
    assert edge_counts["same_device"] > 0, "GT-03: Shared device D1 link not created"
    assert edge_counts["same_media"] > 0, "GT-07: Reused image pHash link not created"

    # Detect funnel pattern
    funnel_findings = detect_mule_funnel_pattern(correlate_db)
    assert len(funnel_findings) > 0, "GT-02: Mule funnel pattern not detected"
    assert funnel_findings[0]["ratio"] >= 0.85

    # Check Cytoscape graph assembly
    graph = get_cytoscape_graph(correlate_db)
    assert graph["total_nodes"] > 5
    assert graph["total_edges"] > 3

    # All generated edges must have tier 'LEAD'
    for edge in graph["edges"]:
        assert edge["data"]["tier"] == "LEAD"

