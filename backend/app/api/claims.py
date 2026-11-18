"""AI Claim Drafting, Deterministic Claim Verification, and Challenger APIs."""

from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Body, HTTPException
from backend.app.db import get_db_connection
from backend.app.ai.provider import get_ai_provider
from backend.app.verify.claim_verifier import verify_claims
from backend.app.verify.challenger import run_challenger_analysis

router = APIRouter(prefix="/api", tags=["claims_and_verify"])


@router.post("/ai/draft")
def draft_claims_endpoint(case_id: Optional[str] = Query(None)):
    """AI drafts structured forensic claims citing explicit database record IDs (PROPOSED status)."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events LIMIT 200;")
        events = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, kind, severity, description FROM anomalies;")
        anomalies = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, src, dst, edge_type, reason_text FROM edges;")
        edges = [dict(r) for r in cursor.fetchall()]

        context_records = {
            "events": events,
            "anomalies": anomalies,
            "edges": edges,
        }

        provider = get_ai_provider()
        drafted = provider.draft_claims(context_records)

        # Store as PROPOSED claims
        import uuid
        for c in drafted:
            cid = c.get("id") or str(uuid.uuid4())
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
                VALUES (?, ?, ?, 'LEAD', 'PROPOSED', ?, ?, ?, 'Pending deterministic verification');
                """,
                (
                    cid,
                    c["text"],
                    c.get("kind", "finding"),
                    json.dumps(c.get("refs", [])),
                    json.dumps(c.get("quotes", [])),
                    provider.__class__.__name__,
                ),
            )
        conn.commit()

        return {
            "status": "DRAFTED",
            "provider": provider.__class__.__name__,
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
            })

        report = verify_claims(conn, claims_to_verify)
        return report
    finally:
        conn.close()


@router.get("/claims")
def list_claims(case_id: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    """List forensic claims filtered by status (PROPOSED, VERIFIED, APPROVED, REMOVED)."""
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
            d["source_refs"] = json.loads(d.pop("source_refs_json", "[]"))
            d["quotes"] = json.loads(d.pop("quotes_json", "[]"))
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

