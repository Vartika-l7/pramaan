"""Phase 4 Parts A & C Tests: Offline Network Guard, Graceful Degradation, AI Run Records, and Explainability."""

from __future__ import annotations

import json
import socket
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db import SCHEMA_SQL
from backend.app.main import app
from backend.app.network_guard import (
    OfflineNetworkError,
    install_network_guard,
    uninstall_network_guard,
    reset_guard_stats,
    get_outbound_count,
)
from backend.app.ai.provider import OllamaProvider, DeterministicProvider
from backend.app.ai.run_records import record_ai_run, build_explain_payload
from backend.app.assistant.engine import ask_assistant
from backend.app.assistant.tools import suggest_next_leads
from backend.app.verify.challenger import run_challenger_analysis
from backend.app.verify.claim_verifier import verify_claims
from backend.app.integrity.custody import verify_chain
from backend.app.spatial.geo import lookup_ip_location
from backend.app.parsers.image import ImageParser
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def test_network_guard_blocks_external_and_counts():
    """Verify Network Guard raises OfflineNetworkError and counts outbound attempts while allowing localhost."""
    reset_guard_stats()
    install_network_guard()
    try:
        assert get_outbound_count() == 0
        with pytest.raises(OfflineNetworkError):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(("8.8.8.8", 80))
            finally:
                s.close()
        assert get_outbound_count() == 1

        with pytest.raises(OfflineNetworkError):
            socket.create_connection(("example.com", 443), timeout=1.0)
        assert get_outbound_count() == 2

        # System capabilities endpoint reports real outbound counter
        with TestClient(app) as client:
            resp = client.get("/api/system/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["network_use"]["outbound_connections"] == 2
        assert data["network_use"]["guard_active"] is True
    finally:
        uninstall_network_guard()
        reset_guard_stats()


def test_graceful_offline_degradation():
    """Verify optional features degrade gracefully offline without crashing."""
    # 1. Ollama absent -> DeterministicProvider
    offline_ollama = OllamaProvider(host="http://127.0.0.1:59999")
    assert offline_ollama.is_available() is False
    det = DeterministicProvider()
    assert det.is_available() is True

    # 2. GeoIP DB absent -> "location unknown"
    assert lookup_ip_location("203.0.113.45")["place_name"] == "location unknown"

    # 3. ImageParser succeeds even if Tesseract/lang pack unavailable
    img_path = DATA_DIR / "screenshot_payment_genuine.png"
    evs, rep = ImageParser().parse_with_report(img_path, "evi_img", img_path.name)
    assert len(evs) == 1
    assert rep.to_dict()["reconciled"] is True


def test_ai_run_records_custody_and_explain_panel(tmp_path: Path):
    """Verify AI run records are hashed into custody_log and 4-part Explain payload is present."""
    import backend.app.ingest.service as ingest_svc
    orig_store = ingest_svc.EVIDENCE_STORE_DIR
    ingest_svc.EVIDENCE_STORE_DIR = tmp_path / "evidence_store"
    try:
        conn = _fresh_conn()
        try:
            with open(DATA_DIR / "whatsapp_chat_meera_vikram.txt", "rb") as f:
                ev_meta = ingest_file(conn, f, "whatsapp_chat_meera_vikram.txt", actor="TEST")
            parse_and_store_evidence(conn, ev_meta["id"], actor="TEST")

            events = [dict(r) for r in conn.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events;").fetchall()]
            prov = DeterministicProvider()
            drafted = prov.draft_claims({"events": events, "anomalies": [], "edges": []})

            run_rec = record_ai_run(
                conn,
                task="claim_drafting",
                model_name=prov.model_name,
                model_version=prov.model_version,
                parameters=prov.parameters,
                prompt=prov.last_prompt,
                input_record_ids=[e["id"] for e in events],
                raw_output=prov.last_raw_output,
                verifier_result={"status": "PENDING"},
            )
            assert run_rec["parameters"] == {"temperature": 0, "seed": 42}
            assert len(run_rec["record_sha256"]) == 64

            for c in drafted:
                c["ai_run_id"] = run_rec["id"]
            ver = verify_claims(conn, drafted)
            assert ver["verified_count"] >= 1

            # Custody log must contain AI_RUN_RECORDED and AI_VERIFIER_RECORDED and remain hash-chain valid
            actions = [r["action"] for r in conn.execute("SELECT action FROM custody_log ORDER BY seq ASC;").fetchall()]
            assert "AI_RUN_RECORDED" in actions
            assert "AI_VERIFIER_RECORDED" in actions
            chain_ok, _, err = verify_chain(conn)
            assert chain_ok is True, err

            # Build 4-part Explain payload for verified claim
            vc = ver["verified_claims"][0]
            explain = build_explain_payload(
                conn,
                record_ids=vc["refs"],
                ai_run_id=run_rec["id"],
                item_type="claim",
                item_id=vc["id"],
            )
            assert set(explain.keys()) == {
                "what_model_saw",
                "what_model_said",
                "what_verifier_kept_and_removed",
                "who_approved",
            }
            assert explain["who_approved"]["label"] == "not yet approved"
            assert len(explain["what_model_saw"]["exhibits"]) >= 1

            # Assistant answer, leads, and challenger objections all include Explain payloads and AI run records
            ans = ask_assistant(conn, "Who is connected to vikram.alpha@okaxis?", session_id="t_explain")
            assert "explain" in ans and "ai_run_id" in ans and "record_sha256" in ans
            assert ans["explain"]["who_approved"]["label"] == "not yet approved"

            leads = suggest_next_leads(conn)
            assert isinstance(leads, list)

            chal = run_challenger_analysis(conn)
            assert chal["total_objections"] >= 1
            assert "explain" in chal["objections"][0]
            assert chal["objections"][0]["explain"]["who_approved"]["label"] == "not yet approved"

            # Unanswerable question mentioning an entity must still refuse cleanly
            unans = ask_assistant(conn, "What is the flight number for Vikram's trip to Dubai?", session_id="t_unans")
            assert "found nothing in the evidence" in unans["answer"].lower()
            assert unans["claims"] == []
        finally:
            conn.close()
    finally:
        ingest_svc.EVIDENCE_STORE_DIR = orig_store


def test_court_report_pdf_only_includes_approved(tmp_path: Path):
    """Verify generate_court_report_pdf includes APPROVED findings and omits VERIFIED/LEAD-only claims."""
    import pdfplumber
    from backend.app.report.render import generate_court_report_pdf

    conn = _fresh_conn()
    conn.execute(
        """
        INSERT INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by)
        VALUES ('cl_unapproved', 'UNAPPROVED_LEAD_MARKER', 'finding', 'LEAD', 'VERIFIED', '["e1"]', '[]', 'TEST'),
               ('cl_approved', 'APPROVED_COURT_MARKER', 'finding', 'APPROVED', 'APPROVED', '["e1"]', '[]', 'TEST');
        """
    )
    conn.commit()
    pdf_path = tmp_path / "court_report.pdf"
    generate_court_report_pdf(conn, pdf_path, case_id="PRM-TEST")
    conn.close()

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "APPROVED_COURT_MARKER" in full_text
    assert "UNAPPROVED_LEAD_MARKER" not in full_text
