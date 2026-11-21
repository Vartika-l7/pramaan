"""AI Claim Drafting, Deterministic Claim Verification, and Challenger APIs."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Query
from backend.app.db import get_db_connection
from backend.app.ai.provider import get_ai_provider
from backend.app.ai.run_records import record_ai_run, build_explain_payload
from backend.app.correlate.base import deterministic_id
from backend.app.verify.claim_verifier import verify_claims
from backend.app.verify.challenger import run_challenger_analysis

router = APIRouter(prefix="/api", tags=["claims_and_verify"])


@router.post("/ai/draft")
def draft_claims_endpoint(case_id: Optional[str] = Query(None)):
    """AI drafts structured forensic claims citing explicit database record IDs (PROPOSED status)."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events ORDER BY ts_utc ASC, id ASC LIMIT 200;")
        events = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id ASC;")
        anomalies = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, src, dst, edge_type, reason_text FROM edges ORDER BY id ASC;")
        edges = [dict(r) for r in cursor.fetchall()]

        context_records = {
            "events": events,
            "anomalies": anomalies,
            "edges": edges,
        }

        provider = get_ai_provider()
        drafted = provider.draft_claims(context_records)

        input_record_ids = (
            [e["id"] for e in events]
            + [a["id"] for a in anomalies]
            + [e["id"] for e in edges]
        )
        run_rec = record_ai_run(
            conn,
            task="claim_drafting",
            model_name=getattr(provider, "model_name", provider.__class__.__name__),
            model_version=getattr(provider, "model_version", "1.0"),
            parameters=getattr(provider, "parameters", {"temperature": 0, "seed": 42}),
            prompt=getattr(provider, "last_prompt", ""),
            input_record_ids=input_record_ids,
            raw_output=getattr(provider, "last_raw_output", json.dumps(drafted, ensure_ascii=True)),
            verifier_result={"status": "PENDING_VERIFICATION", "proposed_count": len(drafted)},
        )

        # Store as PROPOSED claims linked to ai_run_id
        for c in drafted:
            refs = c.get("refs", [])
            cid = c.get("id") or deterministic_id("claim", c["text"], c.get("kind", "finding"), *[str(r) for r in refs])
            c["id"] = cid
            c["ai_run_id"] = run_rec["id"]
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes, ai_run_id)
                VALUES (?, ?, ?, 'LEAD', 'PROPOSED', ?, ?, ?, 'Pending deterministic verification', ?);
                """,
                (
                    cid,
                    c["text"],
                    c.get("kind", "finding"),
                    json.dumps(refs),
                    json.dumps(c.get("quotes", [])),
                    provider.__class__.__name__,
                    run_rec["id"],
                ),
            )
        conn.commit()

        return {
            "status": "DRAFTED",
            "provider": provider.__class__.__name__,
            "ai_run_id": run_rec["id"],
            "record_sha256": run_rec["record_sha256"],
            "claims_count": len(drafted),
            "claims": drafted,
        }
    finally:
        conn.close()


@router.post("/verify/claims")
def verify_claims_endpoint(case_id: Optional[str] = Query(None)):
    """Execute Rules V1 to V5 on all proposed claims and return before/after verification report."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claims WHERE status = 'PROPOSED';")
        rows = cursor.fetchall()

        claims_to_verify = []
        for r in rows:
            claims_to_verify.append({
                "id": r["id"],
                "text": r["text"],
                "kind": r["kind"],
                "refs": json.loads(r["source_refs_json"]),
                "quotes": json.loads(r["quotes_json"]),
                "generated_by": r["generated_by"],
                "ai_run_id": r["ai_run_id"],
            })

        report = verify_claims(conn, claims_to_verify)
        return report
    finally:
        conn.close()


@router.get("/claims")
def list_claims(case_id: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    """List forensic claims filtered by status (PROPOSED, VERIFIED, APPROVED, REMOVED) with Explain payloads."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        query = ["SELECT * FROM claims WHERE 1=1"]
        params = []
        if status:
            query.append("AND status = ?")
            params.append(status.upper())
        query.append("ORDER BY rowid ASC;")

        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            refs = json.loads(d.pop("source_refs_json", "[]"))
            quotes = json.loads(d.pop("quotes_json", "[]"))
            d["source_refs"] = refs
            d["quotes"] = quotes
            d["explain"] = build_explain_payload(
                conn,
                record_ids=refs,
                ai_run_id=d.get("ai_run_id"),
                fallback_model=d.get("generated_by", "AI_DRAFT"),
                fallback_raw=d.get("text", ""),
                verifier_notes=d.get("verifier_notes"),
                item_type="claim",
                item_id=d["id"],
            )
            results.append(d)
        return results
    finally:
        conn.close()


@router.post("/challenge/run")
def run_cross_examination_challenge(case_id: Optional[str] = Query(None)):
    """Execute Challenger cross-examination mode to produce defence objections and evidentiary weak-points."""
    conn = get_db_connection(case_id)
    try:
        return run_challenger_analysis(conn)
    finally:
        conn.close()
